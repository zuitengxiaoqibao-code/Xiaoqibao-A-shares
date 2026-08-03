param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Release = Join-Path $Root "dist\XiaoQiBao-Portable"
$env:PYTHONUTF8 = "1"
$PersistentNames = @(
    "config", "data", "news", "cache", "logs", "models", "exports", "backups"
)

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

$PreserveRoot = Join-Path $env:TEMP (
    "xiaoqibao-persistent-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $PreserveRoot | Out-Null
foreach ($Name in $PersistentNames) {
    $Source = Join-Path $Release $Name
    if (Test-Path -LiteralPath $Source) {
        Copy-Item -LiteralPath $Source -Destination $PreserveRoot -Recurse -Force
    }
}

try {
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
} finally {
    foreach ($Name in $PersistentNames) {
        $Target = Join-Path $Release $Name
        New-Item -ItemType Directory -Force -Path $Target | Out-Null
        $Saved = Join-Path $PreserveRoot $Name
        if (Test-Path -LiteralPath $Saved) {
            Get-ChildItem -LiteralPath $Saved -Force |
                Copy-Item -Destination $Target -Recurse -Force
        }
    }
    $ResolvedPreserve = [IO.Path]::GetFullPath($PreserveRoot)
    $ResolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    if ($ResolvedPreserve.StartsWith($ResolvedTemp)) {
        Remove-Item -LiteralPath $ResolvedPreserve -Recurse -Force
    }
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
