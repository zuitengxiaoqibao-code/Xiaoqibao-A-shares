param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [int]$Port = 18766,
    [switch]$SkipApiProbe,
    [switch]$KeepDrillRoot,
    [switch]$UpdateManifest,
    [string]$ResultPath = ""
)

$ErrorActionPreference = "Stop"
$Utf8 = [Text.UTF8Encoding]::new($false)
$ResolvedRelease = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$ManifestPath = Join-Path $ResolvedRelease "release-manifest.json"
$PersistentNames = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
$DrillRoot = Join-Path $env:TEMP ("xiaoqibao-restore-drill-" + [guid]::NewGuid().ToString("N"))

function Assert-TemporaryDrillRoot([string]$Path) {
    $ResolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $ResolvedPath = [IO.Path]::GetFullPath($Path)
    if (
        -not $ResolvedPath.StartsWith($ResolvedTemp, [StringComparison]::OrdinalIgnoreCase) -or
        (Split-Path -Leaf $ResolvedPath) -notlike "xiaoqibao-restore-drill-*"
    ) {
        throw "Unsafe restore drill directory: $ResolvedPath"
    }
}

function Write-Result([object]$Value) {
    if ([string]::IsNullOrWhiteSpace($ResultPath)) { return }
    $ResolvedResult = [IO.Path]::GetFullPath($ResultPath)
    $Parent = Split-Path -Parent $ResolvedResult
    if ($Parent) { New-Item -ItemType Directory -Force -Path $Parent | Out-Null }
    [IO.File]::WriteAllText($ResolvedResult, ($Value | ConvertTo-Json -Depth 10), $Utf8)
}

& "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $ResolvedRelease -Verify
$Manifest = [IO.File]::ReadAllText($ManifestPath, $Utf8) | ConvertFrom-Json

Assert-TemporaryDrillRoot $DrillRoot
New-Item -ItemType Directory -Path $DrillRoot | Out-Null
try {
    foreach ($Name in $PersistentNames) {
        $Source = Join-Path $ResolvedRelease $Name
        if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
            throw "Restore source is missing persistent directory: $Name"
        }
        Copy-Item -LiteralPath $Source -Destination $DrillRoot -Recurse -Force
    }
    foreach ($Name in @("web", "release-manifest.json", ".migration-version")) {
        $Source = Join-Path $ResolvedRelease $Name
        if (-not (Test-Path -LiteralPath $Source)) {
            throw "Restore source is missing required release item: $Name"
        }
        Copy-Item -LiteralPath $Source -Destination (Join-Path $DrillRoot $Name) -Recurse -Force
    }

    $DatabaseCount = 0
    foreach ($Database in @($Manifest.database_files)) {
        $Relative = ([string]$Database.path).Replace('/', '\')
        $CopiedPath = [IO.Path]::GetFullPath((Join-Path $DrillRoot $Relative))
        $ResolvedDrill = [IO.Path]::GetFullPath($DrillRoot).TrimEnd('\') + '\'
        if (-not $CopiedPath.StartsWith($ResolvedDrill, [StringComparison]::OrdinalIgnoreCase)) {
            throw "Restore database path escapes the temporary drill root"
        }
        if (-not (Test-Path -LiteralPath $CopiedPath -PathType Leaf)) {
            throw "Restored database is missing: $($Database.path)"
        }
        if ((Get-Item -LiteralPath $CopiedPath).Length -ne [long]$Database.bytes) {
            throw "Restored database size differs from the signed manifest: $($Database.path)"
        }
        if ((Get-FileHash -LiteralPath $CopiedPath -Algorithm SHA256).Hash -ne [string]$Database.sha256) {
            throw "Restored database SHA-256 differs from the signed manifest: $($Database.path)"
        }
        $DatabaseCount += 1
    }

    & "$PSScriptRoot\verify-migrations.ps1" -ReleaseRoot $DrillRoot
    if (-not $SkipApiProbe) {
        & "$PSScriptRoot\run-portable-smoke.ps1" `
            -ReleaseRootOverride $ResolvedRelease `
            -PortableRootOverride $DrillRoot `
            -Port $Port
        if ($LASTEXITCODE -ne 0) { throw "Restored critical API smoke failed" }
    }

    $Result = [ordered]@{
        status = "pass"
        mode = "temporary-copy"
        database_count = $DatabaseCount
        migration_version = [int]$Manifest.migration_version
        critical_api_status = if ($SkipApiProbe) { "skipped_for_test" } else { "pass" }
        verified_at = (Get-Date).ToUniversalTime().ToString("o")
        source_release_hash = (Get-FileHash -LiteralPath $ManifestPath -Algorithm SHA256).Hash
    }
    Write-Result $Result

    if ($UpdateManifest) {
        $Current = [IO.File]::ReadAllText($ManifestPath, $Utf8) | ConvertFrom-Json
        if ($Current.PSObject.Properties.Name -contains "restore_drill") {
            $Current.restore_drill = $Result
        } else {
            $Current | Add-Member -MemberType NoteProperty -Name restore_drill -Value $Result
        }
        $Current.PSObject.Properties.Remove("manifest_signature")
        [IO.File]::WriteAllText($ManifestPath, ($Current | ConvertTo-Json -Depth 20), $Utf8)
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $ResolvedRelease
    }
    Write-Host ("Restore drill passed: databases={0}; migration={1}; critical_api={2}" -f $DatabaseCount, $Manifest.migration_version, $Result.critical_api_status)
} finally {
    if ($KeepDrillRoot) {
        Write-Host ("Restore drill directory retained: {0}" -f $DrillRoot)
    } elseif (Test-Path -LiteralPath $DrillRoot) {
        Assert-TemporaryDrillRoot $DrillRoot
        Remove-Item -LiteralPath $DrillRoot -Recurse -Force
    }
}
