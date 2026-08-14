import threading
import time
from datetime import datetime, timezone
from decimal import Decimal

from qibao_api.contracts.bars import DailyBar
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


def test_review_prefers_current_verified_bar_repository_over_stale_tdx_files(tmp_path) -> None:
    class Repository:
        def latest_many(self, symbols, limit, as_of):
            assert symbols == ["600001"]
            assert limit == 252
            return {"600001": [
                DailyBar(
                    symbol="600001", trade_date="2026-08-06", open=Decimal("10"),
                    high=Decimal("10"), low=Decimal("10"), close=Decimal("10"),
                    volume=100, amount=Decimal("100000"), source="baidu",
                ),
                DailyBar(
                    symbol="600001", trade_date="2026-08-07", open=Decimal("11"),
                    high=Decimal("11"), low=Decimal("11"), close=Decimal("11"),
                    volume=200, amount=Decimal("200000"), source="baidu",
                ),
            ]}

    source = LocalMarketReviewSource(
        vipdoc_root=tmp_path,
        cache_path=tmp_path / "market-review.json",
        name_resolver=lambda symbol: "测试股",
        bar_repository=Repository(),
        symbol_provider=lambda: ("600001",),
        clock=lambda: datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc),
    )

    result = source.refresh(as_of=datetime(2026, 8, 7, tzinfo=timezone.utc).date(), include_dragon_tiger=False)

    assert result.latest_trade_date.isoformat() == "2026-08-07"
    assert result.source == "market-db"


def test_review_uses_bar_repository_when_no_tdx_vipdoc_root_is_selected(tmp_path) -> None:
    class Repository:
        def latest_many(self, symbols, limit, as_of):
            return {"600001": [
                DailyBar(
                    symbol="600001", trade_date="2026-08-06", open=Decimal("10"),
                    high=Decimal("10"), low=Decimal("10"), close=Decimal("10"),
                    volume=100, amount=Decimal("100000"), source="baidu",
                ),
                DailyBar(
                    symbol="600001", trade_date="2026-08-07", open=Decimal("11"),
                    high=Decimal("11"), low=Decimal("11"), close=Decimal("11"),
                    volume=200, amount=Decimal("200000"), source="baidu",
                ),
            ]}

    source = LocalMarketReviewSource(
        vipdoc_root=None,
        cache_path=tmp_path / "market-review.json",
        name_resolver=lambda symbol: "测试股",
        bar_repository=Repository(),
        symbol_provider=lambda: ("600001",),
        clock=lambda: datetime(2026, 8, 7, 9, 0, tzinfo=timezone.utc),
    )

    result = source.refresh(
        as_of=datetime(2026, 8, 7, tzinfo=timezone.utc).date(),
        include_dragon_tiger=False,
    )

    assert result.latest_trade_date.isoformat() == "2026-08-07"
    assert result.source == "market-db"


def test_stale_disk_review_cache_is_not_loaded_when_repository_has_newer_day(tmp_path) -> None:
    class Repository:
        def __init__(self, latest_date):
            self.latest_date = latest_date

        def trade_dates(self, limit=1):
            assert limit == 1
            return [self.latest_date]

        def latest_many(self, symbols, limit, as_of):
            return {"600001": [
                DailyBar(
                    symbol="600001", trade_date="2026-07-17", open=Decimal("10"),
                    high=Decimal("10"), low=Decimal("10"), close=Decimal("10"),
                    volume=100, amount=Decimal("100000"), source="baidu",
                ),
            ]}

    cache_path = tmp_path / "market-review.json"
    stale = LocalMarketReviewSource(
        vipdoc_root=None,
        cache_path=cache_path,
        name_resolver=lambda symbol: "测试股",
        bar_repository=Repository("2026-07-17"),
        symbol_provider=lambda: ("600001",),
        clock=lambda: datetime(2026, 7, 17, tzinfo=timezone.utc),
    )
    stale.refresh(as_of=datetime(2026, 7, 17, tzinfo=timezone.utc).date(), include_dragon_tiger=False)

    current = LocalMarketReviewSource(
        vipdoc_root=None,
        cache_path=cache_path,
        name_resolver=lambda symbol: "测试股",
        bar_repository=Repository("2026-08-06"),
        symbol_provider=lambda: ("600001",),
        clock=lambda: datetime(2026, 8, 7, tzinfo=timezone.utc),
    )

    assert current.current() is None


def test_deferred_cache_validation_does_not_touch_bar_store_during_construction(
    tmp_path,
) -> None:
    cache_path = tmp_path / "market-review.json"
    seed = LocalMarketReviewSource(
        vipdoc_root=None,
        cache_path=cache_path,
        name_resolver=lambda symbol: symbol,
        clock=lambda: datetime(2026, 8, 11, tzinfo=timezone.utc),
    )
    seed.refresh(include_dragon_tiger=False)

    class Repository:
        def trade_dates(self, limit=1):
            raise AssertionError("bar store must not open on the startup path")

    deferred = LocalMarketReviewSource(
        vipdoc_root=None,
        cache_path=cache_path,
        name_resolver=lambda symbol: symbol,
        bar_repository=Repository(),
        defer_cache_validation=True,
    )

    assert deferred.current() is None
    assert deferred.cache_is_stale()
