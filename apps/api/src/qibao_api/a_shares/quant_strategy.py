from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from threading import RLock
from typing import Mapping
from zoneinfo import ZoneInfo

from qibao_api.a_shares.models import CandidateBoard, CandidateEntry
from qibao_api.contracts.market_overview import (
    MarketOverviewResponse,
    OverviewFeatureStock,
)
from qibao_api.contracts.quant_strategy import (
    QuantStrategyCandidate,
    QuantStrategyDashboard,
    QuantStrategyModel,
)


ZERO = Decimal()
ONE = Decimal("1")
TWO_PLACES = Decimal("0.01")
CHINA_TZ = ZoneInfo("Asia/Shanghai")
SAFE_CANDIDATE_SCAN_ERROR = "本地候选扫描失败，请检查日线覆盖和数据源状态"

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
}

INVALIDATIONS_BY_REGIME = {
    "情绪主升": ("跌破盘中均价且3分钟不能收回", "资金净流入转负"),
    "指数权重进攻": ("回踩均价后放量跌破", "权重板块强度同步转弱"),
    "轮动震荡": ("开盘涨幅超过4%", "触发分低于80或盈亏比低于2.5"),
    "冰点修复": ("跌停打开后再次回封", "修复幅度与大单流入同时转弱"),
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
        ticks = tuple(self.poll_repository.intraday_snapshots(
            symbol, trading_date, cutoff=cutoff,
        ))
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
    if missing:
        status = "pending_trigger"
    elif not confirmed:
        status = "reject"
    elif score >= Decimal("80"):
        status = "alert"
    elif score >= Decimal("70"):
        status = "watch"
    else:
        status = "reject"
    strategy_coef = ONE if regime in {"情绪主升", "指数权重进攻"} else Decimal("0.8")
    planned_position = _q(
        Decimal("0.2") * market_coef * strategy_coef * rr_score
    )
    risk_flags = []
    if entry.factor_snapshot.volatility_20d >= Decimal("0.04"):
        risk_flags.append("高波动")
    if entry.factor_snapshot.drawdown_60d <= Decimal("-0.25"):
        risk_flags.append("近60日回撤较深")
    risk_flags.append("缺少明确止损/目标价，盈亏比分不计分")
    evidence_coverage = _q((Decimal("70") + trigger_coverage * Decimal("0.3")))
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
        evidence_coverage_percent=evidence_coverage,
        buy_triggers=TRIGGERS_BY_REGIME[regime],
        invalidation_rules=INVALIDATIONS_BY_REGIME[regime],
        risk_flags=tuple(risk_flags),
        missing_evidence=missing,
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
        "trigger_evidence_at": trigger_evidence_timestamp,
        "trigger_evidence_age_seconds": trigger_evidence_age,
        "trigger_evidence_cached": trigger_evidence_cached,
    }
    regime = overview.regime.regime
    missing = tuple(dict.fromkeys((
        *overview.regime.missing_factors,
        *(("candidate_history",) if not board.short_term else ()),
        *((f"candidate_scan_{candidate_scan_state}",)
          if candidate_scan_state != "ready" else ()),
    )))
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
            candidates=(),
            discipline="市场风格尚未形成，等待真实横截面指标后再选择策略。",
            missing_data=missing or ("market_regime",),
            warnings=overview.warnings,
            sources=overview.sources,
        )
    if regime in {"高位退潮", "缩量混沌"}:
        return QuantStrategyDashboard(
            status="partial",
            as_of=overview.as_of,
            observed_at=overview.observed_at,
            **refresh_metadata,
            **cache_metadata,
            metrics=overview.regime_metrics,
            regime=overview.regime,
            strategy_models=_strategy_models(regime),
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
        candidates=candidates,
        discipline=DISCIPLINE_BY_REGIME[regime],
        missing_data=missing,
        warnings=overview.warnings,
        sources=tuple(dict.fromkeys((*overview.sources, *board.sources))),
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
    ) -> None:
        self.overview_service = overview_service
        self.candidate_service = candidate_service
        self.instrument_directory = instrument_directory
        self.trigger_evidence_source = trigger_evidence_source
        self.cache_ttl = timedelta(seconds=max(0, cache_seconds))
        self.evidence_cache_ttl = timedelta(seconds=max(0, evidence_cache_seconds))
        self.defer_initial_scan = defer_initial_scan
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
        self._candidate_scan_jobs: dict[tuple[date, int], Future] = {}
        self._candidate_scan_started: dict[tuple[date, int], datetime] = {}
        self._candidate_scan_errors: dict[tuple[date, int], str] = {}

    def close(self) -> None:
        executor = self._candidate_scan_executor
        self._candidate_scan_executor = None
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

    def candidate_scan_ready(
        self, now: datetime, *, as_of: date | None = None, limit: int = 12
    ) -> bool:
        """检查后台候选扫描是否结束，不在调用线程执行扫描。"""
        key = (as_of or now.astimezone(CHINA_TZ).date(), limit)
        with self._candidate_cache_lock:
            job = self._candidate_scan_jobs.get(key)
        return job is not None and job.done()

    def _scan_candidates(self, selected_date: date, limit: int):
        board = self.candidate_service.candidates(selected_date, limit)
        names = {}
        for item in board.short_term:
            instrument = self.instrument_directory.resolve(item.symbol)
            if instrument is not None:
                names[item.symbol] = instrument.name
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
            self._candidate_scan_started[cache_key] = now
            self._candidate_scan_jobs[cache_key] = self._candidate_scan_executor.submit(
                self._scan_candidates, selected_date, limit
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
                self._candidate_scan_jobs.pop(cache_key, None)
                self._candidate_scan_started.pop(cache_key, None)
            return None, None, "failed", started, message
        with self._candidate_cache_lock:
            self._candidate_cache[cache_key] = (
                now + self.cache_ttl, now, board, names
            )
            self._candidate_scan_jobs.pop(cache_key, None)
            self._candidate_scan_started.pop(cache_key, None)
            self._candidate_scan_errors.pop(cache_key, None)
            self._evidence_cache.pop(cache_key, None)
        return board, names, "ready", now, None

    def current(
        self, now: datetime, *, as_of: date | None = None, limit: int = 12
    ) -> QuantStrategyDashboard:
        overview = self.overview_service.current(now)
        selected_date = as_of or overview.as_of
        if selected_date != overview.as_of:
            raise ValueError(
                "historical market regime is unavailable for the requested date"
            )
        cache_key = (selected_date, limit)
        cached = None
        candidate_scan_cached = False
        candidate_scan_at = now
        candidate_scan_state = "ready"
        candidate_scan_started_at = now
        candidate_scan_error = None
        if self.cache_ttl > timedelta(0):
            with self._candidate_cache_lock:
                cached = self._candidate_cache.get(cache_key)
                if cached is not None and now >= cached[0]:
                    self._candidate_cache.pop(cache_key, None)
                    cached = None
        if cached is None:
            if self.defer_initial_scan:
                self._start_deferred_scan(cache_key, selected_date, limit, now)
                (
                    board, names, candidate_scan_state,
                    candidate_scan_started_at, candidate_scan_error,
                ) = self._consume_deferred_scan(cache_key, now)
                if board is None:
                    board = CandidateBoard(
                        as_of=selected_date,
                        universe_size=0,
                        eligible_size=0,
                        sources=(),
                        short_term=[],
                        swing=[],
                    )
                    names = {}
            else:
                board, names = self._scan_candidates(selected_date, limit)
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
        evidence: dict[str, TriggerEvidence] = {}
        trigger_evidence_cached = False
        trigger_evidence_at: datetime | None = None
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
        return build_quant_strategy_dashboard(
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
            limit=limit,
        )
