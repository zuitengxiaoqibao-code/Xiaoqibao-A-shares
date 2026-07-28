from pathlib import Path

from qibao_api.runtime.layout import RuntimeLayout


def test_runtime_layout_maps_every_portable_directory(tmp_path: Path) -> None:
    layout = RuntimeLayout.from_root(tmp_path / "portable")

    assert layout.root == (tmp_path / "portable").resolve()
    assert layout.web_dir == layout.root / "web"
    assert layout.config_dir == layout.root / "config"
    assert layout.data_dir == layout.root / "data"
    assert layout.legacy_data_dir == layout.root / "data" / "legacy"
    assert layout.news_dir == layout.root / "news"
    assert layout.cache_dir == layout.root / "cache"
    assert layout.logs_dir == layout.root / "logs"
    assert layout.models_dir == layout.root / "models"
    assert layout.exports_dir == layout.root / "exports"
    assert layout.backups_dir == layout.root / "backups"


def test_ensure_creates_runtime_directories_but_not_web_assets(tmp_path: Path) -> None:
    layout = RuntimeLayout.from_root(tmp_path / "portable")

    layout.ensure()

    assert not layout.web_dir.exists()
    for name, path in layout.directory_map().items():
        if name != "web":
            assert path.is_dir(), name
