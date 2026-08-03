param(
    [switch]$IncludeDefaultAIKey
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Dist = (Resolve-Path (Join-Path $Root "dist")).Path
$Release = (Resolve-Path (Join-Path $Dist "XiaoQiBao-Portable")).Path
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$StageParent = Join-Path $Dist (
    ".package-staging-" + [guid]::NewGuid().ToString("N")
)
$StageRelease = Join-Path $StageParent "XiaoQiBao-Portable"
$Suffix = if ($IncludeDefaultAIKey) { "With-Default-AI" } else { "No-AI-Key" }
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
    Copy-Item `
        -LiteralPath $Release `
        -Destination $StageParent `
        -Recurse `
        -Force

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
