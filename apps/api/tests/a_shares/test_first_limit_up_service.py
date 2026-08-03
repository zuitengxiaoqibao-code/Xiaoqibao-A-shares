import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from qibao_api.a_shares.first_limit_up import evaluate_first_limit_up
from qibao_api.a_shares.first_limit_up_repository import FirstLimitUpRepository
from qibao_api.a_shares.first_limit_up_service import (
    FirstLimitUpService,
    SynchronousTencentQuoteSource,
)
from qibao_api.contracts.bars import DailyBar
from qibao_api.gongbu.tencent_quotes import TencentMarketSnapshot

from .test_first_limit_up import AS_OF, _business_days_ending, _first_board_history, _bar


class FakeBars:
    def __init__(self, histories: dict[str, list[DailyBar]]):
        self.histories = histories

    def symbols_with_history(self, minimum_bars: int, as_of: date, *, cutoff=None):
        return [symbol for symbol, bars in self.histories.items() if len(bars) >= minimum_bars]

    def latest_many(self, symbols, limit: int, as_of: date, *, cutoff=None):
        return {symbol: self.histories.get(symbol, [])[-limit:] for symbol in symbols}


class ActiveDirectory:
    def __init__(self, symbols: tuple[str, ...]) -> None:
        self.symbols = symbols

    def active_symbols(self) -> tuple[str, ...]:
        return self.symbols


class FakeQuotes:
    def __init__(self, snapshots: dict[str, TencentMarketSnapshot], *, fail=False):
        self.snapshots = snapshots
        self.fail = fail
        self.calls: list[str] = []

    async def fetch_snapshot(self, symbol: str):
        self.calls.append(symbol)
        if self.fail:
            raise OSError("quote source unavailable")
        return self.snapshots[symbol]


class BatchQuotes:
    def __init__(self, snapshots: dict[str, TencentMarketSnapshot]):
        self.snapshots = snapshots
        self.batch_calls: list[tuple[str, ...]] = []
        self.single_calls: list[str] = []

    async def fetch_many(self, symbols):
        self.batch_calls.append(tuple(symbols))
        return self.snapshots

    async def fetch_snapshot(self, symbol: str):
        self.single_calls.append(symbol)
        raise AssertionError("batch-capable source must not fetch one symbol at a time")


class FakeCompliance:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def require_feature_sources(self, feature: str, market: str) -> None:
        self.calls.append((feature, market))


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content

    def raise_for_status(self) -> None:
        return None


class FakeBatchClient:
    def __init__(self, *, omitted: set[str] | None = None, fail_call: int | None = None):
        self.omitted = omitted or set()
        self.fail_call = fail_call
        self.urls: list[str] = []

    def get(self, url: str):
        self.urls.append(url)
        if self.fail_call == len(self.urls):
            raise OSError("batch unavailable")
        instruments = url.rsplit("=", 1)[1].split(",")
        rows = []
        for instrument in instruments:
            symbol = instrument[-6:]
            if symbol in self.omitted:
                continue
            fields = [""] * 47
            fields[1] = f"Stock {symbol}"
            fields[2] = symbol
            fields[3] = "11"
            fields[4] = "10"
            fields[6] = "1000"
            fields[30] = "20260724150000"
            fields[38] = "2.5"
            fields[39] = "22"
            fields[44] = "100"
            fields[46] = "1.5"
            rows.append(f'v_{instrument}="{"~".join(fields)}";')
        return FakeResponse("\n".join(rows).encode("gbk"))


def quote(symbol: str, name: str, pe: str) -> TencentMarketSnapshot:
    return TencentMarketSnapshot(
        symbol=symbol,
        name=name,
        price=Decimal("11"),
        previous_close=Decimal("10"),
        observed_at=datetime(2026, 7, 24, 7, 0, tzinfo=timezone.utc),
        turnover_rate=None,
        pe_ttm=Decimal(pe),
        market_cap_yi=None,
        pb=None,
        source="fixture",
    )


def test_synchronous_tencent_source_batches_requests_and_keeps_partial_results() -> None:
    symbols = tuple(f"{600001 + index:06d}" for index in range(161))
    client = FakeBatchClient(omitted={symbols[5]}, fail_call=2)
    compliance = FakeCompliance()
    source = SynchronousTencentQuoteSource(client, compliance)

    result = source.fetch_many(symbols)

    assert len(client.urls) == 3
    assert all(url.count(",") <= 79 for url in client.urls)
    assert symbols[0] in result
    assert symbols[5] not in result
    assert symbols[80] not in result
    assert symbols[160] in result
    assert compliance.calls == [("realtime_quotes", "a_share")]


