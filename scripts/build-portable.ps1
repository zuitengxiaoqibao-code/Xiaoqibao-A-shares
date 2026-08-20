param([switch]$SkipTests)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Release = Join-Path $Root "dist\XiaoQiBao-Portable"
$DistRoot = Join-Path $Root "dist"
$ReleaseExe = Join-Path $Release "xiaoqibao.exe"
$ReleaseInUse = @(Get-CimInstance Win32_Process -Filter "Name='xiaoqibao.exe'" -ErrorAction SilentlyContinue |
    Where-Object {
        $_.ExecutablePath -and
        ([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($ReleaseExe))
    })
$BuildDist = $DistRoot
$PersistentFallback = $null
if ($ReleaseInUse.Count -gt 0) {
    # Never remove or overwrite a release that a user is currently viewing.
    # PyInstaller's COLLECT step deletes its output directory before writing;
    # stage the new build beside the live release instead.
    $BuildDist = Join-Path $DistRoot ("XiaoQiBao-Portable-staged-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $BuildDist | Out-Null
    Write-Host ("Live portable release detected (PID {0}); staging new build at {1}" -f ($ReleaseInUse.ProcessId -join ","), $BuildDist)
    $PersistentFallback = Get-ChildItem -LiteralPath $DistRoot -Directory -Filter "XiaoQiBao-Portable-staged-*" -ErrorAction SilentlyContinue |
        Where-Object {
            $candidate = Join-Path $_.FullName "XiaoQiBao-Portable"
            (Test-Path (Join-Path $candidate "xiaoqibao.exe")) -and
            (Test-Path (Join-Path $candidate "data\market.duckdb")) -and
            ([IO.Path]::GetFullPath($candidate) -ine [IO.Path]::GetFullPath($Release))
        } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
    if ($PersistentFallback) {
        $PersistentFallback = Join-Path $PersistentFallback "XiaoQiBao-Portable"
        Write-Host ("Locked persistence fallback: {0}" -f $PersistentFallback)
    }
}
$env:PYTHONUTF8 = "1"
$PersistentNames = @(
    "config", "data", "news", "cache", "logs", "models", "exports", "backups"
)
$TransientFilePatterns = @(
    "*.lock", "*-wal", "*-shm", "*.tmp", "*.part"
)

function Copy-PersistentTree {
    param(
        [Parameter(Mandatory = $true)][string]$Source,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath $Source)) {
        return
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    $SourceRoot = (Resolve-Path -LiteralPath $Source).Path.TrimEnd('\') + '\'
    $sourceName = Split-Path -Leaf $Source.TrimEnd('\')
    Get-ChildItem -LiteralPath $Source -Recurse -File -Force |
        Where-Object {
            $name = $_.Name
            -not ($TransientFilePatterns | Where-Object { $name -like $_ })
        } |
        ForEach-Object {
            $relative = $_.FullName.Substring($SourceRoot.Length)
            $target = Join-Path $Destination $relative
            $targetParent = Split-Path -Parent $target
            New-Item -ItemType Directory -Force -Path $targetParent | Out-Null
            try {
                Copy-Item -LiteralPath $_.FullName -Destination $target -Force
            } catch {
                if (-not $PersistentFallback) { throw }
                $fallbackFile = Join-Path $PersistentFallback (Join-Path $sourceName $relative)
                if (-not (Test-Path -LiteralPath $fallbackFile)) { throw }
                Write-Warning ("Using fallback for locked file: {0}" -f $relative)
                Copy-Item -LiteralPath $fallbackFile -Destination $target -Force
            }
        }
}

if (-not $SkipTests) {
    $PreviousDataDir = [Environment]::GetEnvironmentVariable("QIBAO_DATA_DIR", "Process")
    $env:QIBAO_DATA_DIR = Join-Path $env:TEMP (
        "qibao-build-test-" + [guid]::NewGuid().ToString("N")
    )
    try {
        & $Python -m pytest (Join-Path $Root "apps\api\tests") -q
        if ($LASTEXITCODE -ne 0) { throw "API tests failed" }
    } finally {
        if ($null -eq $PreviousDataDir) {
            Remove-Item Env:QIBAO_DATA_DIR -ErrorAction SilentlyContinue
        } else {
            $env:QIBAO_DATA_DIR = $PreviousDataDir
        }
    }

    & pnpm.cmd --dir $Root --filter "@qibao/web" test
    if ($LASTEXITCODE -ne 0) { throw "Web tests failed" }
}

& pnpm.cmd --dir $Root --filter "@qibao/web" build
if ($LASTEXITCODE -ne 0) { throw "Web build failed" }

$PreserveRoot = Join-Path $env:TEMP (
    "xiaoqibao-persistent-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $PreserveRoot | Out-Null
foreach ($Name in $PersistentNames) {
    $Source = Join-Path $Release $Name
    if (Test-Path -LiteralPath $Source) {
        Copy-PersistentTree -Source $Source -Destination (Join-Path $PreserveRoot $Name)
    }
}

try {
    & $Python -m PyInstaller `
        --noconfirm `
        --clean `
        --distpath $BuildDist `
        --workpath (Join-Path $Root "build") `
        (Join-Path $Root "packaging\xiaoqibao.spec")
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

    $BuiltRelease = Join-Path $BuildDist "XiaoQiBao-Portable"
    $WebTarget = Join-Path $BuiltRelease "web"
    New-Item -ItemType Directory -Force -Path $WebTarget | Out-Null
    Copy-Item -Path (Join-Path $Root "apps\web\dist\*") `
        -Destination $WebTarget -Recurse -Force
} finally {
    if ($null -eq $BuiltRelease) {
        $BuiltRelease = Join-Path $BuildDist "XiaoQiBao-Portable"
    }
    foreach ($Name in $PersistentNames) {
        $Target = Join-Path $BuiltRelease $Name
        New-Item -ItemType Directory -Force -Path $Target | Out-Null
        $Saved = Join-Path $PreserveRoot $Name
        if (Test-Path -LiteralPath $Saved) {
            Copy-PersistentTree -Source $Saved -Destination $Target
        }
    }
    $ResolvedPreserve = [IO.Path]::GetFullPath($PreserveRoot)
    $ResolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    if ($ResolvedPreserve.StartsWith($ResolvedTemp)) {
        Remove-Item -LiteralPath $ResolvedPreserve -Recurse -Force
    }
}

$Files = Get-ChildItem -LiteralPath $BuiltRelease -Recurse -File
$Bytes = ($Files | Measure-Object Length -Sum).Sum
$PersistentBytes = 0
foreach ($Name in $PersistentNames) {
    $PersistentPath = Join-Path $BuiltRelease $Name
    if (Test-Path -LiteralPath $PersistentPath) {
        $PersistentBytes += (Get-ChildItem -LiteralPath $PersistentPath -Recurse -File |
            Measure-Object Length -Sum).Sum
    }
}
$ProgramBytes = [Math]::Max(0, $Bytes - $PersistentBytes)
$IncrementalCopyBytes = $ProgramBytes
$PreviousManifestPath = Join-Path $Release "release-manifest.json"
if (Test-Path -LiteralPath $PreviousManifestPath) {
    try {
        $PreviousManifest = Get-Content -LiteralPath $PreviousManifestPath -Raw -Encoding UTF8 |
            ConvertFrom-Json
        if ($null -ne $PreviousManifest.program_files) {
            $PreviousFiles = @{}
            foreach ($Entry in $PreviousManifest.program_files) {
                $PreviousFiles[$Entry.path] = $Entry.sha256
            }
            $IncrementalCopyBytes = 0
            foreach ($File in $Files) {
                $Relative = $File.FullName.Substring($BuiltRelease.Length).TrimStart('\').Replace('\', '/')
                $Top = $Relative.Split('/')[0]
                if ($PersistentNames -contains $Top) { continue }
                $Hash = (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash
                if (-not $PreviousFiles.ContainsKey($Relative) -or $PreviousFiles[$Relative] -ne $Hash) {
                    $IncrementalCopyBytes += $File.Length
                }
            }
        }
    } catch {
        Write-Warning "Previous release manifest could not be read; incremental copy uses full program size."
    }
}
$ProgramFiles = @($Files | ForEach-Object {
    $Relative = $_.FullName.Substring($BuiltRelease.Length).TrimStart('\').Replace('\', '/')
    $Top = $Relative.Split('/')[0]
    if ($PersistentNames -notcontains $Top) {
        [ordered]@{
            path = $Relative
            bytes = $_.Length
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    }
} | Where-Object { $null -ne $_ })
$Commit = (& git -C $Root rev-parse HEAD 2>$null).Trim()
$SourceState = [Environment]::GetEnvironmentVariable("QIBAO_SOURCE_STATE", "Process")
if ($SourceState -notin @("clean", "dirty", "unknown")) {
    $SourceState = if ((& git -C $Root status --porcelain 2>$null)) { "dirty" } else { "clean" }
}
$LockHash = (Get-FileHash -LiteralPath (Join-Path $Root "pnpm-lock.yaml") -Algorithm SHA256).Hash
$MigrationVersion = [int](& $Python -c "from qibao_desktop.data_migration import CURRENT_MIGRATION_VERSION; print(CURRENT_MIGRATION_VERSION)")
if ($LASTEXITCODE -ne 0) { throw "Migration version could not be resolved" }
[IO.File]::WriteAllText(
    (Join-Path $BuiltRelease ".migration-version"),
    $MigrationVersion.ToString(),
    [Text.Encoding]::ASCII
)
$DatabaseFiles = @(Get-ChildItem -LiteralPath (Join-Path $BuiltRelease "data") -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".sqlite3", ".duckdb", ".db") } |
    ForEach-Object {
        [ordered]@{
            path = $_.FullName.Substring($BuiltRelease.Length).TrimStart('\').Replace('\', '/')
            bytes = $_.Length
            sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
        }
    })
$ExeHash = $null
$ExePath = Join-Path $BuiltRelease "xiaoqibao.exe"
if (Test-Path -LiteralPath $ExePath) {
    $ExeHash = (Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
}
$LatestBackup = Get-ChildItem -LiteralPath (Join-Path $BuiltRelease "backups") -Directory -Filter "backup-*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTimeUtc -Descending |
    Select-Object -First 1
$BackupBaseline = if ($null -eq $LatestBackup) {
    [ordered]@{
        status = "unavailable"
        latest_backup = $null
        file_count = 0
        bytes = 0
        observed_at = (Get-Date).ToUniversalTime().ToString("o")
    }
} else {
    $BackupFiles = @(Get-ChildItem -LiteralPath $LatestBackup.FullName -Recurse -File -Force)
    [ordered]@{
        status = "ready"
        latest_backup = $LatestBackup.Name
        file_count = $BackupFiles.Count
        bytes = [long](($BackupFiles | Measure-Object Length -Sum).Sum)
        observed_at = $LatestBackup.LastWriteTimeUtc.ToString("o")
    }
}
$Toolchain = [ordered]@{
    powershell = $PSVersionTable.PSVersion.ToString()
    python = (& $Python --version 2>&1 | Select-Object -First 1).ToString().Trim()
    node = (& node.exe --version 2>&1 | Select-Object -First 1).ToString().Trim()
    pnpm = (& pnpm.cmd --version 2>&1 | Select-Object -First 1).ToString().Trim()
    pyinstaller = (& $Python -m PyInstaller --version 2>&1 | Select-Object -Last 1).ToString().Trim()
}
$ReleaseManifest = [ordered]@{
    version = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    commit = $Commit
    source_state = $SourceState
    working_tree_dirty = if ($SourceState -eq "dirty") { $true } elseif ($SourceState -eq "clean") { $false } else { $null }
    dependency_lock_hash = $LockHash
    migration_version = $MigrationVersion
    toolchain = $Toolchain
    backup_baseline = $BackupBaseline
    restore_drill = [ordered]@{
        status = "pending"
        mode = "temporary-copy"
        critical_api_status = "pending"
    }
    database_files = $DatabaseFiles
    persistent_dirs = $PersistentNames
    exe_sha256 = $ExeHash
    total_bytes = $Bytes
    program_bytes = $ProgramBytes
    persistent_bytes = $PersistentBytes
    incremental_copy_bytes = $IncrementalCopyBytes
    startup_cold_read_ms = $null
    program_files = $ProgramFiles
} | ConvertTo-Json -Depth 5
[IO.File]::WriteAllText(
    (Join-Path $BuiltRelease "release-manifest.json"),
    $ReleaseManifest,
    [Text.UTF8Encoding]::new($false)
)
& "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $BuiltRelease
Write-Host ("Portable release: {0}" -f $BuiltRelease)
if ($ReleaseInUse.Count -gt 0) {
    Write-Host "The live release was left untouched because it is currently open."
    $PendingUpdate = @{
        version = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
        staged_root = $BuiltRelease
        target_root = $Release
        created_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json
    [IO.File]::WriteAllText(
        (Join-Path $Release "pending-update.json"),
        $PendingUpdate,
        [Text.UTF8Encoding]::new($false)
    )
    Write-Host "The staged release will be applied automatically on the next launch."
}
Write-Host ("Files: {0}; Size: {1:N1} MB" -f $Files.Count, ($Bytes / 1MB))
Write-Host ("Program: {0:N1} MB; Persistent: {1:N1} MB; Incremental copy: {2:N1} MB" -f ($ProgramBytes / 1MB), ($PersistentBytes / 1MB), ($IncrementalCopyBytes / 1MB))

Get-ChildItem -LiteralPath $Release -Force | ForEach-Object {
    $ItemBytes = if ($_.PSIsContainer) {
        (Get-ChildItem -LiteralPath $_.FullName -Recurse -File |
            Measure-Object Length -Sum).Sum
    } else {
        $_.Length
    }
    Write-Host ("  {0,-24} {1,8:N1} MB" -f $_.Name, ($ItemBytes / 1MB))
}
