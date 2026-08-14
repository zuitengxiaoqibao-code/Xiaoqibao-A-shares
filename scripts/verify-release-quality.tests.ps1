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
            exe_sha256 = $hash
            persistent_dirs = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
        } | ConvertTo-Json
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
}
