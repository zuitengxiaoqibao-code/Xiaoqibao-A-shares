import ast
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _assignment_call(tree: ast.AST, name: str) -> ast.Call:
    assignment = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    assert isinstance(assignment.value, ast.Call)
    return assignment.value


def test_portable_spec_shows_boot_splash_before_python_startup() -> None:
    spec_path = _project_root() / "packaging" / "xiaoqibao.spec"
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))

    splash_call = _assignment_call(tree, "splash")
    exe_call = _assignment_call(tree, "exe")
    collect_call = _assignment_call(tree, "coll")

    assert isinstance(splash_call.func, ast.Name)
    assert splash_call.func.id == "Splash"
    assert any(
        isinstance(argument, ast.Name) and argument.id == "splash"
        for argument in exe_call.args
    )
    assert any(
        isinstance(argument, ast.Attribute)
        and isinstance(argument.value, ast.Name)
        and argument.value.id == "splash"
        and argument.attr == "binaries"
        for argument in collect_call.args
    )


def test_portable_spec_keeps_python_modules_in_the_cold_start_archive() -> None:
    spec_path = _project_root() / "packaging" / "xiaoqibao.spec"
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))

    analysis_call = _assignment_call(tree, "a")
    noarchive = next(
        keyword.value
        for keyword in analysis_call.keywords
        if keyword.arg == "noarchive"
    )

    assert isinstance(noarchive, ast.Constant)
    assert noarchive.value is False


def test_portable_build_limits_web_test_workers_for_stable_release_verification() -> None:
    build_path = _project_root() / "scripts" / "build-portable.ps1"
    script = build_path.read_text(encoding="utf-8")

    assert 'test -- --maxWorkers=2' in script


def test_portable_smoke_waits_for_lifespan_before_http_probe() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    lifespan_gate = script.index("desktop startup stage=lifespan-ready")
    health_probe = script.index('Uri "http://127.0.0.1:$Port/health"')

    assert lifespan_gate < health_probe


def test_portable_smoke_ignores_lifespan_markers_from_previous_runs() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "$LogStartOffset" in script
    assert "Get-SmokeLogDelta" in script
    assert "$StartupLog = Get-SmokeLogDelta" in script


def test_portable_smoke_reports_non_json_quant_errors_without_masking_them() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "$RawErrorBody = $QuantError.ErrorDetails.Message" in script
    assert "ConvertFrom-Json -ErrorAction Stop" in script
    assert "with non-JSON error body" in script


def test_portable_smoke_supports_a_release_data_mode() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "[switch]$UseReleaseData" in script
    assert "XiaoQiBao-Portable" in script
    assert "Release data mode" in script
    assert "/api/v1/tdx/local/professional" in script
    assert 'TableList = "Fn193"' in script
    assert "table_list=Fn&" not in script


def test_portable_smoke_probes_every_professional_field_family() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    for method, table in (
        ("get_financial_data", "Fn193"),
        ("get_gpjy_value", "GP1"),
        ("get_bkjy_value", "BK5"),
        ("get_scjy_value", "SC1"),
        ("get_gp_one_data", "GO1"),
    ):
        assert method in script
        assert table in script
    assert "$ProfessionalProbes" in script
    assert "$ProfessionalSummary" in script


def test_portable_smoke_reports_individual_request_timings() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "$HomeRequestMs" in script
    assert "$OverviewRequestMs" in script
    assert "$QuantStrategyRequestMs" in script
    assert "$PortfolioRiskRequestMs" in script
    assert "$CompanyResearchRequestMs" in script
    assert "$ProfessionalRequestMs" in script
    assert "requests home={3}ms overview={4}ms quant={5}ms portfolio={6}ms research={7}ms professional={8}ms" in script


def test_portable_smoke_probes_portfolio_risk_and_company_research_contracts() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "/api/v1/a-shares/portfolio-risk" in script
    portfolio_probe = script.split('$PortfolioRisk = Invoke-RestMethod', 1)[1].split(
        '$PortfolioRiskRequestMs', 1,
    )[0]
    assert "-Method Post" not in portfolio_probe
    assert "$PortfolioRiskBody" not in script
    assert "/api/v1/a-shares/600519/company-research" in script
    assert "$PortfolioRisk.status -notin" in script
    assert "$CompanyResearch.status -notin" in script


