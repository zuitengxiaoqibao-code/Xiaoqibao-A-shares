$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Missing .venv. Follow the README setup steps first."
}

$pnpmCommand = Get-Command pnpm.cmd -ErrorAction SilentlyContinue
if ($pnpmCommand) {
    $pnpm = $pnpmCommand.Source
} else {
    $pnpm = Join-Path $root "node_modules\.bin\pnpm.cmd"
}
if (-not (Test-Path $pnpm)) {
    throw "pnpm.cmd was not found. Install pnpm 10 or newer."
}

$api = Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "qibao_api.main:app", "--reload", "--port", "8000" `
    -WorkingDirectory (Join-Path $root "apps\api") `
    -WindowStyle Hidden `
    -PassThru

Write-Host "API started (PID $($api.Id)) at http://127.0.0.1:8000"
Write-Host "Web application starting at http://127.0.0.1:5173"
try {
    & $pnpm --dir (Join-Path $root "apps\web") dev --host 127.0.0.1
} finally {
    # Kill only the process tree started above, including uvicorn's reload worker.
    if (-not $api.HasExited) {
        & taskkill.exe /PID $api.Id /T /F 2>$null | Out-Null
    }
}

