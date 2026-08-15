Describe "release manifest signature" {
    BeforeEach {
        $script:fixture = Join-Path $TestDrive "release"
        New-Item -ItemType Directory -Force -Path $script:fixture | Out-Null
        $manifest = [ordered]@{
            version = "20260815T000000Z"
            commit = "abc123"
            migration_version = 7
            database_files = @()
            persistent_dirs = @("config", "data")
        } | ConvertTo-Json -Depth 10
        [IO.File]::WriteAllText(
            (Join-Path $script:fixture "release-manifest.json"),
            $manifest,
            [Text.UTF8Encoding]::new($false)
        )
    }

    It "signs and verifies a release manifest" {
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture -Verify

        $signed = [IO.File]::ReadAllText(
            (Join-Path $script:fixture "release-manifest.json"),
            [Text.UTF8Encoding]::new($false)
        ) | ConvertFrom-Json
        $signed.manifest_signature.algorithm | Should Be "SHA256"
        $signed.manifest_signature.digest | Should Match "^[A-F0-9]{64}$"
    }

    It "rejects a manifest changed after signing" {
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture
        $path = Join-Path $script:fixture "release-manifest.json"
        $manifest = [IO.File]::ReadAllText($path, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        $manifest.commit = "tampered"
        [IO.File]::WriteAllText($path, ($manifest | ConvertTo-Json -Depth 10), [Text.UTF8Encoding]::new($false))

        $failed = $false
        try {
            & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $script:fixture -Verify
        } catch {
            $failed = $true
        }
        $failed | Should Be $true
    }
}
