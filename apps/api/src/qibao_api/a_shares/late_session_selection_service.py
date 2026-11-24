import hashlib
import json
import threading
from collections import OrderedDict
from time import monotonic
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Callable
from zoneinfo import ZoneInfo

from qibao_api.a_shares.late_session_selection import classify_behavior, classify_phase, evaluate_candidate
from qibao_api.a_shares.late_session_factor_cache import LateSessionFactorCache
from qibao_api.a_shares.late_session_lifecycle import LateSessionLifecycleTracker, classify_monitor_stage
from qibao_api.contracts.late_session_selection import (
    DEFAULT_LATE_SESSION_RULE_SETTINGS,
    LateSessionBehavior,
    LateSessionCandidateResult,
    LateSessionQuote,
    LateSessionRuleResult,
    LateSessionRuleSettings,
    LateSessionSelectionResponse,
)
from qibao_api.gongbu.tdx_local_overview import derive_intraday_average_price
from qibao_api.operations.field_arbitration import FieldArbitrator, FieldEvidence
from qibao_api.operations.refresh_policy import RefreshPolicy
from qibao_api.operations.source_circuit_breaker import SourceCircuitBreaker


CHINA_TZ = ZoneInfo("Asia/Shanghai")
REFRESH_INTERVAL_MS = 1000


