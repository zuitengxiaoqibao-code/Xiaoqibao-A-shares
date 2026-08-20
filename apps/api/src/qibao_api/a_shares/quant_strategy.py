from dataclasses import dataclass
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import logging
import hashlib
import json
import shutil
import subprocess
import tempfile
from time import perf_counter
from threading import RLock
from typing import Mapping
import os
from zoneinfo import ZoneInfo

from qibao_api.a_shares.models import CandidateBoard, CandidateEntry
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
from qibao_api.contracts.quant_strategy import (
    AlertGate,
    AlertGateCheck,
    CandidateFunnelStage,
    CandidateSelectionFunnel,
    QuantStrategyCandidate,
    QuantStrategyDashboard,
    QuantStrategyModel,
    QuantSignalVote,
)
from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from qibao_api.contracts.field_evidence import FieldEvidence
from qibao_api.a_shares.quant_strategy_snapshot import QuantStrategySnapshotStore
from qibao_api.a_shares.point_in_time import filter_as_of
from qibao_api.a_shares.quant_candidate_process import (
    scan_candidate_board_from_local_bars,
)


ZERO = Decimal()
ONE = Decimal("1")
TWO_PLACES = Decimal("0.01")
CHINA_TZ = ZoneInfo("Asia/Shanghai")
SAFE_CANDIDATE_SCAN_ERROR = "本地候选扫描失败，请检查日线覆盖和数据源状态"
SAFE_MARKET_OVERVIEW_ERROR = "市场总览加载失败，请检查本地行情和新闻数据源"
MINIMUM_SHARED_CANDIDATE_LIMIT = 12
LOGGER = logging.getLogger(__name__)

STRATEGY_MODEL_REGIMES = {
    "0轴低吸模型": ("情绪主升", "轮动震荡"),
    "恐慌低吸模型": ("冰点修复", "高位退潮"),
    "权重容量低吸模型": ("指数权重进攻",),
    "分歧转一致模型": ("情绪主升",),
    "反核修复模型": ("冰点修复",),
    "空仓防守模型": ("高位退潮", "缩量混沌"),
}

DISCIPLINE_BY_REGIME = {
    "情绪主升": "情绪主升：只做核心强股的分歧确认，不追后排和一致加速。",
    "指数权重进攻": "指数权重进攻：优先大成交容量核心，回踩均价确认后再观察。",
    "轮动震荡": "轮动震荡：只做前排低吸，开盘高于4%或下午临时冲高不参与。",
    "冰点修复": "冰点修复：只观察恐慌释放后的主动修复，跌停未打开不参与。",
    "高位退潮": "高位退潮：默认空仓防守，只卖不买；反核必须等待完整触发证据。",
    "缩量混沌": "缩量混沌：默认等待或极小仓试错，不追连板和高位加速。",
}

TRIGGERS_BY_REGIME = {
    "情绪主升": (
        "涨跌幅位于 -1.5% 至 +2%",
        "最新价不低于盘中均价",
        "3分钟涨幅转正",
        "大单与超大单合计净流入率大于0",
        "收盘位置持续抬升",
    ),
    "指数权重进攻": (
        "涨跌幅位于 0% 至 +3%",
        "回踩盘中均价不破",
        "量比不低于1.2",
        "当日资金净流入大于0",
    ),
    "轮动震荡": (
        "最终分和买入分均不低于80",
        "计划盈亏比不低于2.5",
        "开盘高开不超过4%",
        "只确认早盘第一次分歧",
    ),
    "冰点修复": (
        "最低涨幅不高于 -7%",
        "最新价脱离跌停价超过0.5%",
        "1分钟和3分钟涨幅同时转正",
        "委比改善且大单净流出收窄",
    ),
    "缩量混沌": (
        "仅作观察，不追连板和高位加速",
        "等待完整盘中触发证据",
        "市场系数不高于0.2",
    ),
}

INVALIDATIONS_BY_REGIME = {
    "情绪主升": ("跌破盘中均价且3分钟不能收回", "资金净流入转负"),
    "指数权重进攻": ("回踩均价后放量跌破", "权重板块强度同步转弱"),
    "轮动震荡": ("开盘涨幅超过4%", "触发分低于80或盈亏比低于2.5"),
    "冰点修复": ("跌停打开后再次回封", "修复幅度与大单流入同时转弱"),
    "缩量混沌": ("市场成交热度继续下行", "出现高位加速或追涨信号"),
}


@dataclass(frozen=True)
class TriggerEvidence:
    vwap_support: bool | None = None
    one_minute_return: Decimal | None = None
    three_minute_return: Decimal | None = None
    net_large_flow_positive: bool | None = None
    net_fund_flow_positive: bool | None = None
    close_position_rising: bool | None = None
    first_morning_divergence: bool | None = None
    limit_down_recovery: bool | None = None
    order_ratio_improving: bool | None = None
    large_outflow_narrowing: bool | None = None
    sources: tuple[str, ...] = ()


class ArchivedTriggerEvidenceSource:
    def __init__(self, poll_repository, fund_flow_repository) -> None:
        self.poll_repository = poll_repository
        self.fund_flow_repository = fund_flow_repository

    @staticmethod
    def _return_at(ticks, latest, minutes: int) -> Decimal | None:
        target = latest.observed_at - timedelta(minutes=minutes)
        prior = next(
            (item for item in reversed(ticks[:-1]) if item.observed_at <= target),
            None,
        )
        if prior is None or prior.price <= 0:
            return None
        return latest.price / prior.price - ONE

    @staticmethod
    def _sampled_vwap(ticks) -> Decimal | None:
        weighted = ZERO
        total_volume = ZERO
        previous_volume = ZERO
        for item in ticks:
            delta = max(item.volume - previous_volume, ZERO)
            weighted += item.price * delta
            total_volume += delta
            previous_volume = max(previous_volume, item.volume)
        return weighted / total_volume if total_volume > 0 else None

    def get(
        self,
        symbol: str,
        trading_date: date,
        cutoff: datetime,
        stock: OverviewFeatureStock | None,
    ) -> TriggerEvidence:
        ticks = filter_as_of(
            self.poll_repository.intraday_snapshots(
                symbol, trading_date, cutoff=cutoff,
            ),
            cutoff,
        )
        ticks = tuple(sorted(ticks, key=lambda item: item.observed_at))
        latest = ticks[-1] if ticks else None
        sampled_vwap = self._sampled_vwap(ticks)
        close_position_rising = None
        if latest is not None and stock is not None and len(ticks) >= 2:
            baseline = next(
                (
                    item for item in reversed(ticks[:-1])
                    if item.observed_at <= latest.observed_at - timedelta(minutes=3)
                ),
                None,
            )
            if baseline is not None:
                price_range = max(stock.high - stock.low, Decimal("0.01"))
                latest_position = (latest.price - stock.low) / price_range
                baseline_position = (baseline.price - stock.low) / price_range
                close_position_rising = latest_position > baseline_position
        flow = self.fund_flow_repository.latest(
            symbol, trading_date, cutoff=cutoff,
        )
        flow_is_current = flow is not None and flow.latest_trade_date == trading_date
        sources = tuple(dict.fromkeys((
            *((item.source for item in ticks) if ticks else ()),
            *((flow.source,) if flow_is_current else ()),
        )))
        return TriggerEvidence(
            vwap_support=(
                latest.price >= sampled_vwap
                if latest is not None and sampled_vwap is not None else None
            ),
            one_minute_return=(
                self._return_at(ticks, latest, 1) if latest is not None else None
            ),
            three_minute_return=(
                self._return_at(ticks, latest, 3) if latest is not None else None
            ),
            net_large_flow_positive=(
                flow.latest_large_net + flow.latest_super_net > 0
                if flow_is_current else None
            ),
            net_fund_flow_positive=(
                flow.intraday_main_net > 0
                if flow_is_current and flow.intraday_main_net is not None else None
            ),
            close_position_rising=close_position_rising,
            sources=sources,
        )


