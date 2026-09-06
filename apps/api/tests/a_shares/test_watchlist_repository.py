from pathlib import Path

import pytest

from qibao_api.a_shares.watchlist_repository import WatchlistRepository


def test_watchlist_repository_round_trips_valid_codes_and_deduplicates(tmp_path: Path) -> None:
    repository = WatchlistRepository(tmp_path / "config" / "a-share-watchlist.json")

    saved = repository.save(["600519", "000001", "600519"])

    assert saved.symbols == ("600519", "000001")
    assert repository.load().symbols == ("600519", "000001")
    assert repository.load().updated_at is not None


def test_watchlist_repository_rejects_non_a_share_codes(tmp_path: Path) -> None:
    repository = WatchlistRepository(tmp_path / "watchlist.json")

    with pytest.raises(ValueError, match="A 股代码"):
        repository.save(["123456", "600519"])


def test_watchlist_repository_ignores_invalid_existing_file(tmp_path: Path) -> None:
    path = tmp_path / "watchlist.json"
    path.write_text("{not-json", encoding="utf-8")

    snapshot = WatchlistRepository(path).load()

    assert snapshot.symbols == ()
    assert snapshot.updated_at is None
