import threading
import time
from datetime import datetime, timezone

from qibao_api.gongbu.local_market_review import LocalMarketReviewSource


def test_close_cancels_local_scan_before_releasing_name_directory(
    tmp_path, monkeypatch
) -> None:
    started = threading.Event()
    resolver_calls = []

    def cancellable_loader(*_args, stop_requested, **_kwargs):
        started.set()
        while not stop_requested():
            time.sleep(0.001)
        return {}

    monkeypatch.setattr(
        "qibao_api.gongbu.local_market_review.load_tdx_daily_histories",
        cancellable_loader,
    )
    source = LocalMarketReviewSource(
        vipdoc_root=tmp_path,
        cache_path=tmp_path / "market-review.json",
        name_resolver=lambda symbol: resolver_calls.append(symbol) or symbol,
        clock=lambda: datetime(2026, 7, 31, tzinfo=timezone.utc),
        refresh_seconds=3600,
        initial_delay_seconds=0,
    )

    source.start()
    assert started.wait(timeout=1)
    source.close()

    assert source._thread is None
    assert resolver_calls == []


def test_background_review_scan_uses_bounded_worker_count(tmp_path, monkeypatch) -> None:
    loader_calls = []

    def bounded_loader(*_args, max_workers, **_kwargs):
        loader_calls.append(max_workers)
        return {}

    monkeypatch.setattr(
        "qibao_api.gongbu.local_market_review.load_tdx_daily_histories",
        bounded_loader,
    )
    source = LocalMarketReviewSource(
        vipdoc_root=tmp_path,
        cache_path=tmp_path / "market-review.json",
        name_resolver=lambda symbol: symbol,
        clock=lambda: datetime(2026, 8, 6, tzinfo=timezone.utc),
        scan_workers=2,
    )

    source.refresh(include_dragon_tiger=False)

    assert loader_calls == [2]


def test_background_review_scan_waits_for_startup_grace_period(
    tmp_path, monkeypatch
) -> None:
    started = threading.Event()

    def loader(*_args, **_kwargs):
        started.set()
        return {}

    monkeypatch.setattr(
        "qibao_api.gongbu.local_market_review.load_tdx_daily_histories",
        loader,
    )
    source = LocalMarketReviewSource(
        vipdoc_root=tmp_path,
        cache_path=tmp_path / "market-review.json",
        name_resolver=lambda symbol: symbol,
        initial_delay_seconds=60,
    )

    source.start()
    assert not started.wait(timeout=0.05)
    source.close()

    assert source._thread is None
    assert not started.is_set()