def test_portable_smoke_checks_source_health_and_persistent_directories() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "/api/v1/operations/source-health" in script
    assert "$SourceHealth" in script
    for directory in ("config", "data", "news", "cache", "logs", "models", "exports", "backups"):
        assert directory in script


def test_portable_smoke_cleanup_is_scoped_to_its_own_process() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "Stop-Process -Id $Process.Id" in script
    assert "Stop-Process -Name" not in script
    assert "TdxW.exe" not in script
    assert "tdxcef.exe" not in script


def test_portable_build_preserves_persistent_data_without_copying_transient_locks() -> None:
    build_path = _project_root() / "scripts" / "build-portable.ps1"
    script = build_path.read_text(encoding="utf-8")

    assert "Copy-PersistentTree" in script
    assert "*.lock" in script
    assert "*-wal" in script
    assert "*-shm" in script


def test_portable_build_stages_when_the_current_release_is_in_use() -> None:
    build_path = _project_root() / "scripts" / "build-portable.ps1"
    script = build_path.read_text(encoding="utf-8")

    assert "Get-CimInstance Win32_Process" in script
    assert "ReleaseInUse" in script
    assert "$BuildDist" in script
    assert "pending-update.json" in script
    assert "applied automatically on the next launch" in script


def test_portable_build_writes_release_size_and_incremental_copy_manifest() -> None:
    build_path = _project_root() / "scripts" / "build-portable.ps1"
    script = build_path.read_text(encoding="utf-8")

    assert "release-manifest.json" in script
    assert "program_bytes" in script
    assert "persistent_bytes" in script
    assert "incremental_copy_bytes" in script
    assert "startup_cold_read_ms" in script


def test_portable_smoke_records_cold_start_in_release_manifest() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "release-manifest.json" in script
    assert "startup_cold_read_ms" in script
    assert "$ApiReadyMs" in script


def test_portable_smoke_can_target_a_staged_release_directory() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "ReleaseRootOverride" in script
    assert "Resolve-Path $ReleaseRootOverride" in script
    assert "--instance-name" in script


def test_portable_smoke_waits_for_deferred_quant_scan_to_settle() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert 'candidate_scan_state -eq "pending"' in script
    assert "$QuantBackgroundDeadline" in script
    assert "background candidate scan" in script


def test_portable_spec_does_not_collect_cross_platform_or_unused_tool_submodules() -> None:
    spec_path = _project_root() / "packaging" / "xiaoqibao.spec"
    source = spec_path.read_text(encoding="utf-8")

    assert 'collect_submodules("webview")' not in source
    assert 'collect_submodules("uvicorn")' not in source
    assert 'collect_submodules("mootdx")' not in source
    for required in (
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "webview.platforms.mshtml",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan.on",
    ):
        assert required in source


def test_portable_spec_does_not_archive_every_qibao_module() -> None:
    spec_path = _project_root() / "packaging" / "xiaoqibao.spec"
    source = spec_path.read_text(encoding="utf-8")

    assert 'collect_submodules("qibao_api")' not in source
    assert 'collect_submodules("qibao_desktop")' not in source
    assert '"qibao_api.main"' in source


def test_portable_spec_excludes_unreachable_platform_and_mootdx_tool_branches() -> None:
    spec_path = _project_root() / "packaging" / "xiaoqibao.spec"
    tree = ast.parse(spec_path.read_text(encoding="utf-8"))
    analysis_call = _assignment_call(tree, "a")
    excludes = next(
        keyword.value
        for keyword in analysis_call.keywords
        if keyword.arg == "excludes"
    )
    assert isinstance(excludes, ast.List)
    values = {item.value for item in excludes.elts if isinstance(item, ast.Constant)}
    assert {
        "webview.platforms.android",
        "webview.platforms.cocoa",
        "webview.platforms.gtk",
        "webview.platforms.qt",
        "webview.platforms.cef",
        "mootdx.tools",
    }.issubset(values)
