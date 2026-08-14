param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$BackupId,
    [switch]$Confirm
)

$ErrorActionPreference = "Stop"
if (-not $Confirm) { throw "回滚会替换当前 data 目录；请在核验备份后使用 -Confirm" }
$Root = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$Exe = Join-Path $Root "xiaoqibao.exe"
$Running = @(Get-CimInstance Win32_Process -Filter "Name='xiaoqibao.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -and ([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($Exe)) })
if ($Running.Count) { throw "一树-A股观测台正在运行，请关闭本软件后再回滚；不会关闭通达信" }
if ($BackupId -notmatch '^backup-[A-Za-z0-9_-]+$') { throw "备份标识无效" }
$DataRoot = Join-Path $Root "data"
$BackupRoot = Join-Path $DataRoot (Join-Path "backups" $BackupId)
$ManifestPath = Join-Path $BackupRoot "manifest.json"
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) { throw "备份清单不存在" }
$Manifest = [IO.File]::ReadAllText($ManifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
$BackupData = (Resolve-Path -LiteralPath (Join-Path $BackupRoot "data")).Path
foreach ($File in @($Manifest.files)) {
    $Source = [IO.Path]::GetFullPath((Join-Path $BackupData ([string]$File.path).Replace('/', '\')))
    if (-not $Source.StartsWith($BackupData, [StringComparison]::OrdinalIgnoreCase)) { throw "备份文件路径越界" }
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "备份文件缺失：$($File.path)" }
    if ((Get-Item -LiteralPath $Source).Length -ne [long]$File.size) { throw "备份文件大小不一致：$($File.path)" }
    if ((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -ne [string]$File.sha256) { throw "备份文件哈希不一致：$($File.path)" }
}
$Stage = Join-Path $Root ("data.rollback-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $Stage | Out-Null
foreach ($File in @($Manifest.files)) {
    $Source = Join-Path $BackupData ([string]$File.path).Replace('/', '\')
    $Target = Join-Path $Stage ([string]$File.path).Replace('/', '\')
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Target) | Out-Null
    Copy-Item -LiteralPath $Source -Destination $Target -Force
}
$Previous = Join-Path $Root ("data.before-rollback-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ"))
Move-Item -LiteralPath $DataRoot -Destination $Previous
Move-Item -LiteralPath $Stage -Destination $DataRoot
Write-Host ("数据回滚完成；原 data 已保留在 {0}" -f $Previous)

