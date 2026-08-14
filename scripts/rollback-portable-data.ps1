param(
    [Parameter(Mandatory = $true)][string]$ReleaseRoot,
    [Parameter(Mandatory = $true)][string]$BackupId,
    [switch]$Confirm
)

$ErrorActionPreference = "Stop"
if (-not $Confirm) { throw "Rollback replaces the current data directory; verify the backup and pass -Confirm" }
$Root = (Resolve-Path -LiteralPath $ReleaseRoot).Path
$Exe = Join-Path $Root "xiaoqibao.exe"
$Running = @(Get-CimInstance Win32_Process -Filter "Name='xiaoqibao.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.ExecutablePath -and ([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($Exe)) })
if ($Running.Count) { throw "The portable app is running; close it before rollback. TongdaXin will not be closed" }
if ($BackupId -notmatch '^backup-[A-Za-z0-9_-]+$') { throw "Invalid backup identifier" }
$DataRoot = Join-Path $Root "data"
$BackupRoot = Join-Path $DataRoot (Join-Path "backups" $BackupId)
$ManifestPath = Join-Path $BackupRoot "manifest.json"
if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) { throw "Backup manifest is missing" }
$Manifest = [IO.File]::ReadAllText($ManifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
$BackupData = (Resolve-Path -LiteralPath (Join-Path $BackupRoot "data")).Path
foreach ($File in @($Manifest.files)) {
    $Source = [IO.Path]::GetFullPath((Join-Path $BackupData ([string]$File.path).Replace('/', '\')))
    if (-not $Source.StartsWith($BackupData, [StringComparison]::OrdinalIgnoreCase)) { throw "Backup file path escapes the backup root" }
    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw "Backup file is missing: $($File.path)" }
    if ((Get-Item -LiteralPath $Source).Length -ne [long]$File.size) { throw "Backup file size differs: $($File.path)" }
    if ((Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash -ne [string]$File.sha256) { throw "Backup file hash differs: $($File.path)" }
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
Write-Host ("Data rollback completed; previous data was retained at {0}" -f $Previous)
