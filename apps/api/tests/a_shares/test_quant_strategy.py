from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from qibao_api.a_shares.models import CandidateBoard, CandidateEntry, FactorSnapshot
from qibao_api.a_shares.quant_strategy import (
    ArchivedTriggerEvidenceSource,
    QuantStrategyService,
    TriggerEvidence,
    build_quant_strategy_dashboard,
)
from qibao_api.contracts.market_overview import (
    MarketOverviewResponse,
    OverviewBreadth,
    OverviewFeatureStock,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewMarketDataStatus,
    OverviewRegimeAssessment,
    OverviewRegimeMetrics,
    OverviewSentiment,
)
from qibao_api.contracts.quant_strategy import QuantStrategyCandidate
from qibao_api.gongbu.market_feed import MarketFeedSnapshot


NOW = datetime(2026, 7, 31, 6, 0, tzinfo=timezone.utc)


def factor(symbol: str, score: Decimal = Decimal("81")) -> CandidateEntry:
    snapshot = FactorSnapshot(
        symbol=symbol,
        as_of=date(2026, 7, 31),
        latest_trade_date=date(2026, 7, 31),
        close=Decimal("10"),
        return_5d=Decimal("0.04"),
        return_20d=Decimal("0.12"),
        distance_ma20=Decimal("0.03"),
        volume_ratio_5_20=Decimal("1.4"),
        volatility_20d=Decimal("0.025"),
        drawdown_60d=Decimal("-0.12"),
        liquidity_amount_20d=Decimal("80000000"),
        source="tdx-local-daily",
    )
    return CandidateEntry(
        symbol=symbol,
        horizon="short_term",
        score=score,
        score_breakdown={"momentum": score},
        factor_snapshot=snapshot,
    )


def overview(*, quote: bool = True, regime: str = "情绪主升") -> MarketOverviewResponse:
    metrics = OverviewRegimeMetrics(
        up_ratio=Decimal("66"),
        zt_ratio=Decimal("1.4"),
        dt_ratio=Decimal("0.1"),
        median_ret=Decimal("1.2"),
        amt_heat=Decimal("1.15"),
        strong_close_ratio=Decimal("72"),
        weak_close_ratio=Decimal("12"),
        limit_fail_ratio=Decimal("18"),
        panic_ratio=Decimal("2"),
        amp_ratio=Decimal("18"),
        net_positive_ratio=None,
        large_amount_strong_close_ratio=Decimal("70"),
        factor_coverage_percent=Decimal("90.91"),
    )
    regime_value = OverviewRegimeAssessment(
        regime=regime,
        emotion_score=Decimal("76"),
        risk_score=Decimal("22"),
        heat_score=Decimal("68"),
        rotation_score=Decimal("35"),
        coverage_percent=Decimal("85"),
        market_coef=Decimal("1"),
        suitable_strategies=("0轴低吸模型", "分歧转一致模型"),
        avoid_strategies=("后排追涨",),
        reasons=("情绪分达到阈值",),
        missing_factors=("net_positive_ratio",),
        rule_matched=True,
        quality="partial",
    )
    stocks = ()
    if quote:
        stocks = (OverviewFeatureStock(
            symbol="600001",
            name="样本股份",
            price=Decimal("10.10"),
            previous_close=Decimal("10"),
            open=Decimal("9.98"),
            high=Decimal("10.20"),
            low=Decimal("9.90"),
            volume=Decimal("1000000"),
            amount_yi=Decimal("2.5"),
            change_percent=Decimal("1"),
            state="active",
            observed_at=NOW,
            source="tdx-local-realtime",
            quality="ready",
        ),)
    breadth = OverviewBreadth(
        rising_count=3300, falling_count=1500, flat_count=200, valid_count=5000
    )
    return MarketOverviewResponse(
        status="partial",
        as_of=date(2026, 7, 31),
        observed_at=NOW,
        sentiment=OverviewSentiment(
            score=Decimal("72"), band="active", coverage_percent=Decimal("90"),
            quality="partial", observed_at=NOW,
        ),
        breadth=breadth,
        limit_ecology=OverviewLimitEcology(
            limit_up_count=70, limit_down_count=5, broken_limit_up_count=12,
            seal_rate_percent=Decimal("85"),
        ),
        liquidity=OverviewLiquidity(
            total_amount_yi=Decimal("11000"), baseline_amount_yi=Decimal("9600"),
            relative_amount=Decimal("1.15"),
        ),
        regime_metrics=metrics,
        regime=regime_value,
        market_data=OverviewMarketDataStatus(
            source="tdx-local-realtime", quality="ready", observed_at=NOW,
            quote_count=5000, universe_count=5200,
        ),
        market_stocks=stocks,
        sources=("tdx-local-realtime", "tdx-local-daily"),
    )


