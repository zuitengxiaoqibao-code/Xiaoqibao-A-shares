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


def test_portable_smoke_waits_for_lifespan_before_http_probe() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    lifespan_gate = script.index("desktop startup stage=lifespan-ready")
    health_probe = script.index('Uri "http://127.0.0.1:$Port/health"')

    assert lifespan_gate < health_probe


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
    assert "table_list=Fn193" in script
    assert "table_list=Fn&" not in script


def test_portable_smoke_reports_individual_request_timings() -> None:
    smoke_path = _project_root() / "scripts" / "run-portable-smoke.ps1"
    script = smoke_path.read_text(encoding="utf-8")

    assert "$HomeRequestMs" in script
    assert "$OverviewRequestMs" in script
    assert "$QuantStrategyRequestMs" in script
    assert "$ProfessionalRequestMs" in script
    assert "requests home={3}ms overview={4}ms quant={5}ms professional={6}ms" in script


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
