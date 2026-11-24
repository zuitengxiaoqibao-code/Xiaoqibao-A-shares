param(
    [int]$Port = 18765,
    [switch]$KeepSmokeRoot,
    [switch]$VerifySpeech,
    [switch]$UseReleaseData,
    [string]$ReleaseRootOverride = "",
    [string]$PortableRootOverride = "",
    [ValidateSet("auto", "cold", "hot")][string]$StartupKind = "auto"
)

$ErrorActionPreference = "Stop"
$Utf8 = [Text.UTF8Encoding]::new($false)
$OutputEncoding = $Utf8
try { [Console]::OutputEncoding = $Utf8 } catch { }
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ReleaseRoot = if ($ReleaseRootOverride) {
    (Resolve-Path $ReleaseRootOverride).Path
} else {
    Join-Path $Root "dist\XiaoQiBao-Portable"
}
$Exe = Join-Path $ReleaseRoot "xiaoqibao.exe"
$PersistentNames = @("config", "data", "news", "cache", "logs", "models", "exports", "backups")
. "$PSScriptRoot\release-manifest.ps1"
. "$PSScriptRoot\probe-menu-performance.ps1"

if ($UseReleaseData -and $PortableRootOverride) {
    throw "UseReleaseData and PortableRootOverride cannot be used together"
}
$ExternalPortableRoot = -not [string]::IsNullOrWhiteSpace($PortableRootOverride)

function Repair-Utf8Text([string]$Text) {
    if ([string]::IsNullOrEmpty($Text)) { return $Text }
    # A few Windows PowerShell versions decode UTF-8 response text as Latin-1
    # while materializing Invoke-RestMethod objects. Repair only that clear
    # signature; never rewrite ordinary Chinese or hide an unknown error.
    if ($Text -notmatch '[\u00C3\u00C2\u00E5\u00E6\u00E7\u00E8\u00E9\u00EF\u00F0]') { return $Text }
    try {
        $bytes = [Text.Encoding]::GetEncoding(28591).GetBytes($Text)
        $fixed = [Text.Encoding]::UTF8.GetString($bytes)
        if ($fixed -notmatch '\uFFFD') { return $fixed }
    } catch { }
    return $Text
}