def board() -> CandidateBoard:
    item = factor("600001")
    return CandidateBoard(
        as_of=date(2026, 7, 31),
        universe_size=5000,
        eligible_size=4200,
        latest_trade_date=date(2026, 7, 31),
        sources=("tdx-local-daily",),
        short_term=[item],
        swing=[],
    )


def test_strategy_formula_and_missing_trigger_gate_are_explicit() -> None:
    result = build_quant_strategy_dashboard(
        overview(), board(), names={"600001": "样本股份"}, generated_at=NOW
    )

    candidate = result.candidates[0]
    expected = (
        candidate.regime_match * Decimal("40")
        + candidate.stock_score * Decimal("30")
        + candidate.trigger_score * Decimal("20")
        + candidate.rr_score * Decimal("10")
        - candidate.risk_penalty
    ).quantize(Decimal("0.01"))
    assert candidate.strategy_score == expected
    assert candidate.model == "0轴低吸模型"
    assert candidate.status == "pending_trigger"
    assert candidate.trigger_confirmed is False
    assert candidate.trigger_score == Decimal("0")
    assert "three_minute_return" in candidate.missing_evidence
    assert result.regime.regime == "情绪主升"
    assert result.metrics.net_positive_ratio is None
    assert candidate.rr_score == Decimal("0")
    assert "缺少明确止损/目标价，盈亏比分不计分" in candidate.risk_flags
    assert {item.name for item in result.strategy_models} == {
        "0轴低吸模型", "恐慌低吸模型", "权重容量低吸模型",
        "分歧转一致模型", "反核修复模型", "空仓防守模型",
    }
    assert result.generated_at == NOW
    assert result.market_observed_at == NOW
    assert result.data_age_seconds == 0
    assert result.refresh_mode == "live"
    assert result.next_refresh_at == NOW + timedelta(seconds=5)


def test_strategy_marks_old_market_snapshot_stale_without_changing_values() -> None:
    generated_at = NOW + timedelta(minutes=3)

    result = build_quant_strategy_dashboard(
        overview(), board(), names={"600001": "样本股份"},
        generated_at=generated_at,
    )

    assert result.generated_at == generated_at
    assert result.market_observed_at == NOW
    assert result.data_age_seconds == 180
    assert result.refresh_mode == "stale"
    assert result.next_refresh_at == generated_at + timedelta(seconds=30)
    assert result.metrics.up_ratio == Decimal("66")


def test_strategy_preserves_previous_close_semantics_from_market_overview() -> None:
    previous_close = overview().model_copy(update={
        "market_data": overview().market_data.model_copy(update={
            "phase": "premarket", "freshness": "previous_close",
        }),
    })

    result = build_quant_strategy_dashboard(
        previous_close,
        board(),
        names={"600001": "样本股份"},
        generated_at=NOW,
    )

    assert result.refresh_mode == "postclose"


def test_complete_real_trigger_evidence_can_reach_alert() -> None:
    result = build_quant_strategy_dashboard(
        overview(),
        board(),
        names={"600001": "样本股份"},
        trigger_evidence={
            "600001": TriggerEvidence(
                vwap_support=True,
                three_minute_return=Decimal("0.01"),
                net_large_flow_positive=True,
                close_position_rising=True,
                sources=("intraday-poll", "eastmoney-fund-flow"),
            )
        },
    )

    candidate = result.candidates[0]
    assert candidate.trigger_score == Decimal("1")
    assert candidate.trigger_confirmed is True
    assert candidate.status == "alert"
    assert candidate.missing_evidence == ()
    assert "intraday-poll" in candidate.sources


