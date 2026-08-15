Describe "portable restore drill" {
    BeforeEach {
        $script:fixture = Join-Path $TestDrive "release"
        New-Item -ItemType Directory -Force -Path $script:fixture | Out-Null
        @("config", "data", "news", "cache", "logs", "models", "exports", "backups", "web") | ForEach-Object {
            New-Item -ItemType Directory -Force -Path (Join-Path $script:fixture $_) | Out-Null
        }
        [IO.File]::WriteAllText((Join-Path $script:fixture "xiaoqibao.exe"), "portable", [Text.Encoding]::ASCII)
        [IO.File]::WriteAllText((Join-Path $script:fixture "data\market.sqlite3"), "verified-data", [Text.Encoding]::ASCII)
        [IO.File]::WriteAllText((Join-Path $script:fixture ".migration-version"), "7", [Text.Encoding]::ASCII)
        $database = Get-Item -LiteralPath (Join-Path $script:fixture "data\market.sqlite3")
        $manifest = [ordered]@{
            commit = "abc123"
            migration_version = 7
            database_files = @([ordered]@{
                path = "data/market.sqlite3"
                bytes = $database.Length
                sha256 = (Get-FileHash -LiteralPath $database.FullName -Algorithm SHA256).Hash
            })
            persistent_dirs = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
            restore_drill = [ordered]@{ status = "pending"; mode = "temporary-copy" }
        } | ConvertTo-Json -Depth 10
        [IO.File]::WriteAllText((Join-Path $script:fixture "release-manifest.json"), $manifest, [Text.UTF8Encoding]::new($false))
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture
    }

    It "verifies copied database hashes and migrations in a temporary directory" {
        $resultPath = Join-Path $TestDrive "restore-result.json"
        $sourceHash = (Get-FileHash -LiteralPath (Join-Path $script:fixture "data\market.sqlite3") -Algorithm SHA256).Hash

        & "$PSScriptRoot\verify-restore-drill.ps1" -ReleaseRoot $script:fixture -SkipApiProbe -ResultPath $resultPath

        $result = [IO.File]::ReadAllText($resultPath, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        $result.status | Should Be "pass"
        $result.database_count | Should Be 1
        $result.migration_version | Should Be 7
        $result.critical_api_status | Should Be "skipped_for_test"
        (Get-FileHash -LiteralPath (Join-Path $script:fixture "data\market.sqlite3") -Algorithm SHA256).Hash | Should Be $sourceHash
    }

    It "rejects a database that no longer matches the signed manifest" {
        [IO.File]::AppendAllText((Join-Path $script:fixture "data\market.sqlite3"), "tampered", [Text.Encoding]::ASCII)
        $failed = $false
        try {
            & "$PSScriptRoot\verify-restore-drill.ps1" -ReleaseRoot $script:fixture -SkipApiProbe
        } catch {
            $failed = $true
        }
        $failed | Should Be $true
    }
}
