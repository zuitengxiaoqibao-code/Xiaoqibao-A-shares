param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$ManifestPath = Join-Path $Root "release-manifest.json"
$VersionPath = Join-Path $Root ".migration-version"
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "Release manifest is missing; migration version cannot be verified"
}
$Manifest = [IO.File]::ReadAllText($ManifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
$Expected = [int]$Manifest.migration_version
$Current = if (Test-Path -LiteralPath $VersionPath) {
    [int]([IO.File]::ReadAllText($VersionPath, [Text.Encoding]::ASCII).Trim())
} else { 0 }
if ($Current -gt $Expected) {
    throw "Data migration version is newer than the software; downgrade startup is blocked: data=$Current, software=$Expected"
}
if ($Current -lt $Expected) {
    throw "Data migration is incomplete: current=$Current, target=$Expected; start the new EXE first"
}
Write-Host ("Migration version verified: {0}" -f $Current)