def test_archived_trigger_source_uses_real_ticks_and_fund_flow() -> None:
    ticks = (
        MarketFeedSnapshot(
            symbol="600001", price=Decimal("9.95"), change=Decimal("-0.05"),
            change_percent=Decimal("-0.5"), volume=Decimal("100"),
            source="tdx-local-realtime", observed_at=NOW - timedelta(minutes=3),
            fetched_at=NOW - timedelta(minutes=3), quality="ready",
            source_snapshot_id="tick-1",
        ),
        MarketFeedSnapshot(
            symbol="600001", price=Decimal("10.10"), change=Decimal("0.10"),
            change_percent=Decimal("1"), volume=Decimal("300"),
            source="tdx-local-realtime", observed_at=NOW,
            fetched_at=NOW, quality="ready", source_snapshot_id="tick-2",
        ),
    )
    poll_repository = SimpleNamespace(
        intraday_snapshots=lambda symbol, trading_date, cutoff: ticks
    )
    flow = SimpleNamespace(
        latest_trade_date=date(2026, 7, 31),
        intraday_main_net=Decimal("1200000"),
        latest_super_net=Decimal("400000"),
        latest_large_net=Decimal("800000"),
        source="eastmoney-fund-flow",
    )
    flow_repository = SimpleNamespace(
        latest=lambda symbol, as_of, cutoff: flow
    )

    evidence = ArchivedTriggerEvidenceSource(
        poll_repository, flow_repository
    ).get("600001", date(2026, 7, 31), NOW, overview().market_stocks[0])

    assert evidence.vwap_support is True
    assert evidence.three_minute_return > 0
    assert evidence.net_large_flow_positive is True
    assert evidence.net_fund_flow_positive is True
    assert evidence.close_position_rising is True


def test_missing_realtime_quote_never_becomes_a_buy_alert() -> None:
    result = build_quant_strategy_dashboard(
        overview(quote=False), board(), names={"600001": "样本股份"}
    )

    candidate = result.candidates[0]
    assert candidate.trigger_score == Decimal("0")
    assert candidate.status == "pending_trigger"
    assert candidate.position == Decimal("0")
    assert "realtime_quote" in candidate.missing_evidence


def test_defensive_regime_returns_discipline_without_forced_stock_pick() -> None:
    defensive = overview(regime="高位退潮").model_copy(update={
        "regime": overview().regime.model_copy(update={
            "regime": "高位退潮",
            "market_coef": Decimal("0.2"),
            "suitable_strategies": ("空仓防守模型",),
            "avoid_strategies": ("高位接力", "一致加速"),
        })
    })
    result = build_quant_strategy_dashboard(
        defensive, board(), names={"600001": "样本股份"}
    )

    assert result.candidates == ()
    assert result.discipline.startswith("高位退潮")
    assert result.status == "partial"
    assert next(
        item for item in result.strategy_models if item.name == "空仓防守模型"
    ).selected is True


def test_service_rejects_historical_candidates_mixed_with_current_regime() -> None:
    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates=lambda as_of, limit: board()),
        SimpleNamespace(resolve=lambda symbol: None),
    )

    with pytest.raises(ValueError, match="historical market regime"):
        service.current(NOW, as_of=date(2026, 7, 30))


def test_service_reuses_candidate_evidence_within_refresh_window() -> None:
    calls = 0

    def load_board(_as_of, _limit):
        nonlocal calls
        calls += 1
        return board()

    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates=load_board),
        SimpleNamespace(resolve=lambda symbol: None),
        cache_seconds=5,
    )

    first = service.current(NOW)
    second = service.current(NOW + timedelta(seconds=4))
    third = service.current(NOW + timedelta(seconds=6))

    assert calls == 2
    assert first.candidates == second.candidates == third.candidates
    assert first.candidate_scan_cached is False
    assert first.candidate_scan_age_seconds == 0
    assert second.candidate_scan_cached is True
    assert second.candidate_scan_age_seconds == 4
    assert third.candidate_scan_cached is False
    assert third.candidate_scan_age_seconds == 0


def test_service_keeps_daily_candidate_scan_cached_while_strategy_refreshes() -> None:
    calls = 0

    def load_board(_as_of, _limit):
        nonlocal calls
        calls += 1
        return board()

    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates=load_board),
        SimpleNamespace(resolve=lambda symbol: None),
    )

    first = service.current(NOW)
    second = service.current(NOW + timedelta(seconds=6))

    assert calls == 1
    assert first.candidate_scan_cached is False
    assert second.candidate_scan_cached is True
    assert second.candidate_scan_at == NOW
    assert second.candidate_scan_age_seconds == 6


