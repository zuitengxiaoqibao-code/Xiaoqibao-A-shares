Describe "menu performance gate" {
    BeforeAll {
        . "$PSScriptRoot\verify-menu-performance.ps1"
        $script:menuIds = @(
            "market_overview", "today_decision", "stock_observation", "company_research",
            "first_limit_up", "late_session_selection", "quant_analysis", "monitor_center",
            "news", "risk", "history", "settings", "operations", "bonds"
        )
    }

    It "accepts all menus when each returns content or an explicit fallback within ten seconds" {
        $samples = @($script:menuIds | ForEach-Object {
            [pscustomobject]@{
                menu = $_
                state = if ($_ -eq "company_research") { "partial" } else { "ready" }
                latency_ms = 900
                cache_frame_ms = 180
                usable_content = $true
                reason = if ($_ -eq "company_research") { "财务来源尚在后台补齐" } else { "" }
            }
        })

        $result = Test-MenuPerformance -Samples $samples

        $result.state | Should Be "pass"
        $result.checked_count | Should Be 14
        $result.failures.Count | Should Be 0
    }

    It "rejects a missing menu" {
        $samples = @($script:menuIds[0..12] | ForEach-Object {
            [pscustomobject]@{ menu = $_; state = "ready"; latency_ms = 100; usable_content = $true }
        })

        $result = Test-MenuPerformance -Samples $samples

        $result.state | Should Be "fail"
        ($result.failures -join "|") | Should Match "missing_menu:bonds"
    }

    It "rejects a menu that exceeds ten seconds" {
        $samples = @($script:menuIds | ForEach-Object {
            [pscustomobject]@{
                menu = $_
                state = "ready"
                latency_ms = if ($_ -eq "quant_analysis") { 10001 } else { 100 }
                usable_content = $true
            }
        })

        $result = Test-MenuPerformance -Samples $samples

        $result.state | Should Be "fail"
        ($result.failures -join "|") | Should Match "latency_exceeded:quant_analysis"
    }

    It "rejects an empty fallback without a concrete reason" {
        $samples = @($script:menuIds | ForEach-Object {
            [pscustomobject]@{
                menu = $_
                state = if ($_ -eq "news") { "unavailable" } else { "ready" }
                latency_ms = 100
                usable_content = ($_ -ne "news")
                reason = ""
            }
        })

        $result = Test-MenuPerformance -Samples $samples

        $result.state | Should Be "fail"
        ($result.failures -join "|") | Should Match "empty_result_without_reason:news"
    }
}
