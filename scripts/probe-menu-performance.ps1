. "$PSScriptRoot\verify-menu-performance.ps1"

$script:MenuDisplayNames = @{
    market_overview = "信息总览"
    today_decision = "今日研判"
    stock_observation = "个股观察"
    company_research = "公司研究"
    first_limit_up = "首次涨停"
    late_session_selection = "尾盘选股"
    quant_analysis = "量化分析"
    monitor_center = "监控中心"
    news = "新闻热点"
    risk = "风险提醒"
    history = "历史复盘"
    settings = "数据设置"
    operations = "本地运维"
    bonds = "可转债"
}
function Invoke-MenuPerformanceProbe {
    param(
        [Parameter(Mandatory = $true)][string]$BaseUri,
        [int]$TimeoutSec = 10,
        [int]$MaxResultMs = 10000,
        [int]$MaxCacheFrameMs = 1000
    )

    $Samples = @($script:RequiredMenuIds | ForEach-Object {
        $Menu = $_
        $Started = [Diagnostics.Stopwatch]::StartNew()
        try {
            $Snapshot = Invoke-RestMethod `
                -Uri ("{0}/api/v1/operations/page-snapshots/{1}" -f $BaseUri.TrimEnd('/'), $Menu) `
                -TimeoutSec $TimeoutSec
            $Started.Stop()
            [pscustomobject][ordered]@{
                menu = [string]$Snapshot.menu
                state = [string]$Snapshot.state
                latency_ms = [int]$Started.ElapsedMilliseconds
                cache_frame_ms = if ($null -eq $Snapshot.cache_frame_ms) { $null } else { [int]$Snapshot.cache_frame_ms }
                usable_content = [bool]$Snapshot.usable_content
                reason = [string]$Snapshot.reason
                observed_at = $Snapshot.observed_at
                trade_date = $Snapshot.trade_date
                source = [string]$Snapshot.source
                coverage = $Snapshot.coverage
            }
        } catch {
            $Started.Stop()
            $DisplayName = [string]$script:MenuDisplayNames[$Menu]
            [pscustomobject][ordered]@{
                menu = $Menu
                state = "error"
                latency_ms = [int]$Started.ElapsedMilliseconds
                cache_frame_ms = $null
                usable_content = $false
                reason = "${DisplayName}首屏请求失败：$($_.Exception.Message)"
                observed_at = (Get-Date).ToUniversalTime().ToString("o")
                trade_date = $null
                source = "portable-exe-probe"
                coverage = $null
            }
        }
    })

    return Test-MenuPerformance `
        -Samples $Samples `
        -MaxResultMs $MaxResultMs `
        -MaxCacheFrameMs $MaxCacheFrameMs
}
