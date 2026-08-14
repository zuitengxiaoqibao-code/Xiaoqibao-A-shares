param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$ManifestPath = Join-Path $Root "release-manifest.json"
$VersionPath = Join-Path $Root ".migration-version"
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
    throw "发布清单不存在，无法核验数据库迁移版本"
}
$Manifest = [IO.File]::ReadAllText($ManifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
$Expected = [int]$Manifest.migration_version
$Current = if (Test-Path -LiteralPath $VersionPath) {
    [int]([IO.File]::ReadAllText($VersionPath, [Text.Encoding]::ASCII).Trim())
} else { 0 }
if ($Current -gt $Expected) {
    throw "当前数据迁移版本高于软件支持版本，禁止降级启动：数据=$Current，软件=$Expected"
}
if ($Current -lt $Expected) {
    throw "数据迁移尚未完成：当前=$Current，目标=$Expected；请先启动新版 EXE 完成迁移"
}
Write-Host ("数据库迁移版本核验通过：{0}" -f $Current)

