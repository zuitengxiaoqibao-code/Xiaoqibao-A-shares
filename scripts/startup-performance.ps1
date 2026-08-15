param(
    [string]$InputPath = "",
    [string]$OutputPath = "",
    [int]$MaxColdWindowMs = 3000,
    [int]$MaxHotWindowMedianMs = 3000,
    [int]$MaxHotWindowP95Ms = 5000,
    [int]$MaxHotApiMedianMs = 6000,
    [int]$MaxHotApiP95Ms = 8000
)

function Get-StartupPercentile {
    param(
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][double[]]$Values,
        [Parameter(Mandatory = $true)][double]$Percentile
    )

    if ($Values.Count -eq 0) { return $null }
    $Sorted = @($Values | Sort-Object)
    $Rank = [Math]::Ceiling($Percentile * $Sorted.Count)
    $Index = [Math]::Max(0, [int]$Rank - 1)
    return [int][Math]::Round([double]$Sorted[$Index], 0, [MidpointRounding]::AwayFromZero)
}

function Get-StartupTimingValue {
    param(
        [Parameter(Mandatory = $true)]$Run,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][AllowEmptyCollection()][System.Collections.Generic.List[string]]$Warnings
    )

    $Property = $Run.PSObject.Properties[$Name]
    if ($null -eq $Property -or $null -eq $Property.Value -or [string]::IsNullOrWhiteSpace([string]$Property.Value)) {
        $Warnings.Add("missing_$Name")
        return $null
    }
    try {
        $Value = [double]$Property.Value
    } catch {
        $Warnings.Add("invalid_$Name")
        return $null
    }
    if ($Value -lt 0 -or [double]::IsNaN($Value) -or [double]::IsInfinity($Value)) {
        $Warnings.Add("invalid_$Name")
        return $null
    }
    return [int][Math]::Round($Value, 0, [MidpointRounding]::AwayFromZero)
}

function Get-StartupPerformanceSummary {
    param(
        [Parameter(Mandatory = $true)][object[]]$Runs,
        [int]$MaxColdWindowMs = 3000,
        [int]$MaxHotWindowMedianMs = 3000,
        [int]$MaxHotWindowP95Ms = 5000,
        [int]$MaxHotApiMedianMs = 6000,
        [int]$MaxHotApiP95Ms = 8000
    )

    $Warnings = [System.Collections.Generic.List[string]]::new()
    $Cold = [System.Collections.Generic.List[object]]::new()
    $Hot = [System.Collections.Generic.List[object]]::new()
    foreach ($Run in @($Runs)) {
        $KindProperty = $Run.PSObject.Properties["kind"]
        $Kind = if ($null -eq $KindProperty) { "" } else { [string]$KindProperty.Value }
        if ($Kind -notin @("cold", "hot")) {
            $Warnings.Add("invalid_run_kind")
            continue
        }
        $StateProperty = $Run.PSObject.Properties["state"]
        if ($null -eq $StateProperty -or [string]$StateProperty.Value -ne "pass") {
            $Warnings.Add("run_not_pass")
        }
        $Timing = [ordered]@{
            window_visible_ms = Get-StartupTimingValue -Run $Run -Name "window_visible_ms" -Warnings $Warnings
            api_ready_ms = Get-StartupTimingValue -Run $Run -Name "api_ready_ms" -Warnings $Warnings
            full_verification_ms = Get-StartupTimingValue -Run $Run -Name "full_verification_ms" -Warnings $Warnings
        }
        if ($Kind -eq "cold") { $Cold.Add([pscustomobject]$Timing) } else { $Hot.Add([pscustomobject]$Timing) }
    }

    if ($Cold.Count -eq 0) { $Warnings.Add("missing_cold_run") }
    if ($Hot.Count -eq 0) { $Warnings.Add("missing_hot_run") }

    $ColdWindow = @($Cold | Where-Object { $null -ne $_.window_visible_ms } | ForEach-Object { $_.window_visible_ms })
    $HotWindow = @($Hot | Where-Object { $null -ne $_.window_visible_ms } | ForEach-Object { $_.window_visible_ms })
    $HotApi = @($Hot | Where-Object { $null -ne $_.api_ready_ms } | ForEach-Object { $_.api_ready_ms })

    if ($ColdWindow.Count -gt 0 -and ($ColdWindow | Measure-Object -Maximum).Maximum -gt $MaxColdWindowMs) {
        $Warnings.Add("cold_window_visible_ms_exceeded")
    }
    $HotWindowMedian = Get-StartupPercentile -Values ([double[]]$HotWindow) -Percentile 0.5
    $HotWindowP95 = Get-StartupPercentile -Values ([double[]]$HotWindow) -Percentile 0.95
    $HotApiMedian = Get-StartupPercentile -Values ([double[]]$HotApi) -Percentile 0.5
    $HotApiP95 = Get-StartupPercentile -Values ([double[]]$HotApi) -Percentile 0.95
    if ($null -ne $HotWindowMedian -and $HotWindowMedian -gt $MaxHotWindowMedianMs) { $Warnings.Add("hot_window_median_ms_exceeded") }
    if ($null -ne $HotWindowP95 -and $HotWindowP95 -gt $MaxHotWindowP95Ms) { $Warnings.Add("hot_window_p95_ms_exceeded") }
    if ($null -ne $HotApiMedian -and $HotApiMedian -gt $MaxHotApiMedianMs) { $Warnings.Add("hot_api_median_ms_exceeded") }
    if ($null -ne $HotApiP95 -and $HotApiP95 -gt $MaxHotApiP95Ms) { $Warnings.Add("hot_api_p95_ms_exceeded") }

    [ordered]@{
        state = if ($Warnings.Count -eq 0) { "pass" } else { "warning" }
        cold = [ordered]@{
            count = $Cold.Count
            window_visible_max_ms = if ($ColdWindow.Count -eq 0) { $null } else { [int]($ColdWindow | Measure-Object -Maximum).Maximum }
        }
        hot = [ordered]@{
            count = $Hot.Count
            window_visible_median_ms = $HotWindowMedian
            window_visible_p95_ms = $HotWindowP95
            api_ready_median_ms = $HotApiMedian
            api_ready_p95_ms = $HotApiP95
        }
        thresholds = [ordered]@{
            max_cold_window_ms = $MaxColdWindowMs
            max_hot_window_median_ms = $MaxHotWindowMedianMs
            max_hot_window_p95_ms = $MaxHotWindowP95Ms
            max_hot_api_median_ms = $MaxHotApiMedianMs
            max_hot_api_p95_ms = $MaxHotApiP95Ms
        }
        warnings = @($Warnings | Select-Object -Unique)
        observed_at = (Get-Date).ToUniversalTime().ToString("o")
    }
}