class LateSessionSelectionService:
    def __init__(self, *, local_market_source, bar_repository, instrument_directory, tencent_source=None, market_overview_service=None, factor_cache: LateSessionFactorCache | None = None, lifecycle_tracker: LateSessionLifecycleTracker | None = None, refresh_policy: RefreshPolicy | None = None, field_arbitrator: FieldArbitrator | None = None, source_circuit_breaker: SourceCircuitBreaker | None = None, realtime_snapshot_bus=None, audit_store=None, clock: Callable[[], datetime] | None = None) -> None:
        self.local_market_source = local_market_source
        self.bar_repository = bar_repository
        self.instrument_directory = instrument_directory
        self.tencent_source = tencent_source
        self.market_overview_service = market_overview_service
        self.factor_cache = factor_cache or LateSessionFactorCache()
        self.lifecycle_tracker = lifecycle_tracker or LateSessionLifecycleTracker()
        self.refresh_policy = refresh_policy or RefreshPolicy()
        self.field_arbitrator = field_arbitrator or FieldArbitrator()
        self.source_circuit_breaker = source_circuit_breaker or SourceCircuitBreaker()
        self.realtime_snapshot_bus = realtime_snapshot_bus
        self.audit_store = audit_store
        self._published_fingerprint: str | None = None
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._enrichment_observed_at: datetime | None = None
        self._enrichment: dict[str, object] = {}
        self._on_demand_refresh_at: datetime | None = None
        self._refresh_thread: threading.Thread | None = None
        self._refresh_thread_lock = threading.Lock()
        self._refresh_error: str | None = None
        self._snapshot_lock = threading.RLock()
        self._snapshots: OrderedDict[str, tuple[float, LateSessionSelectionResponse]] = OrderedDict()

    def analysis_snapshot(self, snapshot_id: str) -> LateSessionSelectionResponse:
        with self._snapshot_lock:
            saved = self._snapshots.get(snapshot_id)
            if saved is None or monotonic() - saved[0] > 900:
                self._snapshots.pop(snapshot_id, None)
                raise KeyError(snapshot_id)
            return saved[1].model_copy(deep=True)

    def _remember_snapshot(self, response: LateSessionSelectionResponse) -> LateSessionSelectionResponse:
        canonical = response.model_dump_json(exclude={"snapshot_id"})
        snapshot_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        response = response.model_copy(update={"snapshot_id": snapshot_id}, deep=True)
        now = monotonic()
        with self._snapshot_lock:
            while self._snapshots:
                first = next(iter(self._snapshots))
                if now - self._snapshots[first][0] <= 900:
                    break
                self._snapshots.pop(first)
            self._snapshots[snapshot_id] = (now, response.model_copy(deep=True))
            self._snapshots.move_to_end(snapshot_id)
            while len(self._snapshots) > 128:
                self._snapshots.popitem(last=False)
        return response

    def current(
        self,
        now: datetime | None = None,
        *,
        limit: int = 100,
        settings: LateSessionRuleSettings = DEFAULT_LATE_SESSION_RULE_SETTINGS,
    ) -> LateSessionSelectionResponse:
        now = now or self.clock()
        local_now = now.astimezone(CHINA_TZ)
        phase = classify_phase(local_now, start_time=settings.start_time, end_time=settings.end_time)
        trading_date = local_now.date()
        quotes = tuple(getattr(self.local_market_source, "current_quotes", lambda: ())())
        if not quotes:
            refresh = getattr(
                self.local_market_source,
                "refresh_fast",
                getattr(self.local_market_source, "refresh", None),
            )
            last_attempt = self._on_demand_refresh_at
            can_refresh = last_attempt is None or (now - last_attempt).total_seconds() >= 5
            if callable(refresh) and can_refresh:
                self._schedule_refresh(refresh, now)
                refresh_thread = self._refresh_thread
                if refresh_thread is not None:
                    # Fast in-process sources can still satisfy the first
                    # request, while a blocked network source never holds the
                    # HTTP worker for more than this small paint window.
                    refresh_thread.join(timeout=0.1)
                quotes = tuple(getattr(self.local_market_source, "current_quotes", lambda: ())())
        if not quotes:
            if self._refresh_in_progress():
                detail = "本地通达信全市场实时快照尚未就绪，正在后台刷新；页面已先返回状态"
            elif self._refresh_error:
                detail = f"本地通达信全市场实时快照刷新失败：{self._refresh_error}"
            else:
                detail = "本地通达信全市场实时快照尚未就绪"
            return self._publish_if_changed(self._unavailable(trading_date, local_now, phase, detail))
        quotes_are_cached = bool(
            getattr(self.local_market_source, "current_quotes_are_cached", lambda: False)()
        )
        # A restored quote snapshot is the first paint, not a reason to block
        # the page on a full-market remote enrichment request. The refresh
        # loop will publish live quotes; the next request can then enrich them.
        enriched = {} if quotes_are_cached else self._enrich(quotes, now)
        symbols = tuple(raw.symbol for raw in quotes)
        slow_factors = {} if quotes_are_cached else self.factor_cache.get_or_build(
            trading_date,
            symbols,
            lambda requested: self._history_windows(requested, trading_date),
        ).factors
        evaluation_quotes = self._reduce_monitor_pool(
            quotes,
            enriched,
            slow_factors,
            settings,
            maximum=300,
        ) if phase in {"live_monitor", "post_close"} else quotes
        evaluated: list[LateSessionCandidateResult] = []
        for raw in evaluation_quotes:
            data = enriched.get(raw.symbol, {})
            field_conflicts: list[str] = []
            turnover_rate, turnover_source = self._resolve_quote_field(
                "turnover_rate",
                getattr(raw, "turnover_rate", None),
                getattr(raw, "observed_at", None) or now,
                data.get("turnover_rate"),
                data.get("observed_at"),
                now,
                field_conflicts,
            )
            market_cap_yi, market_cap_source = self._resolve_quote_field(
                "market_cap_yi",
                getattr(raw, "market_cap_yi", None),
                getattr(raw, "observed_at", None) or now,
                data.get("market_cap_yi"),
                data.get("observed_at"),
                now,
                field_conflicts,
            )
            explicit_average = data.get("intraday_average_price") or getattr(raw, "intraday_average_price", None)
            average = explicit_average or derive_intraday_average_price(
                amount_wan=getattr(raw, "amount_wan", None),
                volume=getattr(raw, "volume", None),
                low=getattr(raw, "low", None),
                high=getattr(raw, "high", None),
            )
            slow = slow_factors.get(raw.symbol)
            volume_ratio = data.get("volume_ratio") or (
                self._volume_ratio_from_baseline(raw.volume, slow.volume_baseline_5d)
                if slow is not None
                else None if quotes_are_cached
                else self._volume_ratio(raw.symbol, raw.volume)
            )
            quote = LateSessionQuote(
                symbol=raw.symbol,
                name=raw.name or (self.instrument_directory.resolve(raw.symbol).name if self.instrument_directory.resolve(raw.symbol) else raw.symbol),
                price=raw.price,
                previous_close=raw.previous_close,
                change_percent=raw.change_percent,
                volume_ratio=volume_ratio,
                turnover_rate=turnover_rate,
                market_cap_yi=market_cap_yi,
                twenty_day_limit_up_count=(
                    None
                    if quotes_are_cached
                    else slow.twenty_day_limit_up_count
                    if slow is not None
                    else self._twenty_day_limit_count(raw.symbol, trading_date)
                ),
                intraday_average_price=average,
                observed_at=raw.observed_at or now,
                source=("tdx-local-realtime" + ("+tencent" if data else "") + ("+vwap" if explicit_average is None and average is not None else "")),
                field_sources={
                    key: value for key, value in (
                        ("turnover_rate", turnover_source),
                        ("market_cap_yi", market_cap_source),
                    ) if value is not None
                },
                field_conflicts=tuple(field_conflicts),
            )
            result = evaluate_candidate(
                quote,
                settings=settings,
                allow_close_boundary=(
                    phase == "post_close"
                    and quote.observed_at.astimezone(CHINA_TZ).date() == trading_date
                ),
            )
            above = None if average is None else raw.price > average
            tags = classify_behavior(change_percent=raw.change_percent, volume_ratio=quote.volume_ratio, above_average=above)
            evaluated.append(result.model_copy(update={"behavior_tags": tags}))
        passed = [item for item in evaluated if item.passed]
        pre_screened = [
            item for item in evaluated
            if all(rule.status in {"passed", "disabled"} for rule in item.rules if rule.key != "time_window")
        ]
        strict_pool = passed if phase != "pre_screen" else pre_screened
        core_keys = {"change_percent", "turnover_rate", "market_cap"}
        if phase != "pre_screen":
            core_keys.add("time_window")
        observation_pool = sorted(
            (
                item
                for item in evaluated
                if all(
                    rule.status in {"passed", "disabled"}
                    for rule in item.rules
                    if rule.key in core_keys
                )
                and any(rule.status in {"failed", "unavailable"} for rule in item.rules)
            ),
            key=lambda item: (
                sum(rule.status == "failed" for rule in item.rules),
                sum(rule.status == "unavailable" for rule in item.rules),
                -sum(rule.status == "passed" for rule in item.rules),
                item.quote.symbol,
            ),
        )
        candidates = tuple((strict_pool or observation_pool)[: max(1, limit)])
        has_observation_candidates = bool(candidates) and not bool(strict_pool)
        source_quality = "ready" if all(
            item.quote.turnover_rate is not None
            and item.quote.market_cap_yi is not None
            and (not settings.intraday_average_enabled or item.quote.intraday_average_price is not None)
            and (not settings.twenty_day_limit_up_enabled or item.quote.twenty_day_limit_up_count is not None)
            for item in evaluated
        ) else "partial"
        limitations: list[str] = []
        if any(item.quote.intraday_average_price is None for item in evaluated):
            limitations.append("本地快照未提供真实分时黄线，相关规则保持不可用")
        conflicts = sorted({field for item in evaluated for field in item.quote.field_conflicts})
        if conflicts:
            limitations.append(f"真实来源字段冲突：{'、'.join(conflicts)}；已阻止严格候选")
        if not self.tencent_source:
            limitations.append("未接入腾讯补充字段，换手率和市值可能不可用")
        if phase == "pre_screen":
            limitations.append("14:30前展示六项条件预筛结果，时间闸门和尾盘行为需实时窗口确认")
        if phase == "post_close":
            limitations.append("15:00后停止高频刷新，结果为收盘冻结快照")
        if len(evaluation_quotes) < len(quotes):
            limitations.append(f"全市场 {len(quotes)} 只已缩减为 {len(evaluation_quotes)} 只尾盘实时监控池")
        if quotes_are_cached:
            limitations.append("当前使用上次真实行情缓存；历史因子将在实时行情刷新后补齐")
        if has_observation_candidates:
            limitations.append("严格候选为空；当前展示通过时间、涨幅、换手率和市值核心条件的观察候选，未通过与待补齐项已逐股标注")
        source_evidence = ["通达信本地全市场实时快照", "本地日线仓储20交易日窗口"]
        if any("+vwap" in item.quote.source for item in evaluated):
            source_evidence.append("通达信成交额/成交量推导累计成交均价（VWAP）")
        active_symbols = {item.quote.symbol for item in candidates}
        lifecycle_results = self.lifecycle_tracker.update(trading_date, tuple(candidates), now)
        active_candidates = tuple(item for item in lifecycle_results if item.quote.symbol in active_symbols)
        invalidated_candidates = tuple(item for item in lifecycle_results if item.lifecycle_status == "invalidated")
        response = LateSessionSelectionResponse(
            status="partial" if has_observation_candidates else "ready" if candidates else ("partial" if evaluated else "unavailable"),
            trading_date=trading_date,
            server_time=local_now,
            phase=phase,
            monitor_stage=classify_monitor_stage(local_now),
            refresh_interval_ms=self._refresh_interval(phase),
            next_refresh_ms=self._refresh_interval(phase),
            source_quality=source_quality,
            universe_count=len(quotes),
            monitor_pool_count=len(evaluation_quotes),
            quote_count=len(evaluated),
            candidate_count=len(active_candidates),
            rules=self._summary_rules(evaluated, settings),
            data_state=("partial" if has_observation_candidates else "ready" if candidates else "partial" if any(rule.status == "unavailable" for item in evaluated for rule in item.rules) else "no_candidates"),
            no_data_reason=None if candidates else self._no_data_reason(evaluated, quotes_count=len(quotes), phase=phase, limitations=limitations),
            settings=settings,
            default_settings=DEFAULT_LATE_SESSION_RULE_SETTINGS,
            candidates=active_candidates,
            invalidated_candidates=invalidated_candidates,
            behaviors=self._behaviors(phase, evaluated),
            source_evidence=tuple(source_evidence) + (("腾讯行情补充市值/换手率",) if self.tencent_source else ()),
            limitations=tuple(limitations),
        )
        return self._publish_if_changed(response)

    def _schedule_refresh(self, refresh: Callable[[], object], now: datetime) -> None:
        with self._refresh_thread_lock:
            if self._refresh_thread is not None and self._refresh_thread.is_alive():
                return
            self._on_demand_refresh_at = now
            self._refresh_error = None
            self._refresh_thread = threading.Thread(
                target=self._run_refresh,
                args=(refresh,),
                name="late-session-market-refresh",
                daemon=True,
            )
            self._refresh_thread.start()

    def _run_refresh(self, refresh: Callable[[], object]) -> None:
        try:
            refresh()
        except Exception as error:
            self._refresh_error = self._friendly_refresh_error(error)

    @staticmethod
    def _friendly_refresh_error(error: Exception) -> str:
        message = str(error).lower()
        if isinstance(error, TimeoutError) or "timeout" in message or "timed out" in message:
            return "数据源响应超时，请检查网络或通达信本地服务"
        if isinstance(error, OSError) or "connect" in message or "refused" in message:
            return "数据源连接失败，请检查网络或通达信本地服务"
        return "数据源刷新失败，请稍后重试"

    def _refresh_in_progress(self) -> bool:
        thread = self._refresh_thread
        return thread is not None and thread.is_alive()

    def _reduce_monitor_pool(
        self,
        quotes: tuple[object, ...],
        enriched: dict[str, dict[str, object]],
        slow_factors,
        settings: LateSessionRuleSettings,
        *,
        maximum: int,
    ) -> tuple[object, ...]:
        if len(quotes) <= maximum:
            return quotes

        def score(raw) -> tuple[int, str]:
            points = 0
            change = raw.change_percent
            if not settings.change_enabled or settings.change_min <= change <= settings.change_max:
                points += 100
            elif settings.change_min - Decimal("1.5") <= change <= settings.change_max + Decimal("1.5"):
                points += 30
            data = enriched.get(raw.symbol, {})
            turnover = getattr(raw, "turnover_rate", None) or data.get("turnover_rate")
            if not settings.turnover_rate_enabled or (
                turnover is not None and settings.turnover_rate_min <= turnover <= settings.turnover_rate_max
            ):
                points += 20
            market_cap = getattr(raw, "market_cap_yi", None) or data.get("market_cap_yi")
            if not settings.market_cap_enabled or (
                market_cap is not None and settings.market_cap_min <= market_cap <= settings.market_cap_max
            ):
                points += 20
            slow = slow_factors.get(raw.symbol)
            volume_ratio = self._volume_ratio_from_baseline(raw.volume, slow.volume_baseline_5d) if slow is not None else None
            if not settings.volume_ratio_enabled or (
                volume_ratio is not None and settings.volume_ratio_min <= volume_ratio <= settings.volume_ratio_max
            ):
                points += 15
            if not settings.twenty_day_limit_up_enabled or (
                slow is not None
                and slow.twenty_day_limit_up_count is not None
                and slow.twenty_day_limit_up_count >= settings.twenty_day_limit_up_min
                and (settings.twenty_day_limit_up_max is None or slow.twenty_day_limit_up_count <= settings.twenty_day_limit_up_max)
            ):
                points += 10
            average = getattr(raw, "intraday_average_price", None)
            if not settings.intraday_average_enabled or average is not None:
                points += 5
            return -points, raw.symbol

        ranked = sorted(quotes, key=score)
        return tuple(ranked[:maximum])

    def _publish_if_changed(self, response: LateSessionSelectionResponse) -> LateSessionSelectionResponse:
        response = self._remember_snapshot(response)
        payload = response.model_dump(mode="json")
        fingerprint_payload = {
            "trading_date": payload.get("trading_date"),
            "phase": payload.get("phase"),
            "monitor_stage": payload.get("monitor_stage"),
            "status": payload.get("status"),
            "data_state": payload.get("data_state"),
            "candidates": [
                {
                    "symbol": item.get("quote", {}).get("symbol"),
                    "lifecycle_status": item.get("lifecycle_status"),
                    "rule_bitmap": item.get("rule_bitmap"),
                    "passed": item.get("passed"),
                }
                for item in payload.get("candidates", ())
            ],
            "invalidated": [item.get("quote", {}).get("symbol") for item in payload.get("invalidated_candidates", ())],
        }
        fingerprint = hashlib.sha256(json.dumps(fingerprint_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        if fingerprint == self._published_fingerprint:
            return response
        self._published_fingerprint = fingerprint
        output_hash = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        input_payload = {
            "settings": payload.get("settings"),
            "source_evidence": payload.get("source_evidence"),
            "quotes": [item.get("quote") for item in payload.get("candidates", ())],
            "monitor_stage": payload.get("monitor_stage"),
        }
        input_hash = hashlib.sha256(json.dumps(input_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        if self.audit_store is not None:
            self.audit_store.record(
                trading_date=response.trading_date,
                captured_at=response.server_time,
                input_hash=input_hash,
                output_hash=output_hash,
                formula_version="late-session-v2",
                regime=None,
                payload=fingerprint_payload,
            )
        if self.realtime_snapshot_bus is not None:
            self.realtime_snapshot_bus.publish(
                "late_session_candidates",
                payload,
                observed_at=response.server_time,
                source=response.source_evidence[0] if response.source_evidence else "late-session-selection",
                freshness="live" if response.phase == "live_monitor" else "snapshot",
            )
        return response

    @staticmethod
    def _no_data_reason(
        results: list[LateSessionCandidateResult],
        *,
        quotes_count: int,
        phase: str,
        limitations: list[str],
    ) -> str:
        unavailable = sorted({rule.label for item in results for rule in item.rules if rule.status == "unavailable"})
        if unavailable:
            return f"已扫描全市场 {quotes_count} 只，但 { '、'.join(unavailable) } 的真实字段覆盖不足，严格规则无法完成筛选"
        if phase == "pre_screen":
            return f"已扫描全市场 {quotes_count} 只，当前规则下没有股票通过 14:30 前预筛"
        if limitations:
            return f"已扫描全市场 {quotes_count} 只，当前规则没有产生候选；限制原因：{ '；'.join(limitations) }"
        return f"已扫描全市场 {quotes_count} 只，但当前规则没有股票满足全部条件"

    def _enrich(self, quotes: tuple[object, ...], now: datetime) -> dict[str, dict[str, object]]:
        if self.tencent_source is None:
            return {}
        if all(
            getattr(quote, "turnover_rate", None) is not None
            and getattr(quote, "market_cap_yi", None) is not None
            for quote in quotes
        ):
            return {}
        if self._enrichment_observed_at is not None and (now - self._enrichment_observed_at).total_seconds() < 5:
            return self._enrichment
        result: dict[str, dict[str, object]] = {}
        symbols = [quote.symbol for quote in quotes]
        for start in range(0, len(symbols), 320):
            batch = tuple(symbols[start:start + 320])
            if not self.source_circuit_breaker.before_request():
                break
            try:
                rows, _warnings = self.tencent_source.fetch_stocks(batch)
            except Exception:
                self.source_circuit_breaker.record_failure()
                continue
            self.source_circuit_breaker.record_success()
            for row in rows:
                result[row.symbol] = {
                    "market_cap_yi": row.market_cap_yi,
                    "turnover_rate": row.turnover_rate,
                    "volume_ratio": None,
                    "intraday_average_price": None,
                    "observed_at": getattr(row, "observed_at", now),
                }
        self._enrichment = result
        self._enrichment_observed_at = now
        return result

    def _resolve_quote_field(
        self,
        field: str,
        raw_value,
        raw_observed_at: datetime,
        enriched_value,
        enriched_observed_at,
        now: datetime,
        conflicts: list[str],
    ):
        evidence = [FieldEvidence(
            value=raw_value,
            source="tdx-local-realtime",
            observed_at=raw_observed_at,
            priority=10,
            max_age_seconds=300,
        )]
        if enriched_observed_at is not None or enriched_value is not None:
            evidence.append(FieldEvidence(
                value=enriched_value,
                source="tencent-realtime",
                observed_at=enriched_observed_at or now,
                priority=20,
                max_age_seconds=300,
            ))
        resolution = self.field_arbitrator.select(field, tuple(evidence), now=now)
        if resolution.status == "conflicted":
            conflicts.append(field)
        return resolution.value, resolution.source

    def _refresh_interval(self, phase: str) -> int:
        policy_phase = "intraday" if phase == "live_monitor" else "post_close" if phase == "post_close" else "pre_market"
        return self.refresh_policy.interval_ms("late_session_candidates", phase=policy_phase, visible=True) or 60_000

    def _twenty_day_limit_count(self, symbol: str, as_of: date) -> int | None:
        try:
            bars = self.bar_repository.latest(symbol, limit=21, cutoff=None)
        except Exception:
            return None
        return self._twenty_day_limit_count_from_bars(symbol, bars, as_of)

    def _history_windows(self, symbols: tuple[str, ...], as_of: date) -> dict[str, list[object]]:
        latest_many = getattr(self.bar_repository, "latest_many", None)
        if not callable(latest_many) or not symbols:
            return {}
        try:
            return latest_many(list(symbols), 21, as_of)
        except Exception:
            return {}

    @staticmethod
    def _twenty_day_limit_count_from_bars(symbol: str, bars, as_of: date) -> int | None:
        if any(getattr(bar, "trade_date", None) is not None for bar in bars):
            bars = [bar for bar in bars if bar.trade_date <= as_of]
        if len(bars) < 21:
            return None
        count = 0
        for index, bar in enumerate(bars[:20]):
            previous_close = bars[index + 1].close
            if previous_close <= 0:
                continue
            rate = Decimal("0.2") if symbol.startswith(("300", "301", "688", "689")) else Decimal("0.1")
            if bar.close >= (previous_close * (Decimal(1) + rate) * Decimal("0.995")):
                count += 1
        return count

    def _volume_ratio(self, symbol: str, current_volume: Decimal) -> Decimal | None:
        try:
            bars = self.bar_repository.latest(symbol, limit=6, cutoff=None)
        except Exception:
            return None
        if len(bars) < 6 or current_volume < 0:
            return None
        return self._volume_ratio_from_bars(current_volume, bars)

    @staticmethod
    def _volume_ratio_from_bars(current_volume: Decimal, bars) -> Decimal | None:
        if len(bars) < 6 or current_volume < 0:
            return None
        baseline = sum((bar.volume for bar in bars[1:6]), Decimal("0")) / Decimal("5")
        if baseline <= 0:
            return None
        return (current_volume / baseline).quantize(Decimal("0.01"))

    @staticmethod
    def _volume_ratio_from_baseline(current_volume: Decimal, baseline: Decimal | None) -> Decimal | None:
        if baseline is None or baseline <= 0 or current_volume < 0:
            return None
        return (current_volume / baseline).quantize(Decimal("0.01"))

    @staticmethod
    def _summary_rules(results: list[LateSessionCandidateResult], settings: LateSessionRuleSettings) -> tuple[LateSessionRuleResult, ...]:
        keys = ("time_window", "change_percent", "volume_ratio", "turnover_rate", "market_cap", "twenty_day_limit_up", "above_intraday_average")
        labels = {"time_window": "监控时间", "change_percent": "涨幅", "volume_ratio": "量比", "turnover_rate": "换手率", "market_cap": "总市值", "twenty_day_limit_up": "20日涨停", "above_intraday_average": "分时黄线"}
        targets = {
            "time_window": f"{settings.start_time.strftime('%H:%M')}–{settings.end_time.strftime('%H:%M')}",
            "change_percent": f"{settings.change_min}%–{settings.change_max}%",
            "volume_ratio": f"{settings.volume_ratio_min}–{settings.volume_ratio_max}",
            "turnover_rate": f"{settings.turnover_rate_min}%–{settings.turnover_rate_max}%",
            "market_cap": f"{settings.market_cap_min}–{settings.market_cap_max}亿元",
            "twenty_day_limit_up": f"近20日 {settings.twenty_day_limit_up_min}–{settings.twenty_day_limit_up_max if settings.twenty_day_limit_up_max is not None else '不限'} 次",
            "above_intraday_average": {"above": "最新价>真实分时均价", "below": "最新价<真实分时均价", "any": "不限制黄线方向"}[settings.intraday_relation],
        }
        rows: list[LateSessionRuleResult] = []
        for key in keys:
            matched = [next((rule for rule in item.rules if rule.key == key), None) for item in results]
            matched = [rule for rule in matched if rule is not None]
            if not matched:
                status = "unavailable"
                detail = "暂无可验证全市场字段"
            elif any(rule.status == "unavailable" for rule in matched):
                status = "unavailable"
                detail = "字段覆盖不足，未使用代理值"
            elif all(rule.status == "disabled" for rule in matched):
                status = "disabled"
                detail = "该规则已停用"
            elif any(rule.status == "passed" for rule in matched):
                status = "passed"
                detail = f"{sum(rule.status == 'passed' for rule in matched)} / {len(matched)} 只通过"
            else:
                status = "failed"
                detail = "当前没有股票通过此条件"
            rows.append(LateSessionRuleResult(key=key, label=labels[key], target=targets[key], status=status, detail=detail))
        return tuple(rows)

    @staticmethod
    def _behaviors(phase: str, results: list[LateSessionCandidateResult]) -> tuple[LateSessionBehavior, ...]:
        return (
            LateSessionBehavior(key="weak_rally", title="尾盘拉升量能不足", level="risk", description="收盘前快速上拉但成交量未同步放大，次日冲高回落风险较高。", evidence=("需要尾盘分时价格与成交量序列", "当前快照不足时保持待核验")),
            LateSessionBehavior(key="heavy_selloff", title="尾盘急跌放量", level="risk", description="收盘前砸盘且放量，先视为资金出逃风险，不急于抄底。", evidence=("需要14:30–15:00增量成交量",)),
            LateSessionBehavior(key="steady_rise", title="尾盘平稳走高量价配合", level="observe", description="价格平稳抬升且量能温和放大，列为次日溢价观察。", evidence=("需要连续分时序列确认",)),
            LateSessionBehavior(key="flat_lag", title="尾盘横盘弱于大盘", level="risk", description="大盘走强而个股横盘，存在次日补跌风险。", evidence=("需要指数与个股分时对照",)),
            LateSessionBehavior(key="index_resilience", title="大盘跳水个股抗跌", level="observe", description="指数尾盘跳水而个股守住关键价位，列为次日强势观察。", evidence=("需要指数分钟数据和关键价位",)),
            LateSessionBehavior(key="pressure_breakout", title="尾盘放量突破压力位", level="pending", description="收盘前半小时稳步放量突破前高，次日进入重点观察。", evidence=("需要历史前高与尾盘分时量价",)),
        )

    @staticmethod
    def _unavailable(trading_date: date, now: datetime, phase: str, detail: str) -> LateSessionSelectionResponse:
        # The local snapshot may still be warming up. Retry quickly so the
        # page does not remain on a misleading 0/0 state for 15 seconds.
        return LateSessionSelectionResponse(status="unavailable", trading_date=trading_date, server_time=now, phase=phase, monitor_stage=classify_monitor_stage(now), refresh_interval_ms=1000, next_refresh_ms=1000, source_quality="unavailable", universe_count=0, monitor_pool_count=0, quote_count=0, candidate_count=0, rules=(), data_state="no_market_data", no_data_reason=detail, behaviors=(), limitations=(detail,))
