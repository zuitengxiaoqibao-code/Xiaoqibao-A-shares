param(
    [Parameter(Mandatory = $true)]
    [string]$ArchivePath,
    [int]$Port = 19765
)

$ErrorActionPreference = "Stop"
$Archive = (Resolve-Path $ArchivePath).Path
$SmokeRoot = Join-Path $env:TEMP (
    "xiaoqibao-package-smoke-" + [guid]::NewGuid().ToString("N")
)
$Release = Join-Path $SmokeRoot "XiaoQiBao-Portable"
$Exe = Join-Path $Release "xiaoqibao.exe"
$SettingsPath = Join-Path $Release "data\ai-settings.json"
$Process = $null

function Assert-SafeSmokePath([string]$Path) {
    $resolvedSmoke = [IO.Path]::GetFullPath($Path)
    $resolvedTemp = [IO.Path]::GetFullPath($env:TEMP).TrimEnd("\") + "\"
    $leaf = Split-Path -Leaf $resolvedSmoke
    if (
        -not $resolvedSmoke.StartsWith(
            $resolvedTemp,
            [StringComparison]::OrdinalIgnoreCase
        ) -or
        $leaf -notlike "xiaoqibao-package-smoke-*"
    ) {
        throw "Unsafe package smoke path: $resolvedSmoke"
    }
}

try {
    Assert-SafeSmokePath $SmokeRoot
    New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
    Expand-Archive -LiteralPath $Archive -DestinationPath $SmokeRoot -Force

    if (-not (Test-Path -LiteralPath $Exe)) {
        throw "Packaged executable is missing"
    }
    if (-not (Test-Path -LiteralPath $SettingsPath)) {
        throw "Packaged AI settings are missing"
    }

    $settings = Get-Content `
        -LiteralPath $SettingsPath `
        -Encoding UTF8 `
        -Raw | ConvertFrom-Json
    if (
        [string]::IsNullOrWhiteSpace([string]$settings.base_url) -or
        [string]::IsNullOrWhiteSpace([string]$settings.model) -or
        [string]::IsNullOrWhiteSpace([string]$settings.api_key) -or
        $null -ne $settings.api_key_protected
    ) {
        throw "Packaged default AI settings are not portable"
    }

    $Process = Start-Process `
        -FilePath $Exe `
        -ArgumentList @("--portable-root", $Release, "--port", $Port) `
        -PassThru
    $StartedAt = [Diagnostics.Stopwatch]::StartNew()

    $WindowVisibleMs = $null
    $WindowDeadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $Process.Refresh()
        if ($Process.MainWindowHandle -ne 0) {
            $WindowVisibleMs = $StartedAt.ElapsedMilliseconds
            break
        }
        Start-Sleep -Milliseconds 25
    } while ([DateTime]::UtcNow -lt $WindowDeadline -and -not $Process.HasExited)

    if ($null -eq $WindowVisibleMs) {
        throw "Packaged desktop window was not created"
    }
    $FirstWindowTargetMet = $WindowVisibleMs -le 3000

    $Health = $null
    $Deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $Health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$Port/health" `
                -TimeoutSec 1
            break
        } catch {
            Start-Sleep -Milliseconds 200
        }
    } while ([DateTime]::UtcNow -lt $Deadline)
    if ($null -eq $Health) {
        throw "Packaged health check timed out"
    }

    $HomeResponse = Invoke-WebRequest `
        -Uri "http://127.0.0.1:$Port/" `
        -TimeoutSec 5 `
        -UseBasicParsing
    if (
        $HomeResponse.StatusCode -ne 200 -or
        $HomeResponse.Content -notmatch "id=.root."
    ) {
        throw "Packaged frontend smoke failed"
    }

    $AI = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/settings/ai" `
        -TimeoutSec 5
    if (
        -not $AI.configured -or
        [string]::IsNullOrWhiteSpace([string]$AI.base_url) -or
        [string]::IsNullOrWhiteSpace([string]$AI.model) -or
        [string]::IsNullOrWhiteSpace([string]$AI.api_key_hint)
    ) {
        throw "Packaged default AI configuration was not loaded"
    }
    $ApiReadyMs = $StartedAt.ElapsedMilliseconds

    $migrated = Get-Content `
        -LiteralPath $SettingsPath `
        -Encoding UTF8 `
        -Raw | ConvertFrom-Json
    if (
        [string]::IsNullOrWhiteSpace([string]$migrated.api_key_protected) -or
        $null -ne $migrated.api_key
    ) {
        throw "Packaged AI key was not migrated to Windows protection"
    }

    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
    }

    $RepeatPort = $Port + 1
    $Process = Start-Process `
        -FilePath $Exe `
        -ArgumentList @("--portable-root", $Release, "--port", $RepeatPort) `
        -PassThru
    $RepeatStartedAt = [Diagnostics.Stopwatch]::StartNew()
    $RepeatWindowVisibleMs = $null
    $RepeatWindowDeadline = [DateTime]::UtcNow.AddSeconds(10)
    do {
        $Process.Refresh()
        if ($Process.MainWindowHandle -ne 0) {
            $RepeatWindowVisibleMs = $RepeatStartedAt.ElapsedMilliseconds
            break
        }
        Start-Sleep -Milliseconds 25
    } while (
        [DateTime]::UtcNow -lt $RepeatWindowDeadline -and
        -not $Process.HasExited
    )
    if ($null -eq $RepeatWindowVisibleMs) {
        throw "Packaged repeat-launch window was not created"
    }
    if ($RepeatWindowVisibleMs -gt 3000) {
        throw "Packaged repeat launch exceeded 3 second target: ${RepeatWindowVisibleMs}ms"
    }

    Write-Output (
        "PACKAGE_SMOKE=passed;FIRST_WINDOW_MS=" + $WindowVisibleMs +
        ";FIRST_WINDOW_TARGET=" + $FirstWindowTargetMet +
        ";REPEAT_WINDOW_MS=" + $RepeatWindowVisibleMs +
        ";API_MS=" + $ApiReadyMs +
        ";AI_CONFIGURED=true;KEY_OUTPUT=redacted"
    )
} finally {
    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
    }
    if (Test-Path -LiteralPath $SmokeRoot) {
        Assert-SafeSmokePath $SmokeRoot
        Remove-Item -LiteralPath $SmokeRoot -Recurse -Force
    }
    if ($null -ne $Process) {
        $remaining = @(
            Get-Process | Where-Object {
                $_.Path -and $_.Path -eq $Exe
            }
        ).Count
        Write-Output ("PACKAGE_EXE_COUNT=" + $remaining)
    }
}
