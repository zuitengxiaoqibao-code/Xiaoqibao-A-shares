param(
    [switch]$IncludeDefaultAIKey,
    [switch]$DataFree,
    [string]$ReleaseRoot = ""
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dist = (Resolve-Path (Join-Path $Root "dist")).Path
$Release = if ($ReleaseRoot) { (Resolve-Path -LiteralPath $ReleaseRoot).Path } else { (Resolve-Path (Join-Path $Dist "XiaoQiBao-Portable")).Path }
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$StageParent = Join-Path $Dist (
    ".package-staging-" + [guid]::NewGuid().ToString("N")
)
$StageRelease = Join-Path $StageParent "XiaoQiBao-Portable"
$SuffixParts = @(
    if ($DataFree) { "Data-Free" }
    if ($IncludeDefaultAIKey) { "With-Default-AI" } else { "No-AI-Key" }
)
$Suffix = $SuffixParts -join "-"
$Archive = Join-Path $Dist (
    "XiaoQiBao-Portable-Test-$Suffix-$Stamp.zip"
)

function Assert-SafeStagingPath([string]$Path) {
    $resolvedStage = [IO.Path]::GetFullPath($Path)
    $resolvedDist = [IO.Path]::GetFullPath($Dist).TrimEnd("\") + "\"
    $leaf = Split-Path -Leaf $resolvedStage
    if (
        -not $resolvedStage.StartsWith(
            $resolvedDist,
            [StringComparison]::OrdinalIgnoreCase
        ) -or
        $leaf -notlike ".package-staging-*"
    ) {
        throw "Unsafe staging path: $resolvedStage"
    }
}

try {
    Assert-SafeStagingPath $StageParent
    New-Item -ItemType Directory -Path $StageParent | Out-Null
    if ($DataFree) {
        New-Item -ItemType Directory -Path $StageRelease | Out-Null
        $PersistentNames = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
        foreach ($Entry in Get-ChildItem -LiteralPath $Release -Force) {
            if ($Entry.Name -notin ($PersistentNames + @("release-manifest.json"))) {
                Copy-Item -LiteralPath $Entry.FullName -Destination $StageRelease -Recurse -Force
            }
        }
        foreach ($Name in $PersistentNames) {
            New-Item -ItemType Directory -Path (Join-Path $StageRelease $Name) -Force | Out-Null
        }
        $SourceAISettings = Join-Path $Release "data\ai-settings.json"
        if (Test-Path -LiteralPath $SourceAISettings) {
            Copy-Item -LiteralPath $SourceAISettings -Destination (Join-Path $StageRelease "data") -Force
        }
        if (Test-Path -LiteralPath (Join-Path $Release "config")) {
            Copy-Item -Path (Join-Path $Release "config\*") -Destination (Join-Path $StageRelease "config") -Recurse -Force
        }
        $PackageReadme = Join-Path $Root "packaging\portable-test-readme.txt"
        if (Test-Path -LiteralPath $PackageReadme) {
            Copy-Item -LiteralPath $PackageReadme -Destination (Join-Path $StageRelease "测试包说明.txt") -Force
        }
    } else {
        Copy-Item `
            -LiteralPath $Release `
            -Destination $StageParent `
            -Recurse `
            -Force
    }

    if ($IncludeDefaultAIKey) {
        $sourceData = Join-Path $Release "data"
        $stageSettings = Join-Path $StageRelease "data\ai-settings.json"
        if (-not (Test-Path -LiteralPath $stageSettings)) {
            throw "AI settings are missing from the portable release"
        }

        $settingsBackup = "$stageSettings.protected.bak"
        Copy-Item `
            -LiteralPath $stageSettings `
            -Destination $settingsBackup `
            -Force

        $env:PYTHONPATH = (Resolve-Path (Join-Path $Root "apps\api\src")).Path
        $env:PYTHONUTF8 = "1"
        $pythonCode = @(
            "import hmac,json,sys"
            "from pathlib import Path"
            "from qibao_api.settings_repository import AISettingsRepository,AISettings"
            "source_dir=Path(sys.argv[1])"
            "target=Path(sys.argv[2])"
            "source=AISettingsRepository(source_dir).load()"
            "assert isinstance(source,AISettings)"
            "raw=json.loads(target.read_text(encoding='utf-8'))"
            "payload={'base_url':source.base_url,'model':source.model,'revision':raw['revision'],'api_key':source.api_key}"
            "target.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf-8',newline='\n')"
            "portable=AISettingsRepository(target.parent,protector=None).load()"
            "assert isinstance(portable,AISettings)"
            "assert hmac.compare_digest(source.api_key,portable.api_key)"
        ) -join ";"

        & $Python -c $pythonCode $sourceData $stageSettings
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create portable default AI settings"
        }
        Remove-Item -LiteralPath $settingsBackup -Force
    }

    Compress-Archive `
        -LiteralPath $StageRelease `
        -DestinationPath $Archive `
        -CompressionLevel Optimal

    if (-not (Test-Path -LiteralPath $Archive)) {
        throw "Portable test archive was not created"
    }

    $archiveItem = Get-Item -LiteralPath $Archive
    $archiveHash = Get-FileHash -LiteralPath $Archive -Algorithm SHA256
    Write-Output ("ARCHIVE_PATH=" + $archiveItem.FullName)
    Write-Output ("ARCHIVE_BYTES=" + $archiveItem.Length)
    Write-Output ("ARCHIVE_SHA256=" + $archiveHash.Hash)
} finally {
    if (Test-Path -LiteralPath $StageParent) {
        Assert-SafeStagingPath $StageParent
        Remove-Item -LiteralPath $StageParent -Recurse -Force
    }
}