@pytest.mark.asyncio
async def test_refresh_uses_one_batch_enrichment_for_eligible_events(tmp_path) -> None:
    histories = {"600001": _first_board_history(), "600002": _first_board_history("600002")}
    quotes = BatchQuotes({
        "600001": quote("600001", "Batch One", "22"),
        "600002": quote("600002", "Batch Two", "25"),
    })
    service = FirstLimitUpService(
        bar_repository=FakeBars(histories),
        quote_source=quotes,
        repository=FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3"),
    )

    board = await service.refresh(AS_OF)

    assert board.qualified_count == 2
    assert quotes.batch_calls == [("600001", "600002")]
    assert quotes.single_calls == []


@pytest.mark.asyncio
async def test_refresh_scans_limit_up_events_persists_only_qualified_candidates(tmp_path) -> None:
    histories = {"600001": _first_board_history(), "600002": _first_board_history("600002")}
    bars = FakeBars(histories)
    quotes = FakeQuotes({
        "600001": quote("600001", "底部样本", "22"),
        "600002": quote("600002", "高估值样本", "55"),
    })
    service = FirstLimitUpService(
        bar_repository=bars,
        quote_source=quotes,
        repository=FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3"),
    )

    board = await service.refresh(AS_OF)

    assert board.qualified_count == 1
    assert [item.symbol for item in board.pool] == ["600001"]
    assert board.today[0].name == "底部样本"
    assert quotes.calls == ["600001", "600002"]


@pytest.mark.asyncio
async def test_refresh_keeps_historical_limit_up_out_of_current_scan_count(tmp_path) -> None:
    days = _business_days_ending(AS_OF, 270)
    limit_up_date = days[-6]
    history = [_bar("600001", day, "10.00") for day in days]
    history[days.index(limit_up_date)] = _bar("600001", limit_up_date, "11.00")
    quotes = FakeQuotes({"600001": quote("600001", "历史首板", "22")})
    service = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=quotes,
        repository=FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3"),
    )

    board = await service.refresh(AS_OF)

    assert board.today == ()
    assert board.scanned_count == 0
    assert board.status == "ready"
    assert [item.symbol for item in board.pool] == ["600001"]
    assert board.pool[0].limit_up_date == limit_up_date
    assert board.pool[0].stage == "pullback_window"


@pytest.mark.asyncio
async def test_refresh_exposes_scanned_event_when_no_candidate_qualifies(tmp_path) -> None:
    history = _first_board_history()
    quotes = FakeQuotes({"600001": quote("600001", "排除样本", "55")})
    service = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=quotes,
        repository=FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3"),
    )

    board = await service.refresh(AS_OF)

    assert board.status == "partial"
    assert [item.symbol for item in board.today] == ["600001"]
    assert board.pool == ()
    assert board.qualified_count == 0
    assert board.today[0].selection_status == "excluded"
    assert "pe_above_50" in board.today[0].reasons


@pytest.mark.asyncio
async def test_refresh_keeps_excluded_scan_visible_after_reload(tmp_path) -> None:
    history = _first_board_history()
    repository = FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3")
    service = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=FakeQuotes({
            "600001": quote("600001", "排除样本", "55"),
        }),
        repository=repository,
    )

    refreshed = await service.refresh(AS_OF)
    reloaded = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=FakeQuotes({}),
        repository=repository,
    ).current(AS_OF)

    assert [item.symbol for item in refreshed.today] == ["600001"]
    assert [item.symbol for item in reloaded.today] == ["600001"]
    assert reloaded.today[0].selection_status == "excluded"
    assert reloaded.pool == ()
    assert reloaded.scanned_count == 1
    assert reloaded.qualified_count == 0


def test_current_recalculates_pullback_state_without_discarding_month_pool(tmp_path) -> None:
    initial = _first_board_history()
    candidate = evaluate_first_limit_up(
        symbol="600001", name="回撤样本", bars=initial, pe_ttm=Decimal("22"), as_of=AS_OF
    )
    assert candidate is not None
    future_days = _business_days_ending(date(2026, 7, 31), 5)
    histories = {"600001": [*initial, *[_bar("600001", day, "10.20") for day in future_days]]}
    repository = FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3")
    repository.upsert_many([candidate])
    service = FirstLimitUpService(
        bar_repository=FakeBars(histories),
        quote_source=FakeQuotes({}),
        repository=repository,
    )

    board = service.current(future_days[-1])

    assert len(board.pool) == 1
    assert board.pool[0].stage == "pullback_window"
    assert board.priority_symbol == "600001"


