param([int]$Port = 18797)
$ErrorActionPreference = "Stop"
$Project = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Exe = Join-Path $Project "dist\XiaoQiBao-Portable\xiaoqibao.exe"
$ProbeRoot = Join-Path $env:TEMP ("yishu-eltdx-frozen-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $ProbeRoot | Out-Null
$PreviousScheduler = [Environment]::GetEnvironmentVariable("QIBAO_SCHEDULER_ENABLED", "Process")
$env:QIBAO_SCHEDULER_ENABLED = "false"
$ProbeProcess = $null
try {
    $ProbeProcess = Start-Process -FilePath $Exe -ArgumentList @(
        "--portable-root", $ProbeRoot, "--port", $Port,
        "--instance-name", "yishu-frozen-adapter-probe", "--headless"
    ) -WindowStyle Hidden -PassThru
    $Deadline = [DateTime]::UtcNow.AddSeconds(25)
    $Log = Join-Path $ProbeRoot "logs\xiaoqibao.log"
    do {
        Start-Sleep -Milliseconds 300
        $Ready = (Test-Path -LiteralPath $Log) -and (Select-String -LiteralPath $Log -Pattern "stage=lifespan-ready" -Quiet)
    } while (-not $Ready -and [DateTime]::UtcNow -lt $Deadline -and -not $ProbeProcess.HasExited)
    if (-not $Ready) { throw "Frozen API startup failed; inspect $Log" }
    $Timer = [Diagnostics.Stopwatch]::StartNew()
    # Only this disposable probe database is written; never use the user root.
    $Result = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/api/v1/a-shares/600000/history/sync?limit=300" -TimeoutSec 20
    $Result | Select-Object state,written_rows,source,attempts | ConvertTo-Json -Depth 5
    Write-Output "FROZEN_SYNC_MS=$($Timer.ElapsedMilliseconds)"
    if ($Result.state -ne "ready" -or $Result.source -ne "eltdx" -or $Result.written_rows -ne 300) {
        throw "Frozen eltdx did not produce 300 valid daily bars"
    }
} finally {
    if ($null -ne $ProbeProcess -and -not $ProbeProcess.HasExited) {
        Stop-Process -Id $ProbeProcess.Id
    }
    if ($null -eq $PreviousScheduler) {
        Remove-Item Env:QIBAO_SCHEDULER_ENABLED -ErrorAction SilentlyContinue
    } else {
        $env:QIBAO_SCHEDULER_ENABLED = $PreviousScheduler
    }
    Write-Output "PROBE_ROOT=$ProbeRoot"
}