if (-not [string]::IsNullOrWhiteSpace($InputPath)) {
    $ResolvedInput = (Resolve-Path -LiteralPath $InputPath).Path
    if (Test-Path -LiteralPath $ResolvedInput -PathType Container) {
        $Runs = @(Get-ChildItem -LiteralPath $ResolvedInput -Filter "startup-smoke-*.json" -File |
            Sort-Object LastWriteTime |
            ForEach-Object {
                [IO.File]::ReadAllText($_.FullName, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
            })
    } else {
        $InputJson = [IO.File]::ReadAllText($ResolvedInput, [Text.UTF8Encoding]::new($false)) | ConvertFrom-Json
        $Runs = if ($null -ne $InputJson.runs) { @($InputJson.runs) } else { @($InputJson) }
    }
    $Summary = Get-StartupPerformanceSummary `
        -Runs $Runs `
        -MaxColdWindowMs $MaxColdWindowMs `
        -MaxHotWindowMedianMs $MaxHotWindowMedianMs `
        -MaxHotWindowP95Ms $MaxHotWindowP95Ms `
        -MaxHotApiMedianMs $MaxHotApiMedianMs `
        -MaxHotApiP95Ms $MaxHotApiP95Ms
    $Json = $Summary | ConvertTo-Json -Depth 8
    if ([string]::IsNullOrWhiteSpace($OutputPath)) {
        Write-Output $Json
    } else {
        $OutputParent = Split-Path -Parent $OutputPath
        if ([string]::IsNullOrWhiteSpace($OutputParent)) { $OutputParent = (Get-Location).Path }
        New-Item -ItemType Directory -Force -Path $OutputParent | Out-Null
        [IO.File]::WriteAllText((Join-Path (Resolve-Path -LiteralPath $OutputParent).Path (Split-Path -Leaf $OutputPath)), $Json, [Text.UTF8Encoding]::new($false))
    }
    if ($Summary.state -ne "pass") { exit 2 }
}