function Assert-NoManifestMojibake([string]$Text) {
    if ($Text -match '\uFFFD|[\u00C3\u00C2\u00E5\u00E6\u00E7\u00E8\u00E9\u00EF\u00F0][^\r\n]{0,2}[\u0080-\u00BF]') {
        throw "Release manifest contains invalid UTF-8 diagnostic text"
    }
}
if ($ExternalPortableRoot) {
    $SmokeRoot = (Resolve-Path -LiteralPath $PortableRootOverride).Path
    foreach ($Name in $PersistentNames) {
        if (-not (Test-Path -LiteralPath (Join-Path $SmokeRoot $Name) -PathType Container)) {
            throw "External portable root is missing persistent directory: $Name"
        }
    }
    if (-not (Test-Path -LiteralPath (Join-Path $SmokeRoot "web") -PathType Container)) {
        throw "External portable root is missing web assets"
    }
    Write-Host ("External portable root mode: {0}" -f $SmokeRoot)
} elseif ($UseReleaseData) {
    $SmokeRoot = $ReleaseRoot
    if (-not (Test-Path -LiteralPath $SmokeRoot)) {
        throw "Portable release directory was not found: $SmokeRoot"
    }
    foreach ($Name in $PersistentNames) {
        if (-not (Test-Path -LiteralPath (Join-Path $SmokeRoot $Name))) {
            throw "Portable persistent directory is missing: $Name"
        }
    }
    Write-Host ("Release data mode: using persistent portable root {0}" -f $SmokeRoot)
} else {
    $SmokeRoot = Join-Path $env:TEMP (
        "xiaoqibao-smoke-" + [guid]::NewGuid().ToString("N")
    )
    New-Item -ItemType Directory -Path $SmokeRoot | Out-Null
    Copy-Item -LiteralPath (Join-Path $ReleaseRoot "web") `
        -Destination (Join-Path $SmokeRoot "web") -Recurse
}
$LogPath = Join-Path $SmokeRoot "logs\xiaoqibao.log"
$StartupEvidenceDirectory = Join-Path $SmokeRoot "logs"
New-Item -ItemType Directory -Force -Path $StartupEvidenceDirectory | Out-Null
$StartupRunKind = $StartupKind
if ($StartupRunKind -eq "auto") {
    $ExistingStartupEvidence = @(Get-ChildItem -LiteralPath $StartupEvidenceDirectory -Filter "startup-smoke-*.json" -File -ErrorAction SilentlyContinue)
    $StartupRunKind = if ($ExistingStartupEvidence.Count -eq 0) { "cold" } else { "hot" }
}
$StartupEvidencePath = Join-Path $StartupEvidenceDirectory (
    "startup-smoke-{0}-{1}.json" -f (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssfffZ"), [guid]::NewGuid().ToString("N")
)
$LogStartOffset = if (Test-Path -LiteralPath $LogPath) {
    (Get-Item -LiteralPath $LogPath).Length
} else {
    0
}

function Get-SmokeLogDelta {
    if (-not (Test-Path -LiteralPath $LogPath)) { return "" }

    $Stream = $null
    $Reader = $null
    try {
        $Stream = [IO.FileStream]::new(
            $LogPath,
            [IO.FileMode]::Open,
            [IO.FileAccess]::Read,
            [IO.FileShare]::ReadWrite
        )
        $Offset = if ($Stream.Length -ge $LogStartOffset) {
            $LogStartOffset
        } else {
            0
        }
        [void]$Stream.Seek($Offset, [IO.SeekOrigin]::Begin)
        $Reader = [IO.StreamReader]::new($Stream, $Utf8, $true, 4096, $false)
        return $Reader.ReadToEnd()
    } finally {
        if ($null -ne $Reader) {
            $Reader.Dispose()
        } elseif ($null -ne $Stream) {
            $Stream.Dispose()
        }
    }
}

$Process = Start-Process -FilePath $Exe -ArgumentList @(
    "--portable-root", $SmokeRoot,
    "--port", $Port,
    "--instance-name", ("xiaoqibao-smoke-{0}" -f $Port)
) -PassThru
$StartedAt = [Diagnostics.Stopwatch]::StartNew()

try {
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

    if ($null -eq $WindowVisibleMs) { throw "Portable desktop window was not created" }
    if ($WindowVisibleMs -gt 3000) {
        throw "Portable desktop window exceeded 3 second target: ${WindowVisibleMs}ms"
    }

    # The portable server pre-binds its loopback socket before importing the
    # API.  Probing that socket too early can leave a cancelled Windows
    # proactor accept behind and make a healthy server look unavailable.  Wait
    # for the final lifespan log stage before issuing the first HTTP request.
    $LifespanReady = $false
    $LifespanDeadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        if (Test-Path -LiteralPath $LogPath) {
            $StartupLog = Get-SmokeLogDelta
            if ($StartupLog -match "desktop startup stage=lifespan-ready") {
                $LifespanReady = $true
                Start-Sleep -Milliseconds 100
                break
            }
        }
        Start-Sleep -Milliseconds 100
    } while ([DateTime]::UtcNow -lt $LifespanDeadline -and -not $Process.HasExited)
    if (-not $LifespanReady) {
        throw "Portable lifespan readiness log was not observed"
    }

    $Health = $null
    $HealthReadyMs = $null
    $Deadline = [DateTime]::UtcNow.AddSeconds(60)
    do {
        try {
            $Health = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$Port/health" `
                -TimeoutSec 1
            $HealthReadyMs = $StartedAt.ElapsedMilliseconds
            break
        } catch {
            Start-Sleep -Milliseconds 200
        }
    } while ([DateTime]::UtcNow -lt $Deadline)

    if ($null -eq $Health) {
        $Process.Refresh()
        Write-Warning (
            "Portable health timeout diagnostics: pid={0}; cpu={1:N1}s; working_set={2:N1}MB; threads={3}" -f
            $Process.Id,
            $Process.CPU,
            ($Process.WorkingSet64 / 1MB),
            $Process.Threads.Count
        )
        if (Test-Path -LiteralPath $LogPath) {
            (Get-SmokeLogDelta) -split "`r?`n" |
                Select-Object -Last 80 |
                Write-Warning
        }
        throw "Portable health check timed out"
    }
    $ApiReadyMs = $HealthReadyMs
    $MenuPerformance = Invoke-MenuPerformanceProbe `
        -BaseUri "http://127.0.0.1:$Port" `
        -TimeoutSec 10 `
        -MaxResultMs 10000 `
        -MaxCacheFrameMs 1000
    if ($MenuPerformance.state -ne "pass") {
        throw ("Portable fourteen-menu performance gate failed: {0}" -f ($MenuPerformance.failures -join ","))
    }
    if ($UseReleaseData) {
        $ReleaseManifestPath = Join-Path $ReleaseRoot "release-manifest.json"
        if (Test-Path -LiteralPath $ReleaseManifestPath) {
            try {
                $ReleaseManifest = Get-Content -LiteralPath $ReleaseManifestPath -Raw -Encoding UTF8 |
                    ConvertFrom-Json
                $ReleaseManifest.startup_cold_read_ms = $ApiReadyMs
                [IO.File]::WriteAllText(
                    $ReleaseManifestPath,
                    ($ReleaseManifest | ConvertTo-Json -Depth 8),
                    [Text.UTF8Encoding]::new($false)
                )
            } catch {
                Write-Warning "Release manifest startup timing could not be updated."
            }
        }
    }
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    $HomeResponse = Invoke-WebRequest `
        -Uri "http://127.0.0.1:$Port/" `
        -TimeoutSec 5 `
        -UseBasicParsing
    $HomeRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    if (
        $HomeResponse.StatusCode -ne 200 -or
        $HomeResponse.Content -notmatch "id=.root."
    ) {
        throw "Portable frontend smoke failed"
    }
    if ($VerifySpeech) {
        $SpeechAudioPath = Join-Path $StartupEvidenceDirectory "edge-tts-smoke.mp3"
        $SpeechPayload = @{ text = "易数智算，语音连接测试。" } | ConvertTo-Json -Compress
        $SpeechResponse = Invoke-WebRequest `
            -Uri "http://127.0.0.1:$Port/api/v1/speech/synthesize" `
            -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Body ($Utf8.GetBytes($SpeechPayload)) `
            -OutFile $SpeechAudioPath `
            -PassThru `
            -TimeoutSec 30 `
            -UseBasicParsing
        $SpeechBytes = [IO.File]::ReadAllBytes($SpeechAudioPath)
        $HasMp3Header = $SpeechBytes.Length -ge 3 -and (
            ($SpeechBytes[0] -eq 0x49 -and $SpeechBytes[1] -eq 0x44 -and $SpeechBytes[2] -eq 0x33) -or
            ($SpeechBytes[0] -eq 0xFF -and ($SpeechBytes[1] -band 0xE0) -eq 0xE0)
        )
        if (
            $SpeechResponse.StatusCode -ne 200 -or
            [string]$SpeechResponse.Headers["Content-Type"] -notmatch "^audio/mpeg" -or
            -not $HasMp3Header
        ) {
            throw "Portable Edge TTS cloud synthesis did not return MP3 audio"
        }
        Write-Host ("Edge TTS cloud synthesis passed: {0} bytes; audio={1}" -f $SpeechBytes.Length, $SpeechAudioPath)
    }
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    $Overview = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/a-shares/market-overview" `
        -TimeoutSec 30
    $OverviewRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    if ($Overview.status -notin @("ready", "partial", "unavailable")) {
        throw "Portable market overview did not return an honest data status"
    }
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    $LateSession = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/a-shares/late-session-selection?limit=20" `
        -TimeoutSec 30
    $LateSessionRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    if ($LateSession.status -notin @("ready", "partial", "unavailable")) {
        throw "Portable late-session selection did not return an honest data status"
    }
    if ($LateSessionRequestMs -gt 8000) {
        throw "Portable late-session selection exceeded 8 second budget: ${LateSessionRequestMs}ms"
    }
    if ($null -eq $LateSession.monitor_stage -or $null -eq $LateSession.invalidated_candidates) {
        throw "Portable late-session selection omitted lifecycle evidence"
    }
    $LateSessionAuditPath = Join-Path $SmokeRoot "data\late-session-audit.sqlite3"
    if (-not (Test-Path -LiteralPath $LateSessionAuditPath -PathType Leaf)) {
        throw "Portable late-session traceability database was not created"
    }
    $SourceHealth = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/operations/source-health" `
        -TimeoutSec 10
    if ($null -eq $SourceHealth -or $SourceHealth.window_size -lt 1 -or $null -eq $SourceHealth.sources) {
        throw "Portable source-health response was incomplete"
    }
    $SourceHealthStatus = if (@($SourceHealth.sources | Where-Object { $_.status -eq "ready" }).Count -gt 0) {
        "ready"
    } elseif (@($SourceHealth.sources).Count -gt 0) {
        "degraded"
    } else {
        "unavailable"
    }
    $QuantStrategy = $null
    $QuantStrategyStatus = $null
    $QuantLastCandidateCount = 0
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    try {
        $QuantStrategy = Invoke-RestMethod `
            -Uri "http://127.0.0.1:$Port/api/v1/a-shares/quant-strategy?limit=12" `
            -TimeoutSec 30
    } catch {
        $QuantError = $_
        $StatusCode = [int]$QuantError.Exception.Response.StatusCode
        $RawErrorBody = $QuantError.ErrorDetails.Message
        try {
            $ErrorBody = $RawErrorBody | ConvertFrom-Json -ErrorAction Stop
        } catch {
            throw (
                "Portable quant strategy returned HTTP {0} with non-JSON error body: {1}" -f
                $StatusCode,
                $RawErrorBody
            )
        }
        if (
            $StatusCode -ne 503 -or
            $ErrorBody.detail.code -ne "quant_strategy_unavailable"
        ) {
            throw
        }
        $QuantStrategyStatus = "unavailable"
    }
    $QuantStrategyRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    if ($null -ne $QuantStrategy) {
        if ($QuantStrategy.status -notin @("ready", "partial", "unavailable")) {
            throw "Portable quant strategy did not return an honest data status"
        }
        if ($QuantStrategy.formula_version -ne "a-share-short-strategy-v2.0") {
            throw "Portable quant strategy formula version is incorrect"
        }
        if ($QuantStrategy.strategy_models.Count -ne 6) {
            throw "Portable quant strategy did not expose all six strategy models"
        }
        $QuantStrategyStatus = $QuantStrategy.status
        $QuantLastCandidateCount = $QuantStrategy.candidates.Count
    }
    if ($null -ne $QuantStrategy -and $QuantStrategy.candidate_scan_state -eq "pending") {
        $QuantBackgroundDeadline = [DateTime]::UtcNow.AddSeconds(90)
        while ($QuantStrategy.candidate_scan_state -eq "pending" -and [DateTime]::UtcNow -lt $QuantBackgroundDeadline) {
            Start-Sleep -Milliseconds 250
            $QuantPollStarted = [Diagnostics.Stopwatch]::StartNew()
            # Candidate scans are long-running local jobs. The poll request
            # must wait for the API response instead of treating ten seconds
            # as a cancellation boundary.
            $QuantStrategy = Invoke-RestMethod -Uri ("http://127.0.0.1:{0}/api/v1/a-shares/quant-strategy?limit=12" -f $Port) -TimeoutSec 60
            $QuantPollStarted.Stop()
            if ($QuantStrategy.candidates.Count -gt 0) {
                $QuantLastCandidateCount = $QuantStrategy.candidates.Count
            } elseif ($QuantLastCandidateCount -gt 0) {
                throw "quant strategy refresh dropped the last real candidate list"
            }
        }
        if ($QuantStrategy.candidate_scan_state -eq "pending") {
            throw "background candidate scan did not settle within 90 seconds"
        }
        $QuantStrategyStatus = $QuantStrategy.status
    }
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    $PortfolioRisk = Invoke-RestMethod `
        -Uri "http://127.0.0.1:$Port/api/v1/a-shares/portfolio-risk" `
        -TimeoutSec 15
    $PortfolioRiskRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    if ($PortfolioRisk.status -notin @("ready", "partial", "unavailable")) {
        throw "Portable portfolio risk did not return an honest data status"
    }
    $CompanyResearch = $null
    $CompanyResearchStatus = $null
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    try {
        $CompanyResearchTask = Invoke-RestMethod `
            -Method Post `
            -Uri "http://127.0.0.1:$Port/api/v1/a-shares/300456/company-research/tasks" `
            -TimeoutSec 10
        $CompanyResearchTaskId = $CompanyResearchTask.progress.task_id
        if ([string]::IsNullOrWhiteSpace($CompanyResearchTaskId)) {
            throw "Portable company research task did not return a task id"
        }
        $CompanyResearchDeadline = [DateTime]::UtcNow.AddSeconds(60)
        while (
            $CompanyResearchTask.progress.status -in @("queued", "running") -and
            [DateTime]::UtcNow -lt $CompanyResearchDeadline
        ) {
            Start-Sleep -Milliseconds 250
            $CompanyResearchTask = Invoke-RestMethod `
                -Uri "http://127.0.0.1:$Port/api/v1/a-shares/company-research/tasks/$CompanyResearchTaskId" `
                -TimeoutSec 10
        }
        if ($CompanyResearchTask.progress.status -ne "succeeded") {
            throw (
                "Portable company research task ended with status={0}; stage={1}; detail={2}" -f
                $CompanyResearchTask.progress.status,
                $CompanyResearchTask.progress.stage,
                $CompanyResearchTask.progress.detail
            )
        }
        $CompanyResearch = $CompanyResearchTask.result
    } catch {
        $ResearchError = $_
        $ResearchStatusCode = if ($null -ne $ResearchError.Exception.Response) {
            [int]$ResearchError.Exception.Response.StatusCode
        } else {
            0
        }
        $ResearchRawErrorBody = $ResearchError.ErrorDetails.Message
        if (
            $ResearchStatusCode -eq 0 -and
            [string]::IsNullOrWhiteSpace($ResearchRawErrorBody)
        ) {
            throw (
                "Portable company research task failed: {0}" -f
                $ResearchError.Exception.Message
            )
        }
        try {
            $ResearchErrorBody = $ResearchRawErrorBody | ConvertFrom-Json -ErrorAction Stop
        } catch {
            throw (
                "Portable company research returned HTTP {0} with non-JSON error body: {1}" -f
                $ResearchStatusCode,
                $ResearchRawErrorBody
            )
        }
        if (
            $ResearchStatusCode -ne 503 -or
            $ResearchErrorBody.detail.code -ne "company_research_unavailable"
        ) {
            throw
        }
        $CompanyResearchStatus = "unavailable"
    }
    $CompanyResearchRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    if ($null -ne $CompanyResearch) {
        if ($CompanyResearch.status -notin @("ready", "partial", "unavailable")) {
            throw "Portable company research did not return an honest data status"
        }
        if ($CompanyResearch.symbol -ne "300456" -or $CompanyResearch.counter_case.Count -ne 10) {
            throw "Portable company research response did not satisfy the evidence contract"
        }
        $CompanyResearchStatus = $CompanyResearch.status
    }
    $ProfessionalProbes = @(
        [pscustomobject]@{ Method = "get_financial_data"; TableList = "Fn193" },
        [pscustomobject]@{ Method = "get_gpjy_value"; TableList = "GP1" },
        [pscustomobject]@{ Method = "get_bkjy_value"; TableList = "BK5" },
        [pscustomobject]@{ Method = "get_scjy_value"; TableList = "SC1" },
        [pscustomobject]@{ Method = "get_gp_one_data"; TableList = "GO1" }
    )
    $StageStartedMs = $StartedAt.ElapsedMilliseconds
    $ProfessionalResults = @()
    foreach ($Probe in $ProfessionalProbes) {
        $ProfessionalUri = "http://127.0.0.1:{0}/api/v1/tdx/local/professional?method={1}&table_list={2}&stock_codes=600000" -f `
            $Port, $Probe.Method, $Probe.TableList
        $Professional = Invoke-RestMethod -Uri $ProfessionalUri -TimeoutSec 30
        if ($Professional.status -notin @("ready", "partial", "unavailable")) {
            throw "Portable TDX professional probe did not return an honest data status"
        }
        $ProfessionalResults += [pscustomobject]@{
            method = $Probe.Method
            table = $Probe.TableList
            status = $Professional.status
            detail = if ($Professional.detail) {
                Repair-Utf8Text ([string]$Professional.detail)
            } else {
                "rows=$($Professional.rows.Count)"
            }
        }
    }
    $ProfessionalRequestMs = $StartedAt.ElapsedMilliseconds - $StageStartedMs
    $QuantDetail = if ($null -ne $QuantStrategy) {
        if ($QuantStrategy.status -eq "partial") {
            "candidates=$($QuantStrategy.candidates.Count); coverage=$($QuantStrategy.regime.coverage_percent)%"
        } else {
            "candidates=$($QuantStrategy.candidates.Count)"
        }
    } elseif ($null -ne $ErrorBody.detail.reason) {
        $ErrorBody.detail.reason
    } else {
        "unavailable"
    }
    $ProfessionalStatus = if ($ProfessionalResults.status -contains "ready") {
        "ready"
    } elseif ($ProfessionalResults.status -contains "partial") {
        "partial"
    } else {
        "unavailable"
    }
    $ProfessionalSummary = ($ProfessionalResults | ForEach-Object {
        "{0}:{1}={2}" -f $_.method, $_.table, $_.status
    }) -join ","
    $ProfessionalDetail = ($ProfessionalResults | ForEach-Object {
        "{0} {1}" -f $_.method, $_.detail
    }) -join "; "
    $PortfolioRiskDetail = "positions=$($PortfolioRisk.positions.Count); warnings=$($PortfolioRisk.warnings.Count)"
    $CompanyResearchDetail = if ($null -ne $CompanyResearch) {
        "symbol=$($CompanyResearch.symbol); coverage=$($CompanyResearch.evidence_coverage); counter_case=$($CompanyResearch.counter_case.Count)"
    } else {
        $ResearchErrorBody.detail.message
    }
    $CoveragePercent = $null
    if ($Overview.market_data.universe_count -gt 0) {
        $CoveragePercent = [Math]::Round((100.0 * $Overview.market_data.quote_count / $Overview.market_data.universe_count), 2)
    }
    $QualityWarnings = @()
    if ($Overview.status -ne "ready") { $QualityWarnings += "market_overview_partial" }
    if ($SourceHealthStatus -ne "ready") { $QualityWarnings += "source_health_degraded" }
    if ($QuantStrategyStatus -eq "partial") { $QualityWarnings += "quant_strategy_partial" }
    if ($QuantStrategyStatus -eq "unavailable") { $QualityWarnings += "quant_strategy_unavailable" }
    if ($CompanyResearchStatus -eq "partial") { $QualityWarnings += "company_research_partial" }
    if ($CompanyResearchStatus -eq "unavailable") { $QualityWarnings += "company_research_unavailable" }
    $QualityGateState = if ($QualityWarnings.Count -eq 0) { "pass" } else { "warning" }
    if ($UseReleaseData -and (Test-Path -LiteralPath $ReleaseManifestPath)) {
        try {
            $ReleaseManifest = Get-Content -LiteralPath $ReleaseManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $DomainStatus = [ordered]@{
                overview = [ordered]@{
                    status = $Overview.status
                    coverage_percent = $CoveragePercent
                    quote_count = $Overview.market_data.quote_count
                    universe_count = $Overview.market_data.universe_count
                    observed_at = $Overview.observed_at
                }
                source_health = [ordered]@{
                    status = if ($SourceHealthStatus -eq "degraded") { "partial" } else { $SourceHealthStatus }
                    source_count = $SourceHealth.source_count
                    probed_count = $SourceHealth.probed_count
                    ready_count = $SourceHealth.ready_count
                    degraded_count = $SourceHealth.degraded_count
                    unavailable_count = $SourceHealth.unavailable_count
                    observed_at = $SourceHealth.observed_at
                }
                quant_strategy = [ordered]@{
                    status = $QuantStrategyStatus
                    candidate_count = if ($null -eq $QuantStrategy) { 0 } else { $QuantStrategy.candidates.Count }
                    coverage_percent = if ($null -eq $QuantStrategy) { $null } else { $QuantStrategy.regime.coverage_percent }
                    formula_version = if ($null -eq $QuantStrategy) { $null } else { $QuantStrategy.formula_version }
                    detail = Repair-Utf8Text ([string]$QuantDetail)
                }
                late_session = [ordered]@{
                    status = $LateSession.status
                    candidate_count = $LateSession.candidate_count
                    monitor_stage = $LateSession.monitor_stage
                    source_quality = $LateSession.source_quality
                    detail = if ($LateSession.no_data_reason) {
                        Repair-Utf8Text ([string]$LateSession.no_data_reason)
                    } else {
                        $null
                    }
                }
                portfolio_risk = [ordered]@{
                    status = $PortfolioRisk.status
                    position_count = $PortfolioRisk.positions.Count
                    warning_count = $PortfolioRisk.warnings.Count
                    detail = $PortfolioRiskDetail
                }
                company_research = [ordered]@{
                    status = $CompanyResearchStatus
                    symbol = if ($null -eq $CompanyResearch) { $null } else { $CompanyResearch.symbol }
                    evidence_coverage = if ($null -eq $CompanyResearch) { $null } else { $CompanyResearch.evidence_coverage }
                    counter_case_count = if ($null -eq $CompanyResearch) { 0 } else { $CompanyResearch.counter_case.Count }
                    detail = Repair-Utf8Text ([string]$CompanyResearchDetail)
                }
                tdx_professional = [ordered]@{
                    status = $ProfessionalStatus
                    probes = @($ProfessionalResults | ForEach-Object {
                        [ordered]@{
                            method = $_.method
                            table = $_.table
                            status = $_.status
                            detail = $_.detail
                        }
                    })
                }
            }
            $QualityGateSummary = [ordered]@{
                state = $QualityGateState
                smoke = "pass"
                api_ready = "pass"
                window_visible = "pass"
                data_integrity_ratio = if ($null -eq $CoveragePercent) { $null } else { [Math]::Round($CoveragePercent / 100.0, 4) }
                data_status = $Overview.status
                warnings = @($QualityWarnings)
                domain_status = $DomainStatus
                observed_at = (Get-Date).ToUniversalTime().ToString("o")
                startup_metrics = [ordered]@{
                    kind = $StartupRunKind
                    state = "pass"
                    window_visible_ms = [int]$WindowVisibleMs
                    api_ready_ms = [int]$ApiReadyMs
                    full_verification_ms = [int]$StartedAt.ElapsedMilliseconds
                    observed_at = (Get-Date).ToUniversalTime().ToString("o")
                }
                realtime_metrics = [ordered]@{
                    state = "pass"
                    late_session_request_ms = [int]$LateSessionRequestMs
                    late_session_budget_ms = 8000
                    traceability_status = "pass"
                    audit_database = "data/late-session-audit.sqlite3"
                    observed_at = (Get-Date).ToUniversalTime().ToString("o")
                }
                menu_performance = $MenuPerformance
            }
            if ($ReleaseManifest.PSObject.Properties.Name -contains "quality_gates") {
                $ReleaseManifest.quality_gates = $QualityGateSummary
            } else {
                $ReleaseManifest | Add-Member -MemberType NoteProperty -Name quality_gates -Value $QualityGateSummary
            }
            $ManifestJson = $ReleaseManifest | ConvertTo-Json -Depth 10
            Assert-NoManifestMojibake $ManifestJson
            [IO.File]::WriteAllText($ReleaseManifestPath, $ManifestJson, [Text.UTF8Encoding]::new($false))
        } catch {
            $DiagnosticMatch = if ($null -ne $ManifestJson) {
                [regex]::Match($ManifestJson, '\uFFFD|[\u00C3\u00C2\u00E5\u00E6\u00E7\u00E8\u00E9\u00EF\u00F0][^\r\n]{0,2}[\u0080-\u00BF]')
            }
            $DiagnosticValue = if ($DiagnosticMatch -and $DiagnosticMatch.Success) {
                $DiagnosticMatch.Value
            } else {
                "none"
            }
            Write-Warning ("Release manifest quality gate summary could not be updated: {0}; diagnostic_match={1}" -f $_.Exception.Message, $DiagnosticValue)
        }
    }
    $StartupEvidence = [ordered]@{
        schema_version = 1
        kind = $StartupRunKind
        state = "pass"
        window_visible_ms = [int]$WindowVisibleMs
        api_ready_ms = [int]$ApiReadyMs
        full_verification_ms = [int]$StartedAt.ElapsedMilliseconds
        observed_at = (Get-Date).ToUniversalTime().ToString("o")
    } | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($StartupEvidencePath, $StartupEvidence, [Text.UTF8Encoding]::new($false))
    $CoverageDisplay = if ($null -eq $CoveragePercent) { "--" } else { $CoveragePercent }
    Write-Host ("Quality gates: {0}; data coverage={1}% (partial is warning, never fabricated as ready)" -f $QualityGateState, $CoverageDisplay)
    Write-Host ("Fourteen-menu performance: {0}; checked={1}/{2}; max_result=10s; max_cache_frame=1s" -f $MenuPerformance.state, $MenuPerformance.checked_count, $MenuPerformance.required_count)
    Write-Host ("Portable smoke passed; window visible in {0}ms; API ready in {1}ms; verification completed in {2}ms; requests home={3}ms overview={4}ms quant={5}ms portfolio={6}ms research={7}ms professional={8}ms; overview {9} coverage={10}%; source health {11}; quant strategy {12} ({13}); portfolio risk {14} ({15}); company research {16} ({17}); tdx professional {18} ({19})" -f `
        $WindowVisibleMs, $HealthReadyMs, $StartedAt.ElapsedMilliseconds, $HomeRequestMs, $OverviewRequestMs, $QuantStrategyRequestMs, $PortfolioRiskRequestMs, $CompanyResearchRequestMs, $ProfessionalRequestMs, $Overview.status, $CoverageDisplay, $SourceHealthStatus, $QuantStrategyStatus, $QuantDetail, $PortfolioRisk.status, $PortfolioRiskDetail, $CompanyResearchStatus, $CompanyResearchDetail, $ProfessionalStatus, "$ProfessionalSummary; $ProfessionalDetail")
} finally {
    if (-not $Process.HasExited) {
        Stop-Process -Id $Process.Id
        Wait-Process -Id $Process.Id -ErrorAction SilentlyContinue
    }
    # A forced smoke shutdown can orphan a Windows process-pool child. Clean
    # only children launched from this exact portable EXE and smoke PID.
    $SmokeChildProcesses = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.ParentProcessId -eq $Process.Id -and
            $_.ExecutablePath -and
            ([IO.Path]::GetFullPath($_.ExecutablePath) -ieq [IO.Path]::GetFullPath($Exe)) -and
            $_.CommandLine -match "--multiprocessing-fork"
        }
    foreach ($Child in $SmokeChildProcesses) {
        Stop-Process -Id $Child.ProcessId -Force -ErrorAction SilentlyContinue
    }
    if (-not $UseReleaseData -and -not $ExternalPortableRoot) {
        $ResolvedTempRoot = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
        $ResolvedSmokeRoot = [IO.Path]::GetFullPath($SmokeRoot)
        $IsSmokeDirectory = (Split-Path -Leaf $ResolvedSmokeRoot) -like `
            "xiaoqibao-smoke-*"
        if (
            -not $KeepSmokeRoot -and
            $IsSmokeDirectory -and
            $ResolvedSmokeRoot.StartsWith(
                $ResolvedTempRoot,
                [StringComparison]::OrdinalIgnoreCase
            ) -and
            (Test-Path -LiteralPath $ResolvedSmokeRoot)
        ) {
            $CleanupDeadline = [DateTime]::UtcNow.AddSeconds(5)
            do {
                try {
                    Remove-Item `
                        -LiteralPath $ResolvedSmokeRoot `
                        -Recurse `
                        -Force `
                        -ErrorAction Stop
                    break
                } catch [IO.IOException] {
                    if ([DateTime]::UtcNow -ge $CleanupDeadline) { throw }
                    Start-Sleep -Milliseconds 100
                }
            } while (Test-Path -LiteralPath $ResolvedSmokeRoot)
        }
        if ($KeepSmokeRoot) {
            Write-Host ("Portable smoke root retained: {0}" -f $SmokeRoot)
        }
    } elseif ($UseReleaseData) {
        Update-ReleaseManifestRuntimeEvidence -ReleaseRoot $SmokeRoot
        & "$PSScriptRoot\sign-release-manifest.ps1" -ReleaseRoot $SmokeRoot
        Write-Host ("Release data mode: persistent data retained at {0}" -f $SmokeRoot)
    } else {
        Write-Host ("External portable root retained: {0}" -f $SmokeRoot)
    }
}