def test_service_can_defer_first_candidate_scan_without_blocking_request() -> None:
    started = False
    release = __import__("threading").Event()

    def load_board(_as_of, _limit):
        nonlocal started
        started = True
        release.wait(timeout=2)
        return board()

    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates=load_board),
        SimpleNamespace(resolve=lambda symbol: None),
        defer_initial_scan=True,
    )

    pending = service.current(NOW)

    assert started is True
    assert pending.candidate_scan_state == "pending"
    assert pending.candidates == ()
    assert "candidate_scan_pending" in pending.missing_data

    release.set()
    for _ in range(20):
        if service.candidate_scan_ready(NOW):
            break
        __import__("time").sleep(0.01)
    ready = service.current(NOW + timedelta(seconds=1))

    assert ready.candidate_scan_state == "ready"
    assert ready.candidates[0].symbol == "600001"
    service.close()


def test_deferred_scan_exposes_real_factor_progress_when_available() -> None:
    import threading

    started = threading.Event()
    release = threading.Event()

    def load_board_with_progress(_as_of, _limit, *, progress):
        progress("computing_factors", 25, 100)
        started.set()
        release.wait(timeout=2)
        progress("ranking", 100, 100)
        return board()

    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates_with_progress=load_board_with_progress),
        SimpleNamespace(resolve=lambda symbol: None),
        defer_initial_scan=True,
    )

    pending = service.current(NOW)
    assert pending.candidate_scan_state == "pending"
    assert started.wait(timeout=1)

    progress = service.current(NOW + timedelta(seconds=1))
    assert progress.candidate_scan_phase == "computing_factors"
    assert progress.candidate_scan_processed == 25
    assert progress.candidate_scan_total == 100

    release.set()
    for _ in range(20):
        if service.candidate_scan_ready(NOW):
            break
        __import__("time").sleep(0.01)
    service.close()


def test_deferred_scan_failure_is_safe_and_explicit() -> None:
    release = __import__("threading").Event()

    def load_board(_as_of, _limit):
        release.wait(timeout=2)
        raise RuntimeError("secret database path=C:/private/token")

    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates=load_board),
        SimpleNamespace(resolve=lambda symbol: None),
        defer_initial_scan=True,
    )

    service.current(NOW)
    release.set()
    for _ in range(20):
        if service.candidate_scan_ready(NOW):
            break
        __import__("time").sleep(0.01)
    failed = service.current(NOW + timedelta(seconds=1))

    assert failed.candidate_scan_state == "failed"
    assert failed.candidate_scan_error == "本地候选扫描失败，请检查日线覆盖和数据源状态"
    assert "secret database path" not in failed.candidate_scan_error
    service.close()


def test_service_reports_trigger_evidence_cache_age_separately() -> None:
    calls = 0

    class EvidenceSource:
        def get(self, _symbol, _trading_date, _cutoff, _stock):
            nonlocal calls
            calls += 1
            return TriggerEvidence(vwap_support=True, sources=("tick-archive",))

    service = QuantStrategyService(
        SimpleNamespace(current=lambda now: overview()),
        SimpleNamespace(candidates=lambda as_of, limit: board()),
        SimpleNamespace(resolve=lambda symbol: None),
        trigger_evidence_source=EvidenceSource(),
        cache_seconds=30,
        evidence_cache_seconds=5,
    )

    first = service.current(NOW)
    second = service.current(NOW + timedelta(seconds=4))
    third = service.current(NOW + timedelta(seconds=6))

    assert calls == 2
    assert first.trigger_evidence_cached is False
    assert first.trigger_evidence_at == NOW
    assert first.trigger_evidence_age_seconds == 0
    assert second.trigger_evidence_cached is True
    assert second.trigger_evidence_age_seconds == 4
    assert third.trigger_evidence_cached is False
    assert third.trigger_evidence_at == NOW + timedelta(seconds=6)
    assert third.trigger_evidence_age_seconds == 0
    assert third.candidate_scan_cached is True


def test_candidate_contract_rejects_missing_trigger_with_nonzero_score() -> None:
    with pytest.raises(ValidationError):
        QuantStrategyCandidate(
            symbol="600001", name="样本股份", model="0轴低吸模型",
            strategy_score=Decimal("80"), regime_match=Decimal("1"),
            stock_score=Decimal("0.9"), trigger_score=Decimal("0.4"),
            rr_score=Decimal("0"), risk_penalty=Decimal("1"),
            status="pending_trigger", trigger_confirmed=False,
            position=Decimal("0"), planned_position=Decimal("0"),
            evidence_coverage_percent=Decimal("80"), buy_triggers=("条件",),
            invalidation_rules=("失效",), missing_evidence=("three_minute_return",),
            factor_as_of=date(2026, 7, 31), sources=("tdx-local-daily",),
        )
