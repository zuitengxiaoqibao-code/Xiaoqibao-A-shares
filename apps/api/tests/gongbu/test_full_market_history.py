from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from qibao_api.contracts.bars import DailyBar
from qibao_api.gongbu.full_market_history import FullMarketHistoryService
from qibao_api.gongbu.history_sync_repository import HistorySyncRepository
from qibao_api.storage.bar_repository import BarCoverage, BarCoverageAggregate


TARGET = date(2026, 7, 24)
NOW = datetime(2026, 7, 24, 8, tzinfo=timezone.utc)


def bars(symbol: str, count: int, *, source: str = "mootdx") -> list[DailyBar]:
    first = TARGET - timedelta(days=count - 1)
    return [
        DailyBar(
            symbol=symbol,
            trade_date=first + timedelta(days=index),
            open=Decimal("10"),
            high=Decimal("10.2"),
            low=Decimal("9.8"),
            close=Decimal("10"),
            volume=1000,
            amount=Decimal("10000"),
            source=source,
        )
        for index in range(count)
    ]


class Directory:
    def __init__(self, symbols):
        self.symbols = tuple(symbols)

    def active_symbols(self):
        return self.symbols


class Bars:
    def __init__(self, coverage):
        self.values = dict(coverage)
        self.writes: list[DailyBar] = []

    def coverage(self, symbols, target_date):
        return {
            symbol: BarCoverage(
                symbol=symbol,
                bar_count=self.values.get(symbol, (0, None))[0],
                latest_trade_date=self.values.get(symbol, (0, None))[1],
            )
            for symbol in symbols
        }

    def coverage_aggregate(self, symbols, target_date, *, minimum_bars, backfill_bars):
        values = self.coverage(symbols, target_date)
        latest_dates = [item.latest_trade_date for item in values.values() if item.latest_trade_date]
        dominant = max(set(latest_dates), key=latest_dates.count) if latest_dates else None
        latest = max(latest_dates) if latest_dates else None
        return BarCoverageAggregate(
            universe_count=len(symbols),
            dominant_trade_date=dominant,
            dominant_date_count=sum(item == dominant for item in latest_dates),
            latest_available_trade_date=latest,
            latest_available_trade_date_count=sum(item == latest for item in latest_dates),
            history_ready_count=sum(
                item.bar_count >= minimum_bars for item in values.values()
            ),
            backfill_complete_count=sum(
                item.bar_count >= backfill_bars for item in values.values()
            ),
        )

    def append_missing(self, values):
        self.writes.extend(values)
        if values:
            symbol = values[0].symbol
            previous = self.values.get(symbol, (0, None))[0]
            self.values[symbol] = (previous + len(values), values[-1].trade_date)
        return len(values)


class Source:
    def __init__(self, responses):
        self.responses = responses
        self.calls: list[tuple[str, int]] = []

    def fetch_daily(self, symbol, limit):
        self.calls.append((symbol, limit))
        result = self.responses[symbol]
        if isinstance(result, Exception):
            raise result
        return result


class CallbackSource(Source):
    def __init__(self, responses, callback):
        super().__init__(responses)
        self.callback = callback

    def fetch_daily(self, symbol, limit):
        self.callback()
        return super().fetch_daily(symbol, limit)


def service(tmp_path, *, symbols, coverage, tdx, baidu, threshold=20, clock=lambda: NOW, trading_calendar=None):
    return FullMarketHistoryService(
        directory=Directory(symbols),
        bar_repository=Bars(coverage),
        tdx_source=tdx,
        baidu_source=baidu,
        job_repository=HistorySyncRepository(tmp_path / "history-sync.sqlite3"),
        clock=clock,
        failure_pause_threshold=threshold,
        trading_calendar=trading_calendar,
    )


def test_default_target_is_latest_completed_trading_day_before_close(tmp_path) -> None:
    class Calendar:
        @staticmethod
        def is_trading_day(value):
            return value.weekday() < 5

    value = service(
        tmp_path, symbols=("600000",), coverage={},
        tdx=Source({"600000": []}), baidu=Source({"600000": []}),
        clock=lambda: datetime(2026, 8, 19, 6, 11, tzinfo=timezone.utc),
        trading_calendar=Calendar(),
    )

    assert value.default_target_date() == date(2026, 8, 18)
    assert value.create_backfill().target_date == date(2026, 8, 18)


