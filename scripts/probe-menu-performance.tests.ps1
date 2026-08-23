Describe "portable fourteen-menu performance probe" {
    BeforeAll {
        . "$PSScriptRoot\probe-menu-performance.ps1"
    }

    It "probes every menu snapshot and returns a passing gate" {
        Mock Invoke-RestMethod {
            $menu = ($Uri -split "/")[-1]
            [pscustomobject]@{
                menu = $menu
                state = "ready"
                latency_ms = 1
                cache_frame_ms = 1
                usable_content = $true
                reason = ""
                observed_at = "2026-08-23T00:00:00Z"
                trade_date = "2026-08-22"
                source = "shared-snapshot-registry"
                coverage = 99.9
            }
        }

        $result = Invoke-MenuPerformanceProbe -BaseUri "http://127.0.0.1:18765"

        $result.state | Should Be "pass"
        $result.checked_count | Should Be 14
        $result.menus.Count | Should Be 14
        Assert-MockCalled Invoke-RestMethod -Times 14 -Exactly
    }

    It "records a concrete Chinese reason when a menu request fails" {
        Mock Invoke-RestMethod {
            if ($Uri -match "/news$") { throw "connection refused" }
            $menu = ($Uri -split "/")[-1]
            [pscustomobject]@{
                menu = $menu
                state = "ready"
                latency_ms = 1
                cache_frame_ms = 1
                usable_content = $true
                reason = ""
            }
        }

        $result = Invoke-MenuPerformanceProbe -BaseUri "http://127.0.0.1:18765"
        $news = @($result.menus | Where-Object menu -eq "news")[0]

        $result.state | Should Be "pass"
        $news.state | Should Be "error"
        $news.usable_content | Should Be $false
        $news.reason | Should Match "新闻热点首屏请求失败"
    }
}
