Describe "verify-release-quality" {
    BeforeEach {
        $script:fixture = Join-Path $TestDrive "release"
        New-Item -ItemType Directory -Force -Path $script:fixture | Out-Null
        Set-Content -LiteralPath (Join-Path $script:fixture "xiaoqibao.exe") -Value "portable" -NoNewline
        @("config", "data", "news", "cache", "logs", "models", "exports", "backups") | ForEach-Object {
            New-Item -ItemType Directory -Force -Path (Join-Path $script:fixture $_) | Out-Null
        }
        $hash = (Get-FileHash -LiteralPath (Join-Path $script:fixture "xiaoqibao.exe") -Algorithm SHA256).Hash
        $manifest = [ordered]@{
            commit = "abc123"
            source_state = "clean"
            migration_version = 1
            exe_sha256 = $hash
            database_files = @()
            persistent_dirs = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
            restore_drill = [ordered]@{
                status = "pass"
                mode = "temporary-copy"
                critical_api_status = "pass"
            }
            quality_gates = [ordered]@{
                state = "pass"
                domain_status = [ordered]@{
                    overview = [ordered]@{ status = "ready" }
                    quant_strategy = [ordered]@{ status = "partial" }
                    company_research = [ordered]@{ status = "partial" }
                    tdx_professional = [ordered]@{ status = "unavailable" }
                }
                startup_metrics = [ordered]@{
                    kind = "hot"
                    state = "pass"
                    window_visible_ms = 100
                    api_ready_ms = 2000
                    full_verification_ms = 3000
                    observed_at = "2026-08-15T00:00:00Z"
                }
            }
        } | ConvertTo-Json -Depth 10
        [IO.File]::WriteAllText(
            (Join-Path $script:fixture "release-manifest.json"),
            $manifest,
            [Text.UTF8Encoding]::new($false)
        )
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture
    }

    It "accepts a complete release" {
        $succeeded = $true
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $succeeded = $false }
        $succeeded | Should Be $true
    }

    It "rejects a release missing persistent state" {
        Remove-Item -LiteralPath (Join-Path $script:fixture "news") -Recurse -Force
        $failed = $false
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $failed = $true }
        $failed | Should Be $true
    }

    It "rejects a release without domain status evidence" {
        $manifestPath = Join-Path $script:fixture "release-manifest.json"
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        $manifest.quality_gates.PSObject.Properties.Remove("domain_status")
        $manifest.PSObject.Properties.Remove("manifest_signature")
        [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture
        $failed = $false
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $failed = $true }
        $failed | Should Be $true
    }

    It "rejects a release without startup performance evidence" {
        $manifestPath = Join-Path $script:fixture "release-manifest.json"
        $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
        $manifest.quality_gates.PSObject.Properties.Remove("startup_metrics")
        $manifest.PSObject.Properties.Remove("manifest_signature")
        [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture
        $failed = $false
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $failed = $true }
        $failed | Should Be $true
    }

    It "rejects a manifest changed after signing" {
        $manifestPath = Join-Path $script:fixture "release-manifest.json"
        $manifest = [IO.File]::ReadAllText($manifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        $manifest.commit = "tampered"
        [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))

        $failed = $false
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $failed = $true }
        $failed | Should Be $true
    }

    It "rejects a release whose restore drill has not passed" {
        $manifestPath = Join-Path $script:fixture "release-manifest.json"
        $manifest = [IO.File]::ReadAllText($manifestPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        $manifest.restore_drill.status = "pending"
        $manifest.PSObject.Properties.Remove("manifest_signature")
        [IO.File]::WriteAllText($manifestPath, ($manifest | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture

        $failed = $false
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $failed = $true }
        $failed | Should Be $true
    }
}
