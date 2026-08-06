import struct
from datetime import date, datetime, timezone
from decimal import Decimal

from qibao_api.contracts.market_overview import (
    OverviewBreadth,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewMarketSnapshot,
)
from qibao_api.gongbu.tdx_local_daily import (
    LocalTdxDailyFactorBuilder,
    LocalTdxMarketSentimentSource,
    load_tdx_daily_histories,
    read_tdx_day_bars,
)


NOW = datetime(2026, 7, 29, 7, 1, tzinfo=timezone.utc)


def test_history_loader_skips_files_after_stop_is_requested(tmp_path, monkeypatch) -> None:
    lday = tmp_path / "sh" / "lday"
    lday.mkdir(parents=True)
    for index in range(20):
        (lday / f"sh{600001 + index:06d}.day").write_bytes(b"fixture")
    reads = []
    monkeypatch.setattr(
        "qibao_api.gongbu.tdx_local_daily.read_tdx_day_bars",
        lambda *args, **kwargs: reads.append((args, kwargs)) or (),
    )

    histories = load_tdx_daily_histories(
        tmp_path,
        as_of=date(2026, 7, 29),
        stop_requested=lambda: True,
    )

    assert histories == {}
    assert reads == []


def test_read_tdx_day_bars_decodes_prices_amount_and_date(tmp_path) -> None:
    path = tmp_path / "sh600000.day"
    path.write_bytes(struct.pack(
        "<IIIIIfII",
        20260729, 919, 934, 917, 933, 609_194_112.0, 65_595_100, 0,
    ))

    bars = read_tdx_day_bars(path, symbol="600000", as_of=date(2026, 7, 29))

    assert len(bars) == 1
    assert bars[0].trade_date == date(2026, 7, 29)
    assert bars[0].close == Decimal("9.33")
    assert bars[0].amount == Decimal("609194112.0")


def test_read_tdx_day_bars_can_load_an_explicit_interval_without_tail_truncation(tmp_path) -> None:
    path = tmp_path / "sh600000.day"
    path.write_bytes(b"".join([
        struct.pack("<IIIIIfII", 20200102, 1000, 1010, 990, 1000, 100.0, 10, 0),
        struct.pack("<IIIIIfII", 20260701, 1200, 1210, 1190, 1200, 200.0, 20, 0),
        struct.pack("<IIIIIfII", 20260729, 1300, 1310, 1290, 1300, 300.0, 30, 0),
    ]))

    bars = read_tdx_day_bars(
        path,
        symbol="600000",
        as_of=date(2026, 7, 29),
        start_date=date(2026, 7, 1),
        limit=None,
    )

    assert [item.trade_date for item in bars] == [date(2026, 7, 1), date(2026, 7, 29)]


def test_local_tdx_sentiment_source_converts_cached_realtime_snapshot() -> None:
    snapshot = OverviewMarketSnapshot(
        observed_at=NOW,
        source="tdx-local-rpc",
        quality="ready",
        quote_count=5191,
        universe_count=5207,
        median_change_percent=Decimal("0.42"),
        breadth=OverviewBreadth(
            rising_count=3144, falling_count=1951,
            flat_count=96, valid_count=5191,
        ),
        limit_ecology=OverviewLimitEcology(
            limit_up_count=60, limit_down_count=21,
            broken_limit_up_count=40, seal_rate_percent=Decimal("60"),
        ),
        liquidity=OverviewLiquidity(total_amount_yi=Decimal("13859.09")),
    )
    source = LocalTdxMarketSentimentSource(
        overview_source=type("Overview", (), {"current": lambda _self: snapshot})(),
    )

    result = source.fetch(cutoff=NOW)

    assert result.observation.requested_count == 5207
    assert result.observation.valid_count == 5191
    assert result.observation.median_change_percent == Decimal("0.42")
    assert result.observation.total_amount_wan == Decimal("138590900")
    assert result.observation.source_snapshot_ids[0].startswith("tdx-local-market-")


def test_local_daily_factor_builder_adds_history_and_intraday_activity(tmp_path) -> None:
    lday = tmp_path / "sh" / "lday"
    lday.mkdir(parents=True)
    records = []
    for day in range(1, 61):
        raw_date = 20260400 + day if day <= 30 else 20260500 + day - 30
        close = 1000 + day
        records.append(struct.pack(
            "<IIIIIfII", raw_date, close - 2, close + 2, close - 4,
            close, 100_000_000.0, 1_000_000, 0,
        ))
    (lday / "sh600000.day").write_bytes(b"".join(records))
    overview = type("Overview", (), {"current": lambda _self: OverviewMarketSnapshot(
        observed_at=NOW, source="tdx-local-rpc", quality="ready",
        quote_count=1, universe_count=1, median_change_percent=Decimal("1"),
        breadth=OverviewBreadth(rising_count=1, falling_count=0, flat_count=0, valid_count=1),
        limit_ecology=OverviewLimitEcology(limit_up_count=0, limit_down_count=0, broken_limit_up_count=0),
        liquidity=OverviewLiquidity(total_amount_yi=Decimal("1")),
    )})()

    factors = LocalTdxDailyFactorBuilder(
        vipdoc_root=tmp_path,
        overview_source=overview,
        cache_path=tmp_path / "factor-cache.json",
    ).build(as_of=date(2026, 5, 30), cutoff=NOW)

    assert factors.effective_count == 1
    assert factors.ma20_above_count == 1
    assert factors.five_day_rising_count == 1
    assert factors.relative_amount is not None
    assert (tmp_path / "factor-cache.json").exists()


def test_local_daily_factor_builder_reuses_same_day_cache(tmp_path, monkeypatch) -> None:
    cache_path = tmp_path / "factor-cache.json"
    cache_path.write_text(
        '{"as_of":"2026-07-29","baseline_amount_wan":"10000",'
        '"factors":{"effective_count":1,"ma20_above_count":1,'
        '"ma60_above_count":1,"five_day_rising_count":1,'
        '"sixty_day_new_low_count":0,"new_high_252_count":0,'
        '"evidence_ids":["tdx-local-day"]}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "qibao_api.gongbu.tdx_local_daily.load_tdx_daily_histories",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("cache missed")),
    )
    overview = type("Overview", (), {"current": lambda _self: OverviewMarketSnapshot(
        observed_at=NOW, source="tdx-local-rpc", quality="ready",
        quote_count=1, universe_count=1, median_change_percent=Decimal("1"),
        breadth=OverviewBreadth(rising_count=1, falling_count=0, flat_count=0, valid_count=1),
        limit_ecology=OverviewLimitEcology(limit_up_count=0, limit_down_count=0, broken_limit_up_count=0),
        liquidity=OverviewLiquidity(total_amount_yi=Decimal("1")),
    )})()

    factors = LocalTdxDailyFactorBuilder(
        vipdoc_root=tmp_path,
        overview_source=overview,
        cache_path=cache_path,
    ).build(as_of=date(2026, 7, 29), cutoff=NOW)

    assert factors.effective_count == 1
    assert factors.relative_amount == Decimal("1.0000")
