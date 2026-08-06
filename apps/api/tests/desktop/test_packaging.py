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
