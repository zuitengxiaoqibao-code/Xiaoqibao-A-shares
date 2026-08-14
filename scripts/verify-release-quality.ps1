param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [string]$ExpectedCommit = "",
    [switch]$AllowDirtySource
)

$ErrorActionPreference = "Stop"
$ResolvedRoot = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$Exe = Join-Path $ResolvedRoot "xiaoqibao.exe"
$ManifestPath = Join-Path $ResolvedRoot "release-manifest.json"
$RequiredDirs = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")

if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
    throw "Release executable is missing: $Exe"
}
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Release manifest is missing: $ManifestPath"
}

$Manifest = [IO.File]::ReadAllText($ManifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
$ManifestText = [IO.File]::ReadAllText($ManifestPath, [Text.UTF8Encoding]::new($false))
if ($ManifestText -match '\uFFFD|[\u00C3\u00C2\u00E5\u00E6\u00E7\u00E8\u00E9\u00EF\u00F0][^\r\n]{0,2}[\u0080-\u00BF]') {
    throw "Release manifest contains invalid UTF-8 diagnostic text"
}
if ([string]::IsNullOrWhiteSpace([string]$Manifest.commit)) {
    throw "Release manifest does not contain a commit"
}
if ($ExpectedCommit -and $Manifest.commit -ne $ExpectedCommit) {
    throw "Release commit mismatch: expected $ExpectedCommit, got $($Manifest.commit)"
}
if (-not $AllowDirtySource -and $Manifest.source_state -ne "clean") {
    throw "Release was not built from a clean source tree: $($Manifest.source_state)"
}
if ($null -eq $Manifest.migration_version -or [int]$Manifest.migration_version -lt 1) {
    throw "Release manifest contains an invalid migration version"
}
foreach ($Database in @($Manifest.database_files)) {
    $DatabasePath = Join-Path $ResolvedRoot ([string]$Database.path).Replace('/', '\')
    $ResolvedDatabase = [IO.Path]::GetFullPath($DatabasePath)
    if (-not $ResolvedDatabase.StartsWith($ResolvedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Release database path escapes the release root"
    }
    if (-not (Test-Path -LiteralPath $ResolvedDatabase -PathType Leaf)) {
        throw "Release database listed in manifest is missing: $($Database.path)"
    }
    if ((Get-Item -LiteralPath $ResolvedDatabase).Length -ne [long]$Database.bytes) {
        throw "Release database size differs from manifest: $($Database.path)"
    }
    if ((Get-FileHash -LiteralPath $ResolvedDatabase -Algorithm SHA256).Hash -ne [string]$Database.sha256) {
        throw "Release database SHA-256 differs from manifest: $($Database.path)"
    }
}

$ManifestDirs = @($Manifest.persistent_dirs | ForEach-Object { [string]$_ })
foreach ($Name in $RequiredDirs) {
    if ($ManifestDirs -notcontains $Name) {
        throw "Release manifest omits persistent directory: $Name"
    }
    $Path = Join-Path $ResolvedRoot $Name
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "Release persistent directory is missing: $Name"
    }
}

$ActualHash = (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash
if ([string]::IsNullOrWhiteSpace([string]$Manifest.exe_sha256) -or $Manifest.exe_sha256 -ne $ActualHash) {
    throw "Release executable SHA-256 does not match release manifest"
}

$DomainStatus = $Manifest.quality_gates.domain_status
if ($null -eq $DomainStatus) {
    throw "Release manifest does not contain domain status evidence"
}
$AllowedDomainStates = @("ready", "partial", "unavailable", "stale", "error")
foreach ($Name in @("overview", "quant_strategy", "company_research", "tdx_professional")) {
    $Domain = $DomainStatus.PSObject.Properties[$Name].Value
    if ($null -eq $Domain) {
        throw "Release manifest omits domain status evidence: $Name"
    }
    if ([string]$Domain.status -notin $AllowedDomainStates) {
        throw "Release manifest contains invalid domain status: $Name=$($Domain.status)"
    }
}

$SourceHealth = $Manifest.quality_gates.domain_status.source_health
if ($null -ne $SourceHealth) {
    foreach ($Name in @("probed_count", "ready_count", "degraded_count", "unavailable_count")) {
        if ($null -eq $SourceHealth.PSObject.Properties[$Name]) {
            throw "Release manifest source health omits explicit count: $Name"
        }
    }
    if ([int]$SourceHealth.ready_count + [int]$SourceHealth.degraded_count + [int]$SourceHealth.unavailable_count -ne [int]$SourceHealth.probed_count) {
        throw "Release manifest source health counts are inconsistent"
    }
}

Write-Host ("Release quality verified: {0}; commit={1}; exe_sha256={2}" -f $ResolvedRoot, $Manifest.commit, $ActualHash)