@pytest.mark.asyncio
async def test_refresh_source_failure_keeps_existing_pool_and_marks_partial(tmp_path) -> None:
    initial = _first_board_history()
    candidate = evaluate_first_limit_up(
        symbol="600001", name="历史样本", bars=initial, pe_ttm=Decimal("22"), as_of=AS_OF
    )
    assert candidate is not None
    repository = FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3")
    repository.upsert_many([candidate])
    service = FirstLimitUpService(
        bar_repository=FakeBars({"600001": initial}),
        quote_source=FakeQuotes({"600001": quote("600001", "历史样本", "22")}, fail=True),
        repository=repository,
    )

    board = await service.refresh(AS_OF)

    assert board.status == "partial"
    assert [item.symbol for item in board.pool] == ["600001"]
    assert "quote_source_unavailable" in board.missing_data


@pytest.mark.asyncio
async def test_refresh_discloses_and_persists_partial_universe_coverage(tmp_path) -> None:
    history = _first_board_history()
    repository = FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3")
    directory = ActiveDirectory(("000001", "600001"))
    service = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=FakeQuotes({
            "600001": quote("600001", "局部样本", "22"),
        }),
        repository=repository,
        universe_provider=directory,
    )

    board = await service.refresh(AS_OF)
    reloaded = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=FakeQuotes({}),
        repository=repository,
        universe_provider=directory,
    ).current(AS_OF)

    assert board.universe_count == 2
    assert board.history_eligible_count == 1
    assert board.scan_coverage_count == 1
    assert board.coverage_complete is False
    assert board.status == "partial"
    assert reloaded.universe_count == 2
    assert reloaded.scan_coverage_count == 1
    assert reloaded.coverage_complete is False


@pytest.mark.asyncio
async def test_partial_refresh_reports_current_results_without_previous_scan_substitution(tmp_path) -> None:
    repository = FirstLimitUpRepository(tmp_path / "first-limit-up.sqlite3")
    complete = FirstLimitUpService(
        bar_repository=FakeBars({"600001": _first_board_history()}),
        quote_source=FakeQuotes({
            "600001": quote("600001", "完整扫描样本", "22"),
        }),
        repository=repository,
        universe_provider=ActiveDirectory(("600001",)),
    )
    await complete.refresh(AS_OF)

    partial = FirstLimitUpService(
        bar_repository=FakeBars({"600002": _first_board_history("600002")}),
        quote_source=FakeQuotes({
            "600002": quote("600002", "局部扫描样本", "22"),
        }),
        repository=repository,
        universe_provider=ActiveDirectory(("000001", "600002")),
    )
    board = await partial.refresh(AS_OF)

    assert board.coverage_complete is False
    assert board.status == "partial"
    assert [item.symbol for item in board.today] == ["600002"]


def test_current_ignores_legacy_scan_candidates_without_provenance(tmp_path) -> None:
    history = _first_board_history()
    candidate = evaluate_first_limit_up(
        symbol="600001",
        name="legacy sample",
        bars=history,
        pe_ttm=Decimal("22"),
        as_of=AS_OF,
    )
    assert candidate is not None
    database_path = tmp_path / "first-limit-up.sqlite3"
    repository = FirstLimitUpRepository(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO first_limit_up_scans (scan_date, payload, updated_at)
            VALUES (?, ?, ?)
            """,
            (
                AS_OF.isoformat(),
                json.dumps([candidate.model_dump(mode="json")]),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    service = FirstLimitUpService(
        bar_repository=FakeBars({"600001": history}),
        quote_source=FakeQuotes({}),
        repository=repository,
        universe_provider=ActiveDirectory(("000001", "600001")),
    )

    board = service.current(AS_OF)

    assert board.universe_count == 2
    assert board.history_eligible_count == 1
    assert board.scan_coverage_count == 0
    assert board.coverage_complete is False
    assert board.today == ()
    assert board.scanned_count == 0
    assert board.qualified_count == 0
    assert board.no_buy_count == 0
    assert "full_market_scan_required" in board.missing_data
