param(
    [string]$InputPath = "",
    [string]$OutputPath = "",
    [int]$MaxResultMs = 10000,
    [int]$MaxCacheFrameMs = 1000
)

$script:RequiredMenuIds = @(
    "market_overview", "today_decision", "stock_observation", "company_research",
    "first_limit_up", "late_session_selection", "quant_analysis", "monitor_center",
    "news", "risk", "history", "settings", "operations", "bonds"
)
$script:AllowedMenuStates = @("ready", "partial", "stale", "unavailable", "error")

function Get-MenuSampleValue {
    param(
        [Parameter(Mandatory = $true)]$Sample,
        [Parameter(Mandatory = $true)][string]$Name,
        $Default = $null
    )
    $Property = $Sample.PSObject.Properties[$Name]
    if ($null -eq $Property) { return $Default }
    return $Property.Value
}

function Test-MenuPerformance {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][object[]]$Samples,
        [int]$MaxResultMs = 10000,
        [int]$MaxCacheFrameMs = 1000
    )

    $Failures = [System.Collections.Generic.List[string]]::new()
    $Details = [System.Collections.Generic.List[object]]::new()
    foreach ($Menu in $script:RequiredMenuIds) {
        $Matches = @($Samples | Where-Object { [string](Get-MenuSampleValue -Sample $_ -Name "menu" -Default "") -eq $Menu })
        if ($Matches.Count -eq 0) {
            $Failures.Add("missing_menu:$Menu")
            continue
        }
        if ($Matches.Count -gt 1) {
            $Failures.Add("duplicate_menu:$Menu")
            continue
        }

        $Sample = $Matches[0]
        $State = [string](Get-MenuSampleValue -Sample $Sample -Name "state" -Default "")
        $LatencyRaw = Get-MenuSampleValue -Sample $Sample -Name "latency_ms"
        $CacheFrameRaw = Get-MenuSampleValue -Sample $Sample -Name "cache_frame_ms"
        $Usable = [bool](Get-MenuSampleValue -Sample $Sample -Name "usable_content" -Default $false)
        $Reason = [string](Get-MenuSampleValue -Sample $Sample -Name "reason" -Default "")

        if ($State -notin $script:AllowedMenuStates) {
            $Failures.Add("invalid_state:$Menu")
        }
        if ($null -eq $LatencyRaw -or [double]$LatencyRaw -lt 0) {
            $Failures.Add("missing_latency:$Menu")
            $Latency = $null
        } else {
            $Latency = [int][Math]::Round([double]$LatencyRaw, 0, [MidpointRounding]::AwayFromZero)
            if ($Latency -gt $MaxResultMs) { $Failures.Add("latency_exceeded:$Menu") }
        }
        if ($null -ne $CacheFrameRaw -and [string]$CacheFrameRaw -ne "") {
            $CacheFrame = [int][Math]::Round([double]$CacheFrameRaw, 0, [MidpointRounding]::AwayFromZero)
            if ($CacheFrame -gt $MaxCacheFrameMs) { $Failures.Add("cache_frame_exceeded:$Menu") }
        } else {
            $CacheFrame = $null
        }
        if (-not $Usable -and [string]::IsNullOrWhiteSpace($Reason)) {
            $Failures.Add("empty_result_without_reason:$Menu")
        }

        $Details.Add([pscustomobject][ordered]@{
            menu = $Menu
            state = $State
            latency_ms = $Latency
            cache_frame_ms = $CacheFrame
            usable_content = $Usable
            reason = $Reason
        })
    }

    foreach ($Sample in $Samples) {
        $Menu = [string](Get-MenuSampleValue -Sample $Sample -Name "menu" -Default "")
        if ($Menu -and $Menu -notin $script:RequiredMenuIds) {
            $Failures.Add("unknown_menu:$Menu")
        }
    }

    return [pscustomobject][ordered]@{
        state = if ($Failures.Count -eq 0) { "pass" } else { "fail" }
        checked_count = $Details.Count
        required_count = $script:RequiredMenuIds.Count
        max_result_ms = $MaxResultMs
        max_cache_frame_ms = $MaxCacheFrameMs
        failures = @($Failures | Select-Object -Unique)
        menus = @($Details)
        observed_at = (Get-Date).ToUniversalTime().ToString("o")
    }
}

if (-not [string]::IsNullOrWhiteSpace($InputPath)) {
    $ResolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
    $Payload = [IO.File]::ReadAllText($ResolvedInput, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
    $Samples = if ($null -ne $Payload.PSObject.Properties["menus"]) { @($Payload.menus) } elseif ($null -ne $Payload.PSObject.Properties["samples"]) { @($Payload.samples) } else { @($Payload) }
    $Result = Test-MenuPerformance -Samples $Samples -MaxResultMs $MaxResultMs -MaxCacheFrameMs $MaxCacheFrameMs
    $Json = $Result | ConvertTo-Json -Depth 8
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        Write-Output $Json
    } else {
        $OutputParent = Split-Path -Parent $OutputPath
        if ([string]::IsNullOrWhiteSpace($OutputParent)) { $OutputParent = (Get-Location).Path }
        New-Item -ItemType Directory -Force -Path $OutputParent | Out-Null
        $ResolvedParent = (Resolve-Path -LiteralPath $OutputParent).Path
        [IO.File]::WriteAllText(
            (Join-Path $ResolvedParent (Split-Path -Leaf $OutputPath)),
            $Json,
            [Text.UTF8Encoding]::new($false)
        )
    }
    if ($Result.state -ne "pass") { exit 2 }
}
