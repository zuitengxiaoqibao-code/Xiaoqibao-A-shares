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
if ([string]::IsNullOrWhiteSpace([string]$Manifest.commit)) {
    throw "Release manifest does not contain a commit"
}
if ($ExpectedCommit -and $Manifest.commit -ne $ExpectedCommit) {
    throw "Release commit mismatch: expected $ExpectedCommit, got $($Manifest.commit)"
}
if (-not $AllowDirtySource -and $Manifest.source_state -ne "clean") {
    throw "Release was not built from a clean source tree: $($Manifest.source_state)"
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

Write-Host ("Release quality verified: {0}; commit={1}; exe_sha256={2}" -f $ResolvedRoot, $Manifest.commit, $ActualHash)
