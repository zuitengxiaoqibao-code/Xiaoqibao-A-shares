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
            quality_gates = [ordered]@{
                state = "pass"
                domain_status = [ordered]@{
                    overview = [ordered]@{ status = "ready" }
                    quant_strategy = [ordered]@{ status = "partial" }
                    company_research = [ordered]@{ status = "partial" }
                    tdx_professional = [ordered]@{ status = "unavailable" }
                }
            }
        } | ConvertTo-Json -Depth 10
        Set-Content -LiteralPath (Join-Path $script:fixture "release-manifest.json") -Value $manifest -Encoding UTF8
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
        Set-Content -LiteralPath $manifestPath -Value ($manifest | ConvertTo-Json -Depth 10) -Encoding UTF8
        $failed = $false
        try { & "$PSScriptRoot\verify-release-quality.ps1" -ReleaseRoot $script:fixture } catch { $failed = $true }
        $failed | Should Be $true
    }
}