def test_backfill_skips_complete_symbols_and_falls_back_to_baidu(tmp_path) -> None:
    tdx = Source({"600000": OSError("tdx unavailable")})
    baidu = Source({"600000": bars("600000", 280, source="baidu")})
    value = service(
        tmp_path,
        symbols=("000001", "600000"),
        coverage={"000001": (300, TARGET), "600000": (0, None)},
        tdx=tdx,
        baidu=baidu,
    )

    job = value.create_backfill()
    completed = value.run(job.job_id)

    assert completed.state == "completed"
    assert completed.skipped_count == 1
    assert completed.baidu_ready_count == 1
    assert completed.ready_count == 1
    assert tdx.calls == [("600000", 300)]
    assert baidu.calls == [("600000", 300)]


def test_global_source_outage_pauses_without_attempting_entire_universe(tmp_path) -> None:
    symbols = ("000001", "000002", "600000", "600001")
    failures = {symbol: OSError("offline") for symbol in symbols}
    tdx = Source(failures)
    baidu = Source(failures)
    value = service(
        tmp_path,
        symbols=symbols,
        coverage={},
        tdx=tdx,
        baidu=baidu,
        threshold=2,
    )

    paused = value.run(value.create_backfill().job_id)

    assert paused.state == "paused"
    assert paused.failed_count == 2
    assert paused.pending_count == 2
    assert len(tdx.calls) == 2
    assert len(baidu.calls) == 2


def test_incremental_writes_only_bars_after_the_latest_stored_date(tmp_path) -> None:
    latest = TARGET - timedelta(days=1)
    returned = bars("600000", 3)
    tdx = Source({"600000": returned})
    baidu = Source({})
    value = service(
        tmp_path,
        symbols=("600000",),
        coverage={"600000": (250, latest)},
        tdx=tdx,
        baidu=baidu,
    )

    completed = value.run(value.create_incremental(TARGET).job_id)

    assert completed.ready_count == 1
    assert [bar.trade_date for bar in value.bar_repository.writes] == [TARGET]
    assert tdx.calls == [("600000", 30)]
    assert baidu.calls == []


def test_coverage_reports_real_universe_eligibility_and_target_freshness(tmp_path) -> None:
    value = service(
        tmp_path,
        symbols=("000001", "600000", "688001"),
        coverage={
            "000001": (300, TARGET),
            "600000": (250, TARGET - timedelta(days=1)),
            "688001": (20, TARGET),
        },
        tdx=Source({}),
        baidu=Source({}),
    )

    summary = value.coverage(TARGET)

    assert summary.universe_count == 3
    assert summary.backfill_complete_count == 1
    assert summary.eligible_count == 2
    assert summary.target_date_count == 2
    assert summary.target_date_coverage_percent == 66.67


def test_coverage_reports_trading_day_lag_and_target_repair_only_selects_real_gaps(tmp_path) -> None:
    class Calendar:
        @staticmethod
        def is_trading_day(value):
            return value.weekday() < 5

    value = service(
        tmp_path,
        symbols=("000001", "600000", "688001"),
        coverage={
            "000001": (300, TARGET),
            "600000": (250, TARGET - timedelta(days=1)),
            "688001": (20, TARGET),
        },
        tdx=Source({}),
        baidu=Source({}),
        trading_calendar=Calendar(),
    )

    summary = value.coverage(TARGET)
    repair = value.create_target_repair(TARGET)

    assert summary.lag_trading_days == 0
    assert summary.is_fresh is True
    assert repair is not None
    assert repair.total_count == 2


def test_coverage_marks_a_dominant_date_multiple_sessions_behind_as_stale(tmp_path) -> None:
    target = date(2026, 8, 19)
    value = service(
        tmp_path,
        symbols=("000001", "600000"),
        coverage={
            "000001": (300, date(2026, 8, 14)),
            "600000": (300, date(2026, 8, 14)),
        },
        tdx=Source({}),
        baidu=Source({}),
    )

    summary = value.coverage(target)

    assert summary.lag_trading_days == 3
    assert summary.is_fresh is False
    assert summary.quality == "stale"
    assert "dominant_trade_date_behind_target" in summary.blockers


