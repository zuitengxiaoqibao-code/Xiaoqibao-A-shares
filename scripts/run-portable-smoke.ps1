param(
    [int]$Port = 18765,
    [switch]$KeepSmokeRoot,
    [switch]$UseReleaseData
)

$ErrorActionPreference = "Stop"
$Utf8 = [Text.UTF8Encoding]::new($false)
$OutputEncoding = $Utf8
try { [Console]::OutputEncoding = $Utf8 } catch { }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Exe = Join-Path $Root "dist\XiaoQiBao-Portable\xiaoqibao.exe"
$ReleaseRoot = Join-Path $Root "dist\XiaoQiBao-Portable"
if ($UseReleaseData) {
    $SmokeRoot = $ReleaseRoot
    if (-not (Test-Path -LiteralPath $SmokeRoot)) {
        throw "Portable release directory was not found: $SmokeRoot"
    }
    Write-Host ("Release data mode: using persistent portable root {0}" -f $SmokeRoot)
} else {
    $SmokeRoot = Join-Path $env:TEMP (
        "xiaoqibao-smoke-" + [guid]::NewGuid().ToString("N")
    )
    New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $ReleaseRoot "web") `
        -Destination (Join-Path $SmokeRoot "web") -Recurse
}
$Process = Start-Process -FilePath $Exe -ArgumentList @(
    "--portable-root", $SmokeRoot,
    "--port", $Port
) -PassThru
$StartedAt = [Diagnostics.Stopwatch]::StartNew()
$LogPath = Join-Path $SmokeRoot "logs\xiaoqibao.log"

try {
    $WindowVisibleMs = $null
    $WindowDeadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $Process.Refresh()
        if ($Process.MainWindowHandle -ne 0) {
            $WindowVisibleMs = $StartedAt.ElapsedMilliseconds
            break
        }
        Start-Sleep -Milliseconds 25
    } while ([DateTime]::UtcNow -lt $WindowDeadline -and -not $Process.HasExited)

    if ($null -eq $WindowVisibleMs) { throw "Portable desktop window was not created" }
    if ($WindowVisibleMs -gt 3000) {
        throw "Portable desktop window exceeded 3 second target: ${WindowVisibleMs}ms"
    }

    # The portable server pre-binds its loopback socket before importing the
    # API.  Probing that socket too early can leave a cancelled Windows
    # proactor accept behind and make a healthy server look unavailable.  Wait
    # for the final lifespan log stage before issuing the first HTTP request.
    $LifespanReady = $false
    $LifespanDeadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        if (Test-Path -LiteralPath $LogPath) {
            $StartupLog = Get-Content -LiteralPath $LogPath -Raw -ErrorAction SilentlyContinue
            if ($StartupLog -match "desktop startup stage=lifespan-ready") {
                $LifespanReady = $true
                Start-Sleep -Milliseconds 100
                break
            }
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $LifespanDeadline -and -not $Process.HasExited)
    if (-not $LifespanReady) {
        throw "Portable lifespan readiness log was not observed"
    }

    $Health = $null
    $HealthReadyMs = $null
    $Deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $Health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$Port/health" `
                -TimeoutSec 1
            $HealthReadyMs = $StartedAt.ElapsedMilliseconds
            break
        } catch {
            Start-Sleep -Milliseconds 200
        }
    } while ([DateTime]::UtcNow -lt $Deadline)

    if ($null -eq $Health) {
        $Process.Refresh()
        Write-Warning (
            "Portable health timeout diagnostics: pid={0}; cpu={1:N1}s; working_set={2:N1}MB; threads={3}" -f
            $Process.Id,
            $Process.CPU,
            ($Process.WorkingSet64 / 1MB),
            $Process.Threads.Count
        )
        if (Test-Path -LiteralPath $LogPath) {
            Get-Content -LiteralPath $LogPath -Tail 80 | Write-Warning
        }
        throw "Portable health check timed out"
    }
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
    $Overview = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/a-shares/market-overview" `
        -TimeoutSec 30
    if ($Overview.status -notin @("ready", "partial", "unavailable")) {
        throw "Portable market overview did not return an honest data status"
    }
    $QuantStrategy = $null
    $QuantStrategyStatus = $null
    try {
        $QuantStrategy = Invoke-RestMethod `
            -Uri "http://127.0.0.1:$Port/api/v1/a-shares/quant-strategy?limit=12" `
            -TimeoutSec 30
    } catch {
        $QuantError = $_
        $StatusCode = [int]$QuantError.Exception.Response.StatusCode
        $RawErrorBody = $QuantError.ErrorDetails.Message
        try {
            $ErrorBody = $RawErrorBody | ConvertFrom-Json -ErrorAction Stop
        } catch {
            throw (
                "Portable quant strategy returned HTTP {0} with non-JSON error body: {1}" -f
                $StatusCode,
                $RawErrorBody
            )
        }
        if (
            $StatusCode -ne 503 -or
            $ErrorBody.detail.code -ne "quant_strategy_unavailable"
        ) {
            throw
        }
        $QuantStrategyStatus = "unavailable"
    }
    if ($null -ne $QuantStrategy) {
        if ($QuantStrategy.status -notin @("ready", "partial", "unavailable")) {
            throw "Portable quant strategy did not return an honest data status"
        }
        if ($QuantStrategy.formula_version -ne "a-share-short-strategy-v2.0") {
            throw "Portable quant strategy formula version is incorrect"
        }
        if ($QuantStrategy.strategy_models.Count -ne 6) {
            throw "Portable quant strategy did not expose all six strategy models"
        }
        $QuantStrategyStatus = $QuantStrategy.status
    }
    $Professional = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/tdx/local/professional?method=get_financial_data&table_list=Fn193&stock_codes=600000" `
        -TimeoutSec 30
    if ($Professional.status -notin @("ready", "partial", "unavailable")) {
        throw "Portable TDX professional probe did not return an honest data status"
    }
    $QuantDetail = if ($null -ne $QuantStrategy) {
        if ($QuantStrategy.status -eq "partial") {
            "candidates=$($QuantStrategy.candidates.Count); coverage=$($QuantStrategy.regime.coverage_percent)%"
        } else {
            "candidates=$($QuantStrategy.candidates.Count)"
        }
    } elseif ($null -ne $ErrorBody.detail.reason) {
        $ErrorBody.detail.reason
    } else {
        "unavailable"
    }
    $ProfessionalDetail = if ($Professional.detail) { $Professional.detail } else { "rows=$($Professional.rows.Count)" }
    Write-Host ("Portable smoke passed; window visible in {0}ms; API ready in {1}ms; verification completed in {2}ms; overview {3}; quant strategy {4} ({5}); tdx professional {6} ({7})" -f `
        $WindowVisibleMs, $HealthReadyMs, $StartedAt.ElapsedMilliseconds, $Overview.status, $QuantStrategyStatus, $QuantDetail, $Professional.status, $ProfessionalDetail)
} finally {
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
    }
    if (-not $UseReleaseData) {
        $ResolvedTempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
        $ResolvedSmokeRoot = [IO.Path]::GetFullPath($SmokeRoot)
        $IsSmokeDirectory = (Split-Path -Leaf $ResolvedSmokeRoot) -like `
            "xiaoqibao-smoke-*"
        if (
            -not $KeepSmokeRoot -and
            $IsSmokeDirectory -and
            $ResolvedSmokeRoot.StartsWith(
                $ResolvedTempRoot,
                [StringComparison]::OrdinalIgnoreCase
            ) -and
            (Test-Path -LiteralPath $ResolvedSmokeRoot)
        ) {
            $CleanupDeadline = [DateTime]::UtcNow.AddSeconds(5)
            do {
                try {
                    Remove-Item `
                        -LiteralPath $ResolvedSmokeRoot `
                        -Recurse `
                        -Force `
                        -ErrorAction Stop
                    break
                } catch [IO.IOException] {
                    if ([DateTime]::UtcNow -ge $CleanupDeadline) { throw }
                    Start-Sleep -Milliseconds 100
                }
            } while (Test-Path -LiteralPath $ResolvedSmokeRoot)
        }
        if ($KeepSmokeRoot) {
            Write-Host ("Portable smoke root retained: {0}" -f $SmokeRoot)
        }
    } else {
        Write-Host ("Release data mode: persistent data retained at {0}" -f $SmokeRoot)
    }
}
