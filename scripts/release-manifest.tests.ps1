Describe "release manifest runtime evidence" {
    BeforeEach {
        $script:fixture = Join-Path $TestDrive "release"
        New-Item -ItemType Directory -Force -Path (Join-Path $script:fixture "data") | Out-Null
        New-Item -ItemType Directory -Force -Path (Join-Path $script:fixture "logs") | Out-Null
        Set-Content -LiteralPath (Join-Path $script:fixture "xiaoqibao.exe") -Value "portable" -NoNewline
        Set-Content -LiteralPath (Join-Path $script:fixture "data\runtime.sqlite3") -Value "old" -NoNewline
        $manifest = [ordered]@{
            database_files = @([ordered]@{
                path = "data/runtime.sqlite3"
                bytes = 3
                sha256 = "OLD"
            })
            total_bytes = 0
            program_bytes = 0
            persistent_bytes = 0
        } | ConvertTo-Json -Depth 8
        Set-Content -LiteralPath (Join-Path $script:fixture "release-manifest.json") -Value $manifest -Encoding UTF8
        . "$PSScriptRoot\release-manifest.ps1"
    }

    It "refreshes database hashes and runtime size evidence after smoke" {
        Add-Content -LiteralPath (Join-Path $script:fixture "data\runtime.sqlite3") -Value "new" -NoNewline

        Update-ReleaseManifestRuntimeEvidence -ReleaseRoot $script:fixture

        $updated = Get-Content -Raw -LiteralPath (Join-Path $script:fixture "release-manifest.json") | ConvertFrom-Json
        $file = Get-Item -LiteralPath (Join-Path $script:fixture "data\runtime.sqlite3")
        $hash = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
        $updated.database_files[0].bytes | Should Be $file.Length
        $updated.database_files[0].sha256 | Should Be $hash
        ($null -ne $updated.runtime_observed_at -and $updated.runtime_observed_at.Length -gt 0) | Should Be $true
    }
}
