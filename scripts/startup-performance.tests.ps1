Describe "startup performance summary" {
    BeforeAll {
        . "$PSScriptRoot\startup-performance.ps1"
    }

    It "separates cold and hot runs and calculates median and p95" {
        $runs = @(
            [pscustomobject]@{ kind = "cold"; state = "pass"; window_visible_ms = 240; api_ready_ms = 2800; full_verification_ms = 11000 },
            [pscustomobject]@{ kind = "hot"; state = "pass"; window_visible_ms = 120; api_ready_ms = 2200; full_verification_ms = 3200 },
            [pscustomobject]@{ kind = "hot"; state = "pass"; window_visible_ms = 140; api_ready_ms = 2600; full_verification_ms = 3400 },
            [pscustomobject]@{ kind = "hot"; state = "pass"; window_visible_ms = 160; api_ready_ms = 3000; full_verification_ms = 3600 }
        )

        $summary = Get-StartupPerformanceSummary -Runs $runs

        $summary.state | Should Be "pass"
        $summary.cold.count | Should Be 1
        $summary.hot.count | Should Be 3
        $summary.hot.api_ready_median_ms | Should Be 2600
        $summary.hot.api_ready_p95_ms | Should Be 3000
    }

    It "reports a warning when a run has missing timing evidence" {
        $runs = @(
            [pscustomobject]@{ kind = "cold"; state = "pass"; window_visible_ms = 240; api_ready_ms = $null; full_verification_ms = 11000 },
            [pscustomobject]@{ kind = "hot"; state = "pass"; window_visible_ms = 120; api_ready_ms = 2200; full_verification_ms = 3200 }
        )

        $summary = Get-StartupPerformanceSummary -Runs $runs

        $summary.state | Should Be "warning"
        ($summary.warnings -join "|") | Should Match "missing_api_ready_ms"
    }

    It "reports a warning when the window visibility threshold is exceeded" {
        $runs = @(
            [pscustomobject]@{ kind = "cold"; state = "pass"; window_visible_ms = 3201; api_ready_ms = 2800; full_verification_ms = 11000 },
            [pscustomobject]@{ kind = "hot"; state = "pass"; window_visible_ms = 120; api_ready_ms = 2200; full_verification_ms = 3200 }
        )

        $summary = Get-StartupPerformanceSummary -Runs $runs -MaxColdWindowMs 3000

        $summary.state | Should Be "warning"
        ($summary.warnings -join "|") | Should Match "cold_window_visible_ms_exceeded"
    }
}
