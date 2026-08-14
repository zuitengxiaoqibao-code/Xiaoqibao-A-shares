from datetime import datetime, timedelta, timezone
import os

from qibao_api.operations.read_model import OperationsReadModel


def test_cleanup_preview_does_not_delete_and_execute_only_removes_rebuildable_files(tmp_path) -> None:
    cache = tmp_path / "cache"
    logs = tmp_path / "logs"
    data = tmp_path / "data"
    cache.mkdir()
    logs.mkdir()
    data.mkdir()
    stale_cache = cache / "old.json"
    stale_log = logs / "old.log"
    database = data / "market.duckdb"
    stale_cache.write_bytes(b"cache")
    stale_log.write_bytes(b"log")
    database.write_bytes(b"market")
    old = (datetime.now(timezone.utc) - timedelta(days=10)).timestamp()
    os.utime(stale_cache, (old, old))
    os.utime(stale_log, (old, old))
    os.utime(database, (old, old))
    read_model = OperationsReadModel(tmp_path)

    preview = read_model.cleanup_preview(older_than_hours=72)

    assert preview == {"candidate_count": 2, "candidate_bytes": 8, "categories": {"cache": 1, "logs": 1}}
    assert stale_cache.exists() and stale_log.exists() and database.exists()

    result = read_model.cleanup_rebuildable(older_than_hours=72)

    assert result["removed_count"] == 2
    assert database.exists()


def test_release_inventory_separates_program_persistent_and_rebuildable_bytes(tmp_path) -> None:
    (tmp_path / "web").mkdir()
    (tmp_path / "data").mkdir()
    (tmp_path / "cache").mkdir()
    (tmp_path / "config").mkdir()
    (tmp_path / "xiaoqibao.exe").write_bytes(b"program")
    (tmp_path / "web" / "index.js").write_bytes(b"web")
    (tmp_path / "data" / "market.duckdb").write_bytes(b"market-data")
    (tmp_path / "cache" / "overview.json").write_bytes(b"cache")
    (tmp_path / "config" / "settings.json").write_bytes(b"settings")

    inventory = OperationsReadModel(tmp_path).release_inventory()

    assert inventory["total_bytes"] == 7 + 3 + 11 + 5 + 8
    assert inventory["program_bytes"] == 10
    assert inventory["persistent_bytes"] == 24
    assert inventory["rebuildable_bytes"] == 5
    assert inventory["protected_directories"] == [
        "backups", "config", "data", "exports", "models", "news",
    ]
    assert inventory["rebuildable_directories"] == ["cache", "logs"]
