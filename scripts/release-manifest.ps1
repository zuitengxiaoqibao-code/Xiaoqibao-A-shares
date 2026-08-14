function Update-ReleaseManifestRuntimeEvidence {
    param(
        [Parameter(Mandatory = $true)][string]$ReleaseRoot
    )

    $Root = (Resolve-Path -LiteralPath $ReleaseRoot).Path
    $ManifestPath = Join-Path $Root "release-manifest.json"
    if (-not (Test-Path -LiteralPath $ManifestPath -PathType Leaf)) {
        throw "Release manifest is missing: $ManifestPath"
    }

    $Manifest = [IO.File]::ReadAllText(
        $ManifestPath,
        [Text.UTF8Encoding]::new($false)
    ) | ConvertFrom-Json
    $DatabaseFiles = @(Get-ChildItem -LiteralPath (Join-Path $Root "data") -Recurse -File |
        Where-Object { $_.Extension -in @(".sqlite3", ".duckdb", ".db") } |
        ForEach-Object {
            [ordered]@{
                path = $_.FullName.Substring($Root.Length).TrimStart('\').Replace('\', '/')
                bytes = $_.Length
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        })
    $Files = @(Get-ChildItem -LiteralPath $Root -Recurse -File)
    $Bytes = ($Files | Measure-Object Length -Sum).Sum
    $PersistentNames = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
    $PersistentBytes = 0
    foreach ($Name in $PersistentNames) {
        $Path = Join-Path $Root $Name
        if (Test-Path -LiteralPath $Path -PathType Container) {
            $PersistentBytes += (Get-ChildItem -LiteralPath $Path -Recurse -File |
                Measure-Object Length -Sum).Sum
        }
    }

    $Manifest.database_files = $DatabaseFiles
    $Manifest.total_bytes = $Bytes
    $Manifest.persistent_bytes = $PersistentBytes
    $Manifest.program_bytes = [Math]::Max(0, $Bytes - $PersistentBytes)
    $RuntimeObservedAt = (Get-Date).ToUniversalTime().ToString("o")
    if ($Manifest.PSObject.Properties.Name -contains "runtime_observed_at") {
        $Manifest.runtime_observed_at = $RuntimeObservedAt
    } else {
        $Manifest | Add-Member -MemberType NoteProperty -Name runtime_observed_at -Value $RuntimeObservedAt
    }
    $ManifestJson = $Manifest | ConvertTo-Json -Depth 12
    if ($ManifestJson -match '\uFFFD|[\u00C3\u00C2\u00E5\u00E6\u00E7\u00E8\u00E9\u00EF\u00F0][^\r\n]{0,2}[\u0080-\u00BF]') {
        throw "Release manifest contains invalid UTF-8 diagnostic text"
    }
    [IO.File]::WriteAllText($ManifestPath, $ManifestJson, [Text.UTF8Encoding]::new($false))
}