def _clamp(value: Decimal, low: Decimal = ZERO, high: Decimal = ONE) -> Decimal:
    return max(low, min(high, value))


def _q(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def _stock_score(entry: CandidateEntry) -> Decimal:
    return _clamp(entry.score / Decimal("90"))


def _rr_score(entry: CandidateEntry) -> Decimal:
    # A real RR score requires explicit entry, stop and target prices.
    # Historical return/volatility is not a valid substitute.
    return ZERO


def _base_evidence_coverage(
    overview: MarketOverviewResponse,
    board: CandidateBoard,
) -> Decimal:
    """Return the verified pre-trigger coverage for one candidate.

    The old implementation used a constant 70% floor, which made a sparse
    market/factor snapshot look more complete than its source data.  Use the
    real market-regime and factor watermarks instead; a missing watermark is
    not silently treated as zero when a candidate board already carries a
    factor snapshot, but it does lower coverage when an explicit value exists.
    """
    values = [overview.regime.coverage_percent]
    factor_coverage = overview.regime_metrics.factor_coverage_percent
    if factor_coverage > ZERO:
        values.append(factor_coverage)
    if board.universe_size > 0 and board.funnel.factor_ready_size > 0:
        values.append(
            Decimal(board.funnel.factor_ready_size)
            / Decimal(board.universe_size)
            * Decimal("100")
        )
    return _q(max(ZERO, min(values)))


def _risk_penalty(entry: CandidateEntry) -> Decimal:
    snapshot = entry.factor_snapshot
    volatility_points = snapshot.volatility_20d * Decimal("100")
    drawdown_points = abs(snapshot.drawdown_60d) * Decimal("20")
    return _q(_clamp(volatility_points + drawdown_points, high=Decimal("30")))


def _close_position(stock: OverviewFeatureStock) -> Decimal:
    price_range = max(stock.high - stock.low, Decimal("0.01"))
    return (stock.price - stock.low) / price_range * Decimal("100")


def _trigger_evidence(
    regime: str,
    stock: OverviewFeatureStock | None,
    entry: CandidateEntry,
    evidence: TriggerEvidence,
) -> tuple[Decimal, bool, tuple[str, ...], Decimal]:
    checks: list[tuple[bool | None, str]]
    if regime == "情绪主升":
        checks = [
            (
                Decimal("-1.5") <= stock.change_percent <= Decimal("2")
                if stock is not None else None,
                "realtime_quote",
            ),
            (evidence.vwap_support, "vwap_support"),
            (
                evidence.three_minute_return > 0
                if evidence.three_minute_return is not None else None,
                "three_minute_return",
            ),
            (evidence.net_large_flow_positive, "net_large_flow"),
            (evidence.close_position_rising, "close_position_rising"),
        ]
    elif regime == "指数权重进攻":
        checks = [
            (
                ZERO <= stock.change_percent <= Decimal("3")
                if stock is not None else None,
                "realtime_quote",
            ),
            (evidence.vwap_support, "vwap_support"),
            (entry.factor_snapshot.volume_ratio_5_20 >= Decimal("1.2"), "volume_ratio"),
            (evidence.net_fund_flow_positive, "net_fund_flow"),
        ]
    elif regime == "轮动震荡":
        open_gap = None
        if stock is not None:
            open_gap = (stock.open / stock.previous_close - ONE) * Decimal("100")
        checks = [
            (entry.score >= Decimal("80"), "candidate_score"),
            (None, "risk_reward_plan"),
            (open_gap <= Decimal("4") if open_gap is not None else None, "open_gap"),
            (evidence.first_morning_divergence, "first_morning_divergence"),
        ]
    elif regime == "冰点修复":
        low_return = (
            (stock.low / stock.previous_close - ONE) * Decimal("100")
            if stock is not None else None
        )
        checks = [
            (low_return <= Decimal("-7") if low_return is not None else None, "daily_low"),
            (evidence.limit_down_recovery, "limit_down_recovery"),
            (
                evidence.one_minute_return > 0
                if evidence.one_minute_return is not None else None,
                "one_minute_return",
            ),
            (
                evidence.three_minute_return > 0
                if evidence.three_minute_return is not None else None,
                "three_minute_return",
            ),
            (evidence.order_ratio_improving, "order_ratio"),
            (evidence.large_outflow_narrowing, "large_outflow_narrowing"),
        ]
    else:
        return ZERO, False, ("defensive_regime",), Decimal("20")
    missing = tuple(name for value, name in checks if value is None)
    passed = sum(value is True for value, _name in checks)
    total = len(checks)
    score = ZERO if missing else Decimal(passed) / Decimal(total)
    coverage = Decimal(total - len(missing)) / Decimal(total) * Decimal("100")
    return _q(score), not missing and passed == total, missing, _q(coverage)


def _select_model(
    regime: str,
    stock: OverviewFeatureStock | None,
    evidence: TriggerEvidence,
) -> str:
    if regime in {"高位退潮", "缩量混沌"}:
        return "空仓防守模型"
    if regime == "情绪主升":
        if (
            stock is not None
            and stock.change_percent <= 0
            and evidence.three_minute_return is not None
            and evidence.three_minute_return > 0
        ):
            return "分歧转一致模型"
        return "0轴低吸模型"
    if regime == "指数权重进攻":
        return "权重容量低吸模型"
    if regime == "轮动震荡":
        return "0轴低吸模型"
    if evidence.limit_down_recovery:
        return "反核修复模型"
    return "恐慌低吸模型"


def _build_candidate(
    entry: CandidateEntry,
    *,
    overview: MarketOverviewResponse,
    board: CandidateBoard,
    name: str,
    regime: str,
    market_coef: Decimal,
    stock: OverviewFeatureStock | None,
    evidence: TriggerEvidence,
) -> QuantStrategyCandidate:
    model = _select_model(regime, stock, evidence)
    regime_match = ONE
    stock_score = _stock_score(entry)
    rr_score = _rr_score(entry)
    risk_penalty = _risk_penalty(entry)
    trigger_score, confirmed, missing, trigger_coverage = _trigger_evidence(
        regime, stock, entry, evidence
    )
    raw_score = (
        regime_match * Decimal("40")
        + stock_score * Decimal("30")
        + trigger_score * Decimal("20")
        + rr_score * Decimal("10")
        - risk_penalty
    )
    score = _q(_clamp(raw_score, high=Decimal("100")))
    risk_flags = []
    if entry.factor_snapshot.volatility_20d >= Decimal("0.04"):
        risk_flags.append("高波动")
    if entry.factor_snapshot.drawdown_60d <= Decimal("-0.25"):
        risk_flags.append("近60日回撤较深")
    risk_flags.append("缺少明确止损/目标价，盈亏比分不计分")
    base_coverage = _base_evidence_coverage(overview, board)
    evidence_coverage = _q(
        base_coverage * Decimal("0.6")
        + trigger_coverage * Decimal("0.4")
    )
    hard_risk = any(flag in {"高波动", "近60日回撤较深"} for flag in risk_flags)
    gate_checks = (
        AlertGateCheck(
            key="regime_match", label="市场模型匹配", passed=regime_match >= ONE,
            detail=f"匹配度 {regime_match}",
        ),
        AlertGateCheck(
            key="strategy_score", label="策略分门槛", passed=score >= Decimal("80"),
            detail=f"{score} / 80",
        ),
        AlertGateCheck(
            key="trigger_confirmed", label="盘中触发确认", passed=confirmed,
            detail="已确认" if confirmed else "尚未确认",
        ),
        AlertGateCheck(
            key="risk_penalty", label="风险扣分", passed=risk_penalty <= Decimal("5"),
            detail=f"{risk_penalty} / 5",
        ),
        AlertGateCheck(
            key="evidence_coverage", label="证据覆盖", passed=evidence_coverage >= Decimal("90"),
            detail=f"{evidence_coverage}% / 90%",
        ),
        AlertGateCheck(
            key="hard_risk", label="硬风险拦截", passed=not hard_risk,
            detail="无高波动或深回撤" if not hard_risk else "存在高波动或深回撤",
        ),
    )
    blocker_by_key = {
        "regime_match": "市场风格与模型未匹配",
        "strategy_score": "策略分低于80",
        "trigger_confirmed": "盘中触发未确认",
        "risk_penalty": "风险扣分超过5",
        "evidence_coverage": "证据覆盖低于90%",
        "hard_risk": "存在高波动或深回撤硬风险",
    }
    alert_gate = AlertGate(
        eligible=all(check.passed for check in gate_checks),
        checks=gate_checks,
        blockers=tuple(blocker_by_key[check.key] for check in gate_checks if not check.passed),
    )
    if missing:
        status = "pending_trigger"
    elif not confirmed:
        status = "reject"
    elif alert_gate.eligible:
        status = "alert"
    elif score >= Decimal("70"):
        status = "watch"
    else:
        status = "reject"
    strategy_coef = ONE if regime in {"情绪主升", "指数权重进攻"} else Decimal("0.8")
    planned_position = _q(
        Decimal("0.2") * market_coef * strategy_coef * rr_score
    )
    vote_inputs = (
        ("市场风格", regime_match),
        ("个股质量", stock_score),
        ("盘中触发", trigger_score),
        ("盈亏比", rr_score),
        ("风险约束", ONE - risk_penalty / Decimal("30")),
    )
    signal_votes = tuple(
        QuantSignalVote(
            signal=label,
            vote=1 if value >= Decimal("0.7") else 0 if value >= Decimal("0.45") else -1,
            evidence_value=_q(_clamp(value)),
        )
        for label, value in vote_inputs
    )
    vote_consensus = _q(
        Decimal(sum(item.vote for item in signal_votes)) / Decimal(len(signal_votes))
    )
    vote_position = _q(planned_position * max(ZERO, vote_consensus))
    return QuantStrategyCandidate(
        symbol=entry.symbol,
        name=name,
        model=model,
        strategy_score=score,
        regime_match=regime_match,
        stock_score=_q(stock_score),
        trigger_score=trigger_score,
        rr_score=_q(rr_score),
        risk_penalty=risk_penalty,
        status=status,
        trigger_confirmed=confirmed,
        position=planned_position if confirmed else ZERO,
        planned_position=planned_position,
        reference_price=stock.price if stock is not None and stock.price > 0 else None,
        vote_consensus=vote_consensus,
        vote_position=vote_position if confirmed else ZERO,
        signal_votes=signal_votes,
        evidence_coverage_percent=evidence_coverage,
        buy_triggers=TRIGGERS_BY_REGIME[regime],
        invalidation_rules=INVALIDATIONS_BY_REGIME[regime],
        risk_flags=tuple(risk_flags),
        missing_evidence=missing,
        alert_gate=alert_gate,
        factor_as_of=entry.factor_snapshot.as_of,
        sources=tuple(dict.fromkeys((
            entry.factor_snapshot.source,
            *((stock.source,) if stock is not None else ()),
            *evidence.sources,
        ))),
    )


def _strategy_models(regime: str | None) -> tuple[QuantStrategyModel, ...]:
    return tuple(
        QuantStrategyModel(
            name=name,
            applicable_regimes=regimes,
            selected=regime in regimes if regime is not None else False,
            defensive=name == "空仓防守模型",
        )
        for name, regimes in STRATEGY_MODEL_REGIMES.items()
    )


def _refresh_metadata(
    overview: MarketOverviewResponse,
    generated_at: datetime,
) -> dict[str, object]:
    market_observed_at = overview.market_data.observed_at or overview.observed_at
    data_age_seconds = max(
        0,
        int((generated_at - market_observed_at).total_seconds()),
    )
    overview_freshness = getattr(overview.market_data, "freshness", "unknown")
    if overview_freshness in {"previous_close", "final"}:
        refresh_mode = "postclose"
        refresh_seconds = 30
    elif overview_freshness == "stale":
        refresh_mode = "stale"
        refresh_seconds = 30
    elif overview.as_of < generated_at.astimezone(CHINA_TZ).date():
        refresh_mode = "postclose"
        refresh_seconds = 30
    elif (
        data_age_seconds <= 30
        and overview.market_data.quality in {"ready", "partial"}
    ):
        refresh_mode = "live"
        refresh_seconds = 5
    elif (
        data_age_seconds <= 120
        and overview.market_data.quality != "unavailable"
    ):
        refresh_mode = "delayed"
        refresh_seconds = 5
    else:
        refresh_mode = "stale"
        refresh_seconds = 30
    return {
        "generated_at": generated_at,
        "market_observed_at": market_observed_at,
        "data_age_seconds": data_age_seconds,
        "refresh_mode": refresh_mode,
        "next_refresh_at": generated_at + timedelta(seconds=refresh_seconds),
    }


def build_quant_strategy_dashboard(
    overview: MarketOverviewResponse,
    board: CandidateBoard,
    *,
    names: Mapping[str, str] | None = None,
    trigger_evidence: Mapping[str, TriggerEvidence] | None = None,
    generated_at: datetime | None = None,
    candidate_scan_at: datetime | None = None,
    candidate_scan_cached: bool = False,
    trigger_evidence_at: datetime | None = None,
    trigger_evidence_cached: bool = False,
    candidate_scan_state: str = "ready",
    candidate_scan_started_at: datetime | None = None,
    candidate_scan_error: str | None = None,
    candidate_scan_phase: str = "ready",
    candidate_scan_processed: int | None = None,
    candidate_scan_total: int | None = None,
    extra_missing_data: tuple[str, ...] = (),
    limit: int = 12,
) -> QuantStrategyDashboard:
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")
    refresh_metadata = _refresh_metadata(
        overview,
        generated_at or overview.observed_at,
    )
    generated = generated_at or overview.observed_at
    candidate_scan_timestamp = candidate_scan_at or generated
    trigger_evidence_timestamp = trigger_evidence_at
    candidate_scan_age = max(
        0, int((generated - candidate_scan_timestamp).total_seconds())
    )
    trigger_evidence_age = (
        max(0, int((generated - trigger_evidence_timestamp).total_seconds()))
        if trigger_evidence_timestamp is not None else None
    )
    cache_metadata = {
        "candidate_scan_at": candidate_scan_timestamp,
        "candidate_scan_age_seconds": candidate_scan_age,
        "candidate_scan_cached": candidate_scan_cached,
        "candidate_scan_state": candidate_scan_state,
        "candidate_scan_started_at": candidate_scan_started_at,
        "candidate_scan_error": candidate_scan_error,
        "candidate_scan_phase": candidate_scan_phase,
        "candidate_scan_processed": candidate_scan_processed,
        "candidate_scan_total": candidate_scan_total,
        "trigger_evidence_at": trigger_evidence_timestamp,
        "trigger_evidence_age_seconds": trigger_evidence_age,
        "trigger_evidence_cached": trigger_evidence_cached,
    }
    regime = overview.regime.regime
    missing = tuple(dict.fromkeys((
        *overview.regime.missing_factors,
        *board.funnel.blockers,
        *(("candidate_history",) if not board.short_term else ()),
        *((f"candidate_scan_{candidate_scan_state}",)
          if candidate_scan_state != "ready" else ()),
        *extra_missing_data,
    )))
    base_funnel = _candidate_selection_funnel(board, (), missing)
    base_ledger = _strategy_evidence_ledger(overview, board, missing)
    input_snapshot_ids = _quant_input_snapshot_ids(overview)
    if regime is None:
        return QuantStrategyDashboard(
            status="unavailable",
            as_of=overview.as_of,
            observed_at=overview.observed_at,
            **refresh_metadata,
            **cache_metadata,
            metrics=overview.regime_metrics,
            regime=overview.regime,
            strategy_models=_strategy_models(regime),
            candidate_funnel=base_funnel,
            evidence_ledger=base_ledger,
            input_snapshot_ids=input_snapshot_ids,
            candidates=(),
            discipline="市场风格尚未形成，等待真实横截面指标后再选择策略。",
            missing_data=missing or ("market_regime",),
            warnings=overview.warnings,
            sources=overview.sources,
        )
    if regime == "高位退潮":
        return QuantStrategyDashboard(
            status="partial",
            as_of=overview.as_of,
            observed_at=overview.observed_at,
            **refresh_metadata,
            **cache_metadata,
            metrics=overview.regime_metrics,
            regime=overview.regime,
            strategy_models=_strategy_models(regime),
            candidate_funnel=base_funnel,
            evidence_ledger=base_ledger,
            input_snapshot_ids=input_snapshot_ids,
            candidates=(),
            discipline=DISCIPLINE_BY_REGIME[regime],
            missing_data=missing,
            warnings=overview.warnings,
            sources=tuple(dict.fromkeys((*overview.sources, *board.sources))),
        )
    name_map = names or {}
    evidence_map = trigger_evidence or {}
    stocks = {item.symbol: item for item in overview.market_stocks}
    candidates = tuple(
        _build_candidate(
            entry,
            overview=overview,
            board=board,
            name=name_map.get(entry.symbol, entry.symbol),
            regime=regime,
            market_coef=overview.regime.market_coef,
            stock=stocks.get(entry.symbol),
            evidence=evidence_map.get(entry.symbol, TriggerEvidence()),
        )
        for entry in board.short_term[:limit]
    )
    candidates = tuple(sorted(
        candidates, key=lambda item: (-item.strategy_score, item.symbol)
    ))
    candidate_funnel = _candidate_selection_funnel(board, candidates, missing)
    evidence_ledger = _strategy_evidence_ledger(overview, board, missing)
    field_evidence = _strategy_field_evidence(overview, candidates, generated)
    status = "ready" if overview.status == "ready" and not missing else "partial"
    return QuantStrategyDashboard(
        status=status,
        as_of=overview.as_of,
        observed_at=overview.observed_at,
        **refresh_metadata,
        **cache_metadata,
        metrics=overview.regime_metrics,
        regime=overview.regime,
        strategy_models=_strategy_models(regime),
        candidate_funnel=candidate_funnel,
        evidence_ledger=evidence_ledger,
        field_evidence=field_evidence,
        input_snapshot_ids=input_snapshot_ids,
        candidates=candidates,
        discipline=DISCIPLINE_BY_REGIME[regime],
        missing_data=missing,
        warnings=overview.warnings,
        sources=tuple(dict.fromkeys((*overview.sources, *board.sources))),
    )


def _quant_input_snapshot_ids(overview: MarketOverviewResponse) -> tuple[str, ...]:
    """Return only real immutable source snapshot IDs used by the overview.

    Evidence IDs are the canonical provenance boundary.  The operation name
    (for example ``quant_strategy_v2``) describes a computation and must never
    be presented as a data snapshot.
    """
    return tuple(dict.fromkeys(
        evidence_id
        for field in overview.field_evidence
        for evidence_id in field.evidence_ids
        if evidence_id.strip()
    ))


def _strategy_field_evidence(
    overview: MarketOverviewResponse,
    candidates: tuple[QuantStrategyCandidate, ...],
    observed_at: datetime,
) -> tuple[FieldEvidence, ...]:
    sources = " / ".join(overview.sources) or "unavailable"
    limitations = tuple(overview.regime.missing_factors)
    entries = [
        FieldEvidence(
            field_path=f"regime.{name}", value=value,
            source=sources if value is not None else "unavailable", source_field=None,
            status="derived" if value is not None else "missing", trade_date=overview.as_of,
            observed_at=observed_at if value is not None else None,
            coverage_percent=overview.regime.coverage_percent if value is not None else None,
            derived=value is not None,
            formula=overview.regime.formula_version if value is not None else None,
            limitations=limitations if value is not None and limitations else (("market_regime_unavailable",) if value is None else ()),
        )
        for name, value in (
            ("emotion_score", overview.regime.emotion_score),
            ("risk_score", overview.regime.risk_score),
            ("previous_risk_score", overview.regime.previous_risk_score),
            ("heat_score", overview.regime.heat_score),
            ("rotation_score", overview.regime.rotation_score),
        )
    ]
    for candidate in candidates:
        entries.append(FieldEvidence(
            field_path=f"candidates.{candidate.symbol}.strategy_score",
            value=candidate.strategy_score,
            source=" / ".join(candidate.sources) or sources,
            source_field=None,
            status="derived",
            trade_date=candidate.factor_as_of,
            observed_at=observed_at,
            coverage_percent=candidate.evidence_coverage_percent,
            derived=True,
            formula="a-share-short-strategy-v2.0",
            limitations=tuple(candidate.missing_evidence),
        ))
    return tuple(entries)


def _candidate_selection_funnel(
    board: CandidateBoard,
    candidates: tuple[QuantStrategyCandidate, ...],
    missing: tuple[str, ...],
) -> CandidateSelectionFunnel:
    """Translate the scan's real counts into the dashboard funnel contract."""
    scan = board.funnel
    trigger_confirmed = sum(item.trigger_confirmed for item in candidates)
    final_candidates = sum(item.status in {"alert", "watch"} for item in candidates)
    exclusions = dict(scan.exclusion_reasons)
    not_confirmed = sum(not item.trigger_confirmed for item in candidates)
    risk_flagged = sum(bool(item.risk_flags) for item in candidates)
    if not_confirmed:
        exclusions["trigger_not_confirmed"] = not_confirmed
    if risk_flagged:
        exclusions["risk_flags"] = risk_flagged
    blockers = list(scan.blockers)
    if missing and "candidate_scan_pending" in missing:
        blockers.append("candidate_scan_pending")
    if missing and "trigger_evidence_pending" in missing:
        blockers.append("trigger_evidence_pending")
    return CandidateSelectionFunnel(
        stages=(
            CandidateFunnelStage(key="universe", label="全市场股票", count=board.universe_size),
            CandidateFunnelStage(key="history_ready", label="日线历史完整", count=scan.history_ready_size),
            CandidateFunnelStage(key="factor_ready", label="因子计算完成", count=scan.factor_ready_size),
            CandidateFunnelStage(key="liquidity_ready", label="流动性达标", count=scan.liquidity_ready_size),
            CandidateFunnelStage(key="ranked", label="策略排名入选", count=scan.ranked_size),
            CandidateFunnelStage(key="trigger_confirmed", label="盘中触发确认", count=trigger_confirmed),
            CandidateFunnelStage(key="final_candidates", label="最终候选", count=final_candidates),
        ),
        exclusion_reasons=exclusions,
        completeness=scan.completeness,
        blockers=tuple(dict.fromkeys(blockers)),
    )


def _strategy_evidence_ledger(
    overview: MarketOverviewResponse,
    board: CandidateBoard,
    missing: tuple[str, ...],
) -> tuple[EvidenceLedgerEntry, ...]:
    limitations = tuple(dict.fromkeys((*missing, *board.funnel.blockers)))
    status = (
        "ready" if overview.status == "ready" and not limitations
        else "partial" if overview.status != "unavailable" or board.funnel.completeness == "partial"
        else "unavailable"
    )
    return (EvidenceLedgerEntry(
        source=" / ".join(dict.fromkeys((*overview.sources, *board.sources))) or "unavailable",
        operation="quant_strategy_v2",
        status=status,
        trade_date=board.latest_trade_date or overview.as_of,
        observed_at=overview.observed_at,
        formula_version="a-share-short-strategy-v2.0",
        sample_count=board.universe_size if board.universe_size > 0 else None,
        total_count=board.universe_size if board.universe_size > 0 else None,
        coverage_percent=(
            float(board.funnel.factor_ready_size / board.universe_size * 100)
            if board.universe_size > 0 else None
        ),
        limitations=limitations,
    ),)


def _unavailable_market_overview(now: datetime, warning: str) -> MarketOverviewResponse:
    """Return an honest shell while the real overview is being fetched in a worker."""
    local_now = now.astimezone(CHINA_TZ)
    phase = (
        "premarket" if local_now.hour < 9 or (local_now.hour == 9 and local_now.minute < 25)
        else "intraday" if local_now.hour < 15
        else "postclose"
    )
    return MarketOverviewResponse(
        status="unavailable",
        as_of=local_now.date(),
        observed_at=now,
        sentiment=OverviewSentiment(
            score=None, band="unavailable", coverage_percent=Decimal("0"),
            quality="unavailable", observed_at=now,
        ),
        breadth=OverviewBreadth(
            rising_count=0, falling_count=0, flat_count=0, valid_count=0,
        ),
        limit_ecology=OverviewLimitEcology(
            limit_up_count=0, limit_down_count=0, broken_limit_up_count=0,
        ),
        liquidity=OverviewLiquidity(),
        regime_metrics=OverviewRegimeMetrics(),
        regime=OverviewRegimeAssessment(),
        market_data=OverviewMarketDataStatus(
            source="unavailable", quality="unavailable", phase=phase,
            freshness="unavailable",
        ),
        warnings=(warning,),
        sources=(),
    )


class QuantStrategyService:
    def __init__(
        self,
        overview_service,
        candidate_service,
        instrument_directory,
        trigger_evidence_source=None,
        cache_seconds: int = 30,
        evidence_cache_seconds: int = 5,
        defer_initial_scan: bool = False,
        defer_initial_overview: bool = False,
        defer_trigger_evidence: bool = False,
        snapshot_store: QuantStrategySnapshotStore | None = None,
        shadow_ledger=None,
        shared_snapshot_registry=None,
        realtime_snapshot_bus=None,
    ) -> None:
        self.overview_service = overview_service
        self.candidate_service = candidate_service
        self.instrument_directory = instrument_directory
        self.trigger_evidence_source = trigger_evidence_source
        self.cache_ttl = timedelta(seconds=max(0, cache_seconds))
        self.evidence_cache_ttl = timedelta(seconds=max(0, evidence_cache_seconds))
        self.defer_initial_scan = defer_initial_scan
        self.defer_initial_overview = defer_initial_overview
        self.defer_trigger_evidence = defer_trigger_evidence
        self.snapshot_store = snapshot_store
        self.shadow_ledger = shadow_ledger
        self.shared_snapshot_registry = shared_snapshot_registry
        self.realtime_snapshot_bus = realtime_snapshot_bus
        self._candidate_cache: dict[
            tuple[date, int],
            tuple[datetime, datetime, CandidateBoard, dict[str, str]],
        ] = {}
        self._evidence_cache: dict[
            tuple[date, int], tuple[datetime, datetime, dict[str, TriggerEvidence]]
        ] = {}
        self._candidate_cache_lock = RLock()
        self._candidate_scan_executor = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="quant-candidate-scan")
            if defer_initial_scan else None
        )
        bar_repository = getattr(candidate_service, "bar_repository", None)
        database_path = getattr(bar_repository, "database_path", None)
        parquet_dir = getattr(bar_repository, "parquet_dir", None)
        self._candidate_process_paths = (
            (str(database_path), str(parquet_dir))
            if defer_initial_scan and database_path is not None and parquet_dir is not None
            else None
        )
        self._candidate_process_alias: Path | None = None
        self._candidate_process_paths = self._prepare_process_paths(
            self._candidate_process_paths
        )
        self._candidate_process_executor = (
            ProcessPoolExecutor(max_workers=1)
            if self._candidate_process_paths is not None else None
        )
        self._candidate_scan_jobs: dict[tuple[date, int], Future] = {}
        self._candidate_scan_started: dict[tuple[date, int], datetime] = {}
        self._candidate_scan_errors: dict[tuple[date, int], str] = {}
        self._candidate_fallback_snapshots: dict[
            tuple[date, int], QuantStrategyDashboard
        ] = {}
        self._candidate_scan_progress: dict[
            tuple[date, int], tuple[str, int | None, int | None]
        ] = {}
        self._overview_lock = RLock()
        self._overview_executor = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="quant-market-overview")
            if defer_initial_overview else None
        )
        self._overview_future: Future | None = None
        self._overview_started_at: datetime | None = None
        self._overview_error: str | None = None
        self._overview_snapshot: MarketOverviewResponse | None = None
        self._evidence_executor = (
            ThreadPoolExecutor(max_workers=1, thread_name_prefix="quant-trigger-evidence")
            if defer_trigger_evidence else None
        )
        self._evidence_jobs: dict[tuple[date, int], Future] = {}
        self._evidence_started: dict[tuple[date, int], datetime] = {}
        self._evidence_errors: dict[tuple[date, int], str] = {}

    def close(self) -> None:
        executor = self._candidate_scan_executor
        self._candidate_scan_executor = None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
        process_executor = self._candidate_process_executor
        self._candidate_process_executor = None
        if process_executor is not None:
            process_executor.shutdown(wait=True, cancel_futures=True)
        if self._candidate_process_alias is not None:
            shutil.rmtree(self._candidate_process_alias, ignore_errors=True)
            self._candidate_process_alias = None
        for lock, future_attr, executor_attr in (
            (self._overview_lock, "_overview_future", "_overview_executor"),
        ):
            with lock:
                future = getattr(self, future_attr)
                setattr(self, future_attr, None)
                background_executor = getattr(self, executor_attr)
                setattr(self, executor_attr, None)
            if future is not None:
                future.cancel()
            if background_executor is not None:
                background_executor.shutdown(wait=False, cancel_futures=True)
        evidence_executor = self._evidence_executor
        self._evidence_executor = None
        if evidence_executor is not None:
            with self._candidate_cache_lock:
                for job in self._evidence_jobs.values():
                    job.cancel()
                self._evidence_jobs.clear()
            evidence_executor.shutdown(wait=False, cancel_futures=True)

    def _prepare_process_paths(
        self, paths: tuple[str, str] | None
    ) -> tuple[str, str] | None:
        if paths is None:
            return None
        if all(str(path).isascii() for path in paths):
            return paths
        # DuckDB's frozen Windows child runtime can fail decoding a Chinese
        # path before opening the database.  A temporary ASCII junction keeps
        # the same real files while preserving process isolation and speed.
        temp_root = Path(tempfile.gettempdir())
        if not str(temp_root).isascii():
            return None
        database = Path(paths[0])
        parquet = Path(paths[1])
        alias = temp_root / f"qibao-data-{os.getpid()}-{id(self):x}"
        try:
            alias.parent.mkdir(parents=True, exist_ok=True)
            target = database.parent
            result = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(alias), str(target)],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                subprocess.run(["cmd.exe", "/d", "/c", "rmdir", str(alias)], check=False)
                return None
            self._candidate_process_alias = alias
            return (
                str(alias / database.name),
                str(alias / parquet.relative_to(target)),
            )
        except (OSError, ValueError):
            subprocess.run(["cmd.exe", "/d", "/c", "rmdir", str(alias)], check=False)
            return None

    def market_overview_ready(self) -> bool:
        with self._overview_lock:
            return self._overview_future is not None and self._overview_future.done()

    def _start_deferred_overview(self, now: datetime) -> None:
        if self._overview_executor is None:
            return
        with self._overview_lock:
            if self._overview_future is not None:
                return
            self._overview_started_at = now
            self._overview_error = None
            self._overview_future = self._overview_executor.submit(
                self.overview_service.current, now
            )

    def _consume_deferred_overview(self, now: datetime) -> tuple[MarketOverviewResponse, bool]:
        with self._overview_lock:
            future = self._overview_future
            snapshot = self._overview_snapshot
        if future is None:
            if snapshot is not None:
                return snapshot, False
            return _unavailable_market_overview(now, "market_overview_pending"), True
        if not future.done():
            if snapshot is not None:
                return snapshot, True
            return _unavailable_market_overview(now, "market_overview_pending"), True
        try:
            result = future.result()
        except Exception:
            with self._overview_lock:
                self._overview_error = SAFE_MARKET_OVERVIEW_ERROR
                self._overview_future = None
                snapshot = self._overview_snapshot
            if snapshot is not None:
                return snapshot, True
            return _unavailable_market_overview(now, SAFE_MARKET_OVERVIEW_ERROR), False
        with self._overview_lock:
            self._overview_future = None
            self._overview_error = None
            self._overview_snapshot = result
        return result, False

    def candidate_scan_ready(
        self, now: datetime, *, as_of: date | None = None, limit: int = 12
    ) -> bool:
        """检查后台候选扫描是否结束，不在调用线程执行扫描。"""
        key = self._candidate_cache_key(
            as_of or now.astimezone(CHINA_TZ).date(), limit
        )
        with self._candidate_cache_lock:
            job = self._candidate_scan_jobs.get(key)
        return job is not None and job.done()

    @staticmethod
    def _candidate_cache_key(selected_date: date, limit: int) -> tuple[date, int]:
        return selected_date, max(MINIMUM_SHARED_CANDIDATE_LIMIT, limit)

    def _record_candidate_progress(
        self,
        cache_key: tuple[date, int],
        phase: str,
        processed: int | None,
        total: int | None,
    ) -> None:
        with self._candidate_cache_lock:
            self._candidate_scan_progress[cache_key] = (phase, processed, total)

    def _scan_candidates(self, cache_key: tuple[date, int], selected_date: date, limit: int):
        scan_started = perf_counter()
        def progress(phase, processed=None, total=None):
            self._record_candidate_progress(cache_key, phase, processed, total)
        progress("loading_history")
        progress_loader = getattr(self.candidate_service, "candidates_with_progress", None)
        if self._candidate_process_paths is not None and self._candidate_process_executor is not None:
            factor_as_of = selected_date
            candidate_as_of = getattr(self.candidate_service, "_candidate_as_of", None)
            if callable(candidate_as_of):
                factor_as_of = candidate_as_of(selected_date, None)
            LOGGER.info(
                "quant candidate scan input factor_as_of=%s database=%s parquet=%s",
                factor_as_of,
                self._candidate_process_paths[0],
                self._candidate_process_paths[1],
            )
            progress("computing_factors", 0, None)
            process_future = self._candidate_process_executor.submit(
                scan_candidate_board_from_local_bars,
                *self._candidate_process_paths,
                factor_as_of,
                limit,
            )
            board = process_future.result()
            progress("computing_factors", board.universe_size, board.universe_size)
        elif callable(progress_loader):
            board = progress_loader(selected_date, limit, progress=progress)
        else:
            board = self.candidate_service.candidates(selected_date, limit)
        progress("ranking")
        names = {}
        for item in board.short_term:
            instrument = self.instrument_directory.resolve(item.symbol)
            if instrument is not None:
                names[item.symbol] = instrument.name
        with self._candidate_cache_lock:
            _phase, processed, total = self._candidate_scan_progress.get(
                cache_key, ("ready", None, None)
            )
        progress("ready", processed, total)
        LOGGER.warning(
            "quant candidate scan finished elapsed_ms=%s processed=%s total=%s",
            round((perf_counter() - scan_started) * 1000),
            processed,
            total,
        )
        return board, names

    def _start_deferred_scan(
        self, cache_key: tuple[date, int], selected_date: date, limit: int, now: datetime
    ) -> None:
        if self._candidate_scan_executor is None:
            return
        with self._candidate_cache_lock:
            existing = self._candidate_scan_jobs.get(cache_key)
            if existing is not None:
                return
            self._candidate_scan_errors.pop(cache_key, None)
            self._candidate_fallback_snapshots.pop(cache_key, None)
            self._candidate_scan_progress[cache_key] = ("loading_history", None, None)
            self._candidate_scan_started[cache_key] = now
            self._candidate_scan_jobs[cache_key] = self._candidate_scan_executor.submit(
                self._scan_candidates, cache_key, selected_date, limit
            )

    def _consume_deferred_scan(self, cache_key: tuple[date, int], now: datetime):
        with self._candidate_cache_lock:
            job = self._candidate_scan_jobs.get(cache_key)
            started = self._candidate_scan_started.get(cache_key, now)
        if job is None or not job.done():
            return None, None, "pending", started, None
        try:
            board, names = job.result()
        except Exception:
            message = SAFE_CANDIDATE_SCAN_ERROR
            with self._candidate_cache_lock:
                self._candidate_scan_errors[cache_key] = message
                self._candidate_scan_progress[cache_key] = ("failed", None, None)
                self._candidate_scan_jobs.pop(cache_key, None)
                self._candidate_scan_started.pop(cache_key, None)
            return None, None, "failed", started, message
        with self._candidate_cache_lock:
            _phase, processed, total = self._candidate_scan_progress.get(
                cache_key, ("ready", None, None)
            )
            self._candidate_scan_progress[cache_key] = ("ready", processed, total)
            self._candidate_cache[cache_key] = (
                now + self.cache_ttl, now, board, names
            )
            self._candidate_scan_jobs.pop(cache_key, None)
            self._candidate_scan_started.pop(cache_key, None)
            self._candidate_scan_errors.pop(cache_key, None)
            self._evidence_cache.pop(cache_key, None)
        return board, names, "ready", now, None

    def trigger_evidence_ready(
        self, now: datetime, *, as_of: date | None = None, limit: int = 12
    ) -> bool:
        key = self._candidate_cache_key(
            as_of or now.astimezone(CHINA_TZ).date(), limit
        )
        with self._candidate_cache_lock:
            job = self._evidence_jobs.get(key)
        return job is not None and job.done()

    def _load_trigger_evidence(
        self, cache_key: tuple[date, int], selected_date: date, now: datetime,
        symbols: tuple[str, ...], stocks: Mapping[str, OverviewFeatureStock],
    ) -> dict[str, TriggerEvidence]:
        return {
            symbol: self.trigger_evidence_source.get(
                symbol, selected_date, now, stocks.get(symbol)
            )
            for symbol in symbols
        }

    def _start_deferred_trigger_evidence(
        self, cache_key: tuple[date, int], selected_date: date, now: datetime,
        board: CandidateBoard, stocks: Mapping[str, OverviewFeatureStock],
    ) -> None:
        if self._evidence_executor is None or self.trigger_evidence_source is None:
            return
        with self._candidate_cache_lock:
            if cache_key in self._evidence_jobs:
                return
            self._evidence_started[cache_key] = now
            self._evidence_errors.pop(cache_key, None)
            self._evidence_jobs[cache_key] = self._evidence_executor.submit(
                self._load_trigger_evidence,
                cache_key, selected_date, now,
                tuple(item.symbol for item in board.short_term), stocks,
            )

    def _consume_deferred_trigger_evidence(
        self, cache_key: tuple[date, int], now: datetime,
    ) -> tuple[dict[str, TriggerEvidence], datetime | None, bool, str | None]:
        with self._candidate_cache_lock:
            job = self._evidence_jobs.get(cache_key)
        if job is None or not job.done():
            return {}, None, False, None
        try:
            evidence = job.result()
        except Exception:
            with self._candidate_cache_lock:
                self._evidence_errors[cache_key] = "trigger_evidence_failed"
                self._evidence_jobs.pop(cache_key, None)
                self._evidence_started.pop(cache_key, None)
            return {}, None, False, "trigger_evidence_failed"
        with self._candidate_cache_lock:
            self._evidence_jobs.pop(cache_key, None)
            self._evidence_started.pop(cache_key, None)
            self._evidence_cache[cache_key] = (
                now + self.evidence_cache_ttl, now, evidence
            )
        return evidence, now, False, None

    def current(
        self, now: datetime, *, as_of: date | None = None, limit: int = 12
    ) -> QuantStrategyDashboard:
        started_at = perf_counter()
        stage_times: dict[str, int] = {}

        def mark(stage: str) -> None:
            stage_times[stage] = round((perf_counter() - started_at) * 1000)

        def finish(result: QuantStrategyDashboard) -> QuantStrategyDashboard:
            elapsed_ms = round((perf_counter() - started_at) * 1000)
            self._record_shared_snapshot(result, latency_ms=elapsed_ms)
            if elapsed_ms >= 1000:
                LOGGER.warning(
                    "quant strategy request slow elapsed_ms=%s stages=%s "
                    "refresh_state=%s candidate_scan_state=%s",
                    elapsed_ms,
                    stage_times,
                    result.refresh_state,
                    result.candidate_scan_state,
                )
            return result

        overview_pending = False
        if self.defer_initial_overview:
            self._start_deferred_overview(now)
            overview, overview_pending = self._consume_deferred_overview(now)
        else:
            overview = self.overview_service.current(now)
        mark("overview")
        selected_date = as_of or overview.as_of
        if selected_date != overview.as_of:
            raise ValueError(
                "historical market regime is unavailable for the requested date"
            )
        persisted = None
        if self.snapshot_store is not None:
            persisted = self.snapshot_store.load(
                trading_date=selected_date,
                formula_version="a-share-short-strategy-v2.0",
            )
        mark("snapshot_load")
        if overview_pending and persisted is not None:
            pending_missing = tuple(dict.fromkeys((
                *persisted.missing_data,
                "market_overview_pending",
                "candidate_scan_pending",
            )))
            return finish(persisted.model_copy(update={
                "refresh_state": "pending",
                "snapshot_at": persisted.snapshot_at or persisted.generated_at,
                "refresh_started_at": now,
                "candidate_scan_state": "pending",
                "candidate_scan_started_at": now,
                "candidate_scan_phase": "loading_overview",
                "candidate_scan_error": None,
                "snapshot_source": "disk",
                "missing_data": pending_missing,
            }))
        cache_key = self._candidate_cache_key(selected_date, limit)
        scan_limit = cache_key[1]
        cached = None
        stale_cached = None
        candidate_scan_cached = False
        candidate_scan_at = now
        candidate_scan_state = "ready"
        candidate_scan_started_at = now
        candidate_scan_error = None
        candidate_scan_phase = "ready"
        candidate_scan_processed: int | None = None
        candidate_scan_total: int | None = None
        if self.cache_ttl > timedelta(0):
            with self._candidate_cache_lock:
                cached = self._candidate_cache.get(cache_key)
                if cached is not None and now >= cached[0]:
                    if self.defer_initial_scan:
                        stale_cached = cached
                    else:
                        self._candidate_cache.pop(cache_key, None)
                    cached = None
        fallback_snapshot = None
        with self._candidate_cache_lock:
            if cached is not None:
                fallback_snapshot = self._candidate_fallback_snapshots.get(cache_key)
        if fallback_snapshot is not None:
            return finish(fallback_snapshot.model_copy(update={
                "refresh_started_at": now,
                "refresh_finished_at": None,
                "snapshot_source": "disk",
                "candidate_scan_cached": True,
            }))
        if cached is None:
            if self.defer_initial_scan:
                self._start_deferred_scan(
                    cache_key, selected_date, scan_limit, now
                )
                (
                    board, names, candidate_scan_state,
                    candidate_scan_started_at, candidate_scan_error,
                ) = self._consume_deferred_scan(cache_key, now)
                mark("candidate_scan")
                with self._candidate_cache_lock:
                    (
                        candidate_scan_phase,
                        candidate_scan_processed,
                        candidate_scan_total,
                    ) = self._candidate_scan_progress.get(
                        cache_key, ("loading_history", None, None)
                    )
                if board is None:
                    if persisted is not None and candidate_scan_state in {"pending", "failed"}:
                        refresh_missing = list(persisted.missing_data)
                        refresh_missing.append(
                            f"candidate_scan_{candidate_scan_state}"
                        )
                        if overview_pending:
                            refresh_missing.append("market_overview_pending")
                        return finish(persisted.model_copy(update={
                            "refresh_state": (
                                "failed" if candidate_scan_state == "failed" else "pending"
                            ),
                            "snapshot_at": persisted.snapshot_at or persisted.generated_at,
                            "refresh_started_at": now,
                            "refresh_finished_at": None,
                            "snapshot_source": "disk",
                            "candidate_scan_at": persisted.candidate_scan_at or persisted.generated_at,
                            "candidate_scan_cached": True,
                            "candidate_scan_state": candidate_scan_state,
                            "candidate_scan_started_at": candidate_scan_started_at,
                            "candidate_scan_error": candidate_scan_error,
                            "candidate_scan_phase": candidate_scan_phase,
                            "candidate_scan_processed": candidate_scan_processed,
                            "candidate_scan_total": candidate_scan_total,
                            "missing_data": tuple(dict.fromkeys(refresh_missing)),
                        }))
                    if stale_cached is not None:
                        _expires_at, candidate_scan_at, board, names = stale_cached
                        candidate_scan_cached = True
                    else:
                        board = CandidateBoard(
                            as_of=selected_date,
                            universe_size=0,
                            eligible_size=0,
                            sources=(),
                            short_term=[],
                            swing=[],
                        )
                        names = {}
                elif (
                    persisted is not None
                    and candidate_scan_state == "ready"
                    and not board.short_term
                    and board.latest_trade_date is None
                ):
                    # A completed scan with no latest bar is an evidence
                    # failure, not a confirmed empty candidate pool. This is
                    # common when a fragmented trading day only contains a
                    # few partial symbols. Keep the last same-day snapshot
                    # visible and mark the refresh as failed until a scan
                    # with a confirmed factor date succeeds.
                    refresh_missing = list(persisted.missing_data)
                    refresh_missing.append("candidate_scan_insufficient_history")
                    failed_snapshot = persisted.model_copy(update={
                        "refresh_state": "failed",
                        "snapshot_at": persisted.snapshot_at or persisted.generated_at,
                        "refresh_started_at": now,
                        "refresh_finished_at": None,
                        "snapshot_source": "disk",
                        "candidate_scan_at": persisted.candidate_scan_at or persisted.generated_at,
                        "candidate_scan_cached": True,
                        "candidate_scan_state": "failed",
                        "candidate_scan_started_at": candidate_scan_started_at,
                        "candidate_scan_error": SAFE_CANDIDATE_SCAN_ERROR,
                        "candidate_scan_phase": "failed",
                        "candidate_scan_processed": board.universe_size,
                        "candidate_scan_total": board.universe_size,
                        "missing_data": tuple(dict.fromkeys(refresh_missing)),
                    })
                    with self._candidate_cache_lock:
                        self._candidate_cache[cache_key] = (
                            now + self.cache_ttl, now, board, names
                        )
                        self._candidate_fallback_snapshots[cache_key] = failed_snapshot
                        self._candidate_scan_progress[cache_key] = (
                            "failed", board.universe_size, board.universe_size
                        )
                        self._candidate_scan_errors[cache_key] = (
                            SAFE_CANDIDATE_SCAN_ERROR
                        )
                    return finish(failed_snapshot)
            else:
                board, names = self._scan_candidates(
                    cache_key, selected_date, scan_limit
                )
                mark("candidate_scan")
                if self.cache_ttl > timedelta(0):
                    with self._candidate_cache_lock:
                        self._candidate_cache[cache_key] = (
                            now + self.cache_ttl,
                            now,
                            board,
                            names,
                        )
                        self._evidence_cache.pop(cache_key, None)
        else:
            _expires_at, candidate_scan_at, board, names = cached
            candidate_scan_cached = True
            candidate_scan_state = "ready"
            candidate_scan_started_at = candidate_scan_at
            with self._candidate_cache_lock:
                (
                    candidate_scan_phase,
                    candidate_scan_processed,
                    candidate_scan_total,
                ) = self._candidate_scan_progress.get(cache_key, ("ready", None, None))
        evidence: dict[str, TriggerEvidence] = {}
        trigger_evidence_cached = False
        trigger_evidence_at: datetime | None = None
        extra_missing_data: list[str] = []
        if overview_pending:
            extra_missing_data.append("market_overview_pending")
        if self.trigger_evidence_source is not None:
            evidence_cached = None
            if self.evidence_cache_ttl > timedelta(0):
                with self._candidate_cache_lock:
                    evidence_cached = self._evidence_cache.get(cache_key)
                    if evidence_cached is not None and now >= evidence_cached[0]:
                        self._evidence_cache.pop(cache_key, None)
                        evidence_cached = None
            if evidence_cached is not None:
                _evidence_expires_at, trigger_evidence_at, evidence = evidence_cached
                trigger_evidence_cached = True
            elif self.defer_trigger_evidence:
                stocks = {item.symbol: item for item in overview.market_stocks}
                self._start_deferred_trigger_evidence(
                    cache_key, selected_date, now, board, stocks
                )
                evidence, trigger_evidence_at, trigger_evidence_cached, evidence_error = (
                    self._consume_deferred_trigger_evidence(cache_key, now)
                )
                if evidence_error:
                    extra_missing_data.append(evidence_error)
                elif trigger_evidence_at is None and board.short_term:
                    extra_missing_data.append("trigger_evidence_pending")
            else:
                stocks = {item.symbol: item for item in overview.market_stocks}
                for item in board.short_term:
                    evidence[item.symbol] = self.trigger_evidence_source.get(
                        item.symbol, selected_date, now, stocks.get(item.symbol)
                    )
                if self.evidence_cache_ttl > timedelta(0):
                    with self._candidate_cache_lock:
                        self._evidence_cache[cache_key] = (
                            now + self.evidence_cache_ttl,
                            now,
                            evidence,
                        )
                trigger_evidence_at = now
        mark("trigger_evidence")
        dashboard = build_quant_strategy_dashboard(
            overview,
            board,
            names=names,
            trigger_evidence=evidence,
            generated_at=now,
            candidate_scan_at=candidate_scan_at,
            candidate_scan_cached=candidate_scan_cached,
            trigger_evidence_at=trigger_evidence_at,
            trigger_evidence_cached=trigger_evidence_cached,
            candidate_scan_state=candidate_scan_state,
            candidate_scan_started_at=candidate_scan_started_at,
            candidate_scan_error=candidate_scan_error,
            candidate_scan_phase=candidate_scan_phase,
            candidate_scan_processed=candidate_scan_processed,
            candidate_scan_total=candidate_scan_total,
            extra_missing_data=tuple(extra_missing_data),
            limit=limit,
        )
        mark("dashboard_build")
        refresh_state = (
            "failed" if candidate_scan_error else
            "pending" if overview_pending or candidate_scan_state == "pending" else
            "ready"
        )
        dashboard = dashboard.model_copy(update={
            "refresh_state": refresh_state,
            "snapshot_at": persisted.snapshot_at if persisted is not None else None,
            "refresh_started_at": now if refresh_state != "ready" else None,
            "refresh_finished_at": now if refresh_state == "ready" else None,
            "snapshot_source": "computed",
        })
        if self.snapshot_store is not None and refresh_state == "ready":
            dashboard = dashboard.model_copy(update={"snapshot_at": now})
            self.snapshot_store.save(dashboard)
            mark("snapshot_save")
        if self.shadow_ledger is not None and refresh_state == "ready":
            self.shadow_ledger.freeze(dashboard)
            mark("shadow_freeze")
        return finish(dashboard)

    def _record_shared_snapshot(
        self, result: QuantStrategyDashboard, *, latency_ms: int
    ) -> None:
        registry = self.shared_snapshot_registry
        bus = self.realtime_snapshot_bus
        if registry is None and bus is None:
            return
        projection = result.model_dump(
            mode="json",
            exclude={
                "generated_at", "observed_at", "next_refresh_at",
                "refresh_started_at", "refresh_finished_at",
                "candidate_scan_at", "trigger_evidence_at",
            },
        )
        encoded = json.dumps(
            projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        stages = {item.key: item.count for item in result.candidate_funnel.stages}
        universe = stages.get("universe", 0)
        factor_ready = stages.get("factor_ready", 0)
        coverage = round(factor_ready / universe * 100, 2) if universe else None
        reused = result.snapshot_source == "disk" or result.candidate_scan_cached
        if registry is not None:
            try:
                registry.record(
                    "quant_factors",
                    content_hash=hashlib.sha256(encoded).hexdigest(),
                    trade_date=result.as_of,
                    observed_at=result.observed_at,
                    coverage_percent=coverage,
                    freshness=result.refresh_mode,
                    source=result.snapshot_source,
                    reused=reused,
                    latency_ms=latency_ms,
                )
            except Exception:
                pass
        if bus is not None and not reused and result.refresh_state == "ready":
            try:
                bus.publish(
                    "quant_strategy",
                    result.model_dump(mode="json"),
                    observed_at=result.observed_at,
                    source=result.snapshot_source,
                    freshness=result.refresh_mode,
                )
            except Exception:
                return