def test_repair_center_classifies_real_history_gaps(tmp_path) -> None:
    value = service(
        tmp_path,
        symbols=("600001", "600002", "600003", "600004"),
        coverage={
            "600001": (300, TARGET),
            "600002": (0, None),
            "600003": (120, TARGET),
            "600004": (280, TARGET - timedelta(days=1)),
        },
        tdx={},
        baidu={},
    )

    result = value.repair_center(TARGET, limit=10)

    assert result.coverage.dominant_trade_date == TARGET
    assert result.total_gap_count == 3
    assert [(item.symbol, item.gap_kind) for item in result.gaps] == [
        ("600002", "missing_history"),
        ("600003", "insufficient_history"),
        ("600004", "behind_dominant_date"),
    ]


def test_quality_report_uses_local_date_grid_and_flags_real_gaps(tmp_path) -> None:
    value = service(
        tmp_path,
        symbols=("600001", "600002"),
        coverage={"600001": (3, TARGET), "600002": (2, TARGET)},
        tdx=Source({}),
        baidu=Source({}),
    )
    value.bar_repository.trade_dates = lambda limit=1000: [
        TARGET, TARGET - timedelta(days=1), TARGET - timedelta(days=2)
    ]
    value.bar_repository.latest_many = lambda symbols, limit, as_of: {
        "600001": bars("600001", 3),
        "600002": [bars("600002", 1)[0], bars("600002", 1)[0]],
    }

    report = value.quality_report(limit=3)

    assert report.source == "market.duckdb/daily_bars"
    assert report.expected_sessions == 3
    assert report.status == "partial"
    assert report.gap_count == 1


def test_shutdown_request_leaves_pending_work_restartable(tmp_path) -> None:
    value = service(
        tmp_path,
        symbols=("000001", "600000"),
        coverage={},
        tdx=Source({"000001": bars("000001", 300), "600000": bars("600000", 300)}),
        baidu=Source({}),
    )
    job = value.create_backfill()

    value.request_shutdown()
    stopped = value.run(job.job_id)

    assert stopped.state == "pending"
    assert stopped.pending_count == 2
    assert value.tdx_source.calls == []


def test_backfill_fills_older_gaps_even_when_latest_date_is_current(tmp_path) -> None:
    from qibao_api.storage.bar_repository import BarRepository

    repository = BarRepository(tmp_path / "market.duckdb", tmp_path / "parquet")
    history = bars("600000", 300)
    repository.upsert(history[-5:])
    value = service(tmp_path, symbols=("600000",), coverage={},
                    tdx=Source({"600000": history}), baidu=Source({}))
    value.bar_repository = repository
    completed = value.run(value.create_backfill().job_id)
    assert completed.ready_count == 1
    assert repository.coverage(["600000"], TARGET)["600000"].bar_count == 300
    assert value.jobs.items(completed.job_id)[0].written_rows == 295


def test_target_repair_retries_remaining_gaps_after_an_incomplete_source_response(tmp_path) -> None:
    value = service(tmp_path, symbols=("600000",), coverage={},
                    tdx=Source({"600000": bars("600000", 10)}), baidu=Source({}))
    first = value.run(value.create_target_repair(TARGET).job_id)
    assert first.state == "completed"
    assert value.bar_repository.values["600000"][0] == 10
    value.tdx_source.responses["600000"] = bars("600000", 300)
    retry = value.create_target_repair(TARGET)
    assert retry.job_id == first.job_id
    assert retry.state == "pending"
    assert retry.pending_count == 1
    second = value.run(retry.job_id)
    assert second.ready_count == 1
    assert len(value.tdx_source.calls) == 2


def test_invalid_primary_history_automatically_uses_valid_backup(tmp_path) -> None:
    value = service(tmp_path, symbols=("600000",), coverage={},
                    tdx=Source({"600000": bars("000001", 300)}),
                    baidu=Source({"600000": bars("600000", 300, source="baidu")}))
    result = value.run(value.create_backfill().job_id)
    assert result.baidu_ready_count == 1
    assert all(bar.symbol == "600000" for bar in value.bar_repository.writes)


def test_pause_during_an_item_does_not_try_to_finish_pending_work(tmp_path) -> None:
    holder = {}
    tdx = CallbackSource(
        {"000001": bars("000001", 300)},
        lambda: holder["service"].pause(holder["job_id"]),
    )
    value = service(
        tmp_path,
        symbols=("000001", "600000"),
        coverage={},
        tdx=tdx,
        baidu=Source({}),
    )
    holder["service"] = value
    job = value.create_backfill()
    holder["job_id"] = job.job_id

    paused = value.run(job.job_id)

    assert paused.state == "paused"
    assert paused.ready_count == 1
    assert paused.pending_count == 1
