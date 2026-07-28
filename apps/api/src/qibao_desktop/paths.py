import sys
from pathlib import Path

from qibao_api.runtime import RuntimeLayout


def desktop_layout(root: Path | None = None) -> RuntimeLayout:
    if root is not None:
        return RuntimeLayout.from_root(root)
    executable = Path(sys.executable if getattr(sys, "frozen", False) else __file__)
    base = executable.resolve().parent if getattr(sys, "frozen", False) else Path.cwd()
    return RuntimeLayout.from_root(base)
