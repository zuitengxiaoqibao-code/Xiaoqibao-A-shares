from pathlib import Path

from qibao_desktop.paths import desktop_layout


def test_explicit_portable_root_wins(tmp_path: Path) -> None:
    layout = desktop_layout(tmp_path / "portable")
    assert layout.root == (tmp_path / "portable").resolve()
