param([int]$Port = 18765)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Exe = Join-Path $Root "dist\XiaoQiBao-Portable\xiaoqibao.exe"
$SmokeRoot = Join-Path $env:TEMP (
    "xiaoqibao-smoke-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
Copy-Item -LiteralPath (Join-Path $Root "dist\XiaoQiBao-Portable\web") `
    -Destination (Join-Path $SmokeRoot "web") -Recurse
$Process = Start-Process -FilePath $Exe -ArgumentList @(
    "--portable-root", $SmokeRoot,
    "--port", $Port,
    "--headless"
) -PassThru -WindowStyle Hidden

try {
    $Health = $null
    $Deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $Health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$Port/health" `
                -TimeoutSec 1
            break
        } catch {
            Start-Sleep -Milliseconds 200
        }
    } while ([DateTime]::UtcNow -lt $Deadline)

    if ($null -eq $Health) { throw "Portable health check timed out" }
    $HomeResponse = Invoke-WebRequest `
        -Uri "http://127.0.0.1:$Port/" `
        -TimeoutSec 5 `
        -UseBasicParsing
    if (
        $HomeResponse.StatusCode -ne 200 -or
        $HomeResponse.Content -notmatch "id=.root."
    ) {
        throw "Portable frontend smoke failed"
    }
    Write-Host "Portable smoke passed"
} finally {
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
    }
}
