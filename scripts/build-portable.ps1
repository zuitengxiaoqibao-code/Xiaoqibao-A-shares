param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Release = Join-Path $Root "dist\XiaoQiBao-Portable"
$env:PYTHONUTF8 = "1"

if (-not $SkipTests) {
    $PreviousDataDir = [Environment]::GetEnvironmentVariable("QIBAO_DATA_DIR", "Process")
    $env:QIBAO_DATA_DIR = Join-Path $env:TEMP (
        "qibao-build-test-" + [guid]::NewGuid().ToString("N")
    )
    try {
        & $Python -m pytest (Join-Path $Root "apps\api\tests") -q
        if ($LASTEXITCODE -ne 0) { throw "API tests failed" }
    } finally {
        if ($null -eq $PreviousDataDir) {
            Remove-Item Env:QIBAO_DATA_DIR -ErrorAction SilentlyContinue
        } else {
            $env:QIBAO_DATA_DIR = $PreviousDataDir
        }
    }

    & pnpm.cmd --dir $Root --filter "@qibao/web" test
    if ($LASTEXITCODE -ne 0) { throw "Web tests failed" }
}

& pnpm.cmd --dir $Root --filter "@qibao/web" build
if ($LASTEXITCODE -ne 0) { throw "Web build failed" }

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath (Join-Path $Root "dist") `
    --workpath (Join-Path $Root "build") `
    (Join-Path $Root "packaging\xiaoqibao.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

$WebTarget = Join-Path $Release "web"
New-Item -ItemType Directory -Force -Path $WebTarget | Out-Null
Copy-Item -Path (Join-Path $Root "apps\web\dist\*") `
    -Destination $WebTarget -Recurse -Force

foreach ($Name in @(
    "config", "data", "news", "cache", "logs", "models", "exports", "backups"
)) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Release $Name) | Out-Null
}

$Files = Get-ChildItem -LiteralPath $Release -Recurse -File
$Bytes = ($Files | Measure-Object Length -Sum).Sum
Write-Host ("Portable release: {0}" -f $Release)
Write-Host ("Files: {0}; Size: {1:N1} MB" -f $Files.Count, ($Bytes / 1MB))

Get-ChildItem -LiteralPath $Release -Force | ForEach-Object {
    $ItemBytes = if ($_.PSIsContainer) {
        (Get-ChildItem -LiteralPath $_.FullName -Recurse -File |
            Measure-Object Length -Sum).Sum
    } else {
        $_.Length
    }
    Write-Host ("  {0,-24} {1,8:N1} MB" -f $_.Name, ($ItemBytes / 1MB))
}
