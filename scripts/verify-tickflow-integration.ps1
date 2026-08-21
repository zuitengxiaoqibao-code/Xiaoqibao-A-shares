param(
    [string]$ReleaseRoot = "",
    [string]$SourceRoot = ""
)

$ErrorActionPreference = "Stop"
$Root = if ($SourceRoot) { (Resolve-Path $SourceRoot).Path } else { (Resolve-Path (Join-Path $PSScriptRoot "..")).Path }
$Release = if ($ReleaseRoot) { (Resolve-Path $ReleaseRoot).Path } else { Join-Path $Root "dist\XiaoQiBao-Portable" }
$Failures = [Collections.Generic.List[string]]::new()

function Require-Path([string]$Path, [string]$Label, [string]$Kind = "Any") {
    $PathType = if ($Kind -eq "Leaf") { "Leaf" } elseif ($Kind -eq "Container") { "Container" } else { "Any" }
    if (-not (Test-Path -LiteralPath $Path -PathType $PathType)) { $Failures.Add("Missing ${Label}: $Path") }
}

Require-Path (Join-Path $Release "xiaoqibao.exe") "portable EXE" "Leaf"
Require-Path (Join-Path $Release "release-manifest.json") "release manifest" "Leaf"
foreach ($Name in @("config", "data", "news", "cache", "logs", "models", "exports", "backups")) {
    Require-Path (Join-Path $Release $Name) "persistent directory $Name" "Container"
}

$ManifestPath = Join-Path $Release "release-manifest.json"
if (Test-Path -LiteralPath $ManifestPath -PathType Leaf) {
    try { $Manifest = Get-Content -LiteralPath $ManifestPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $Failures.Add("Release manifest is not valid UTF-8 JSON") }
    if ($null -ne $Manifest) {
        if (-not $Manifest.commit) { $Failures.Add("Release manifest has no source commit") }
        $ExePath = Join-Path $Release "xiaoqibao.exe"
        if (Test-Path -LiteralPath $ExePath -PathType Leaf) {
            $ActualHash = (Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
            $ExpectedHash = [string]$Manifest.exe_sha256
            if (-not $ExpectedHash -or $ExpectedHash -ne $ActualHash) { $Failures.Add("EXE SHA-256 does not match release manifest") }
        }
    }
}

$Capabilities = [ordered]@{
    "data_import" = "apps/api/src/qibao_api/routes/data_import.py"
    "strategy_draft_gate" = "apps/api/src/qibao_api/a_shares/strategy_draft_gate.py"
    "matrix_backtest" = "apps/api/src/qibao_api/zhongshu/backtest_matrix.py"
    "portfolio_backtest" = "apps/api/src/qibao_api/zhongshu/backtest_portfolio.py"
    "monitor_center" = "apps/api/src/qibao_api/a_shares/monitor_center.py"
    "postclose_report" = "apps/api/src/qibao_api/a_shares/postclose_report.py"
}
foreach ($Entry in $Capabilities.GetEnumerator()) {
    Require-Path (Join-Path $Root $Entry.Value) $Entry.Key "Leaf"
}

$Main = Get-Content -LiteralPath (Join-Path $Root "apps/api/src/qibao_api/main.py") -Raw -Encoding UTF8
foreach ($Router in @("data_import_router", "monitor_center_router")) {
    if ($Main -notmatch [regex]::Escape("app.include_router($Router)")) { $Failures.Add("Main app did not register $Router") }
}

if ($Failures.Count -gt 0) {
    Write-Host "TickFlow integration gate failed:" -ForegroundColor Red
    $Failures | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "TickFlow integration gate passed" -ForegroundColor Green
Write-Host " - EXE, manifest and eight persistent directories are present"
Write-Host " - Import, strategy gate, backtest, monitor and postclose contracts are registered"
