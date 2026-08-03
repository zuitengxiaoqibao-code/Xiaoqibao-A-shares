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
    "--port", $Port
) -PassThru
$StartedAt = [Diagnostics.Stopwatch]::StartNew()

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
        $StatusCode = [int]$_.Exception.Response.StatusCode
        $ErrorBody = $_.ErrorDetails.Message | ConvertFrom-Json
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
    Write-Host ("Portable smoke passed; window visible in {0}ms; API ready in {1}ms; overview {2}; quant strategy {3}" -f `
        $WindowVisibleMs, $StartedAt.ElapsedMilliseconds, $Overview.status, $QuantStrategyStatus)
} finally {
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
    }
    $ResolvedTempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $ResolvedSmokeRoot = [IO.Path]::GetFullPath($SmokeRoot)
    $IsSmokeDirectory = (Split-Path -Leaf $ResolvedSmokeRoot) -like `
        "xiaoqibao-smoke-*"
    if (
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
}
