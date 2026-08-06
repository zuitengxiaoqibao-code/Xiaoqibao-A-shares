import os
import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_api_import_defers_heavy_market_dependencies() -> None:
    source_root = _project_root() / "apps" / "api" / "src"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(source_root), environment.get("PYTHONPATH", "")))
    )
    probe = (
        "import sys; import qibao_api.main; "
        "print('\\n'.join(sorted(name for name in sys.modules "
        "if name == 'duckdb' or name == 'pandas' or name == 'numpy' "
        "or name == 'mootdx' or name.startswith('mootdx.'))))"
    )

    result = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        check=True,
        text=True,
        env=environment,
    )

    assert result.stdout.strip() == ""
