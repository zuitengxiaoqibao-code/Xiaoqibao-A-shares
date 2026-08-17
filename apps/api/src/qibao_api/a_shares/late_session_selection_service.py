from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Callable
from zoneinfo import ZoneInfo

from qibao_api.a_shares.late_session_selection import classify_behavior, classify_phase, evaluate_candidate
from qibao_api.contracts.late_session_selection import (
    DEFAULT_LATE_SESSION_RULE_SETTINGS,
    LateSessionBehavior,
    LateSessionCandidateResult,
    LateSessionQuote,
    LateSessionRuleResult,
    LateSessionRuleSettings,
    LateSessionSelectionResponse,
)


CHINA_TZ = ZoneInfo("Asia/Shanghai")
REFRESH_INTERVAL_MS = 1000


class LateSessionSelectionService:
    def __init__(self, *, local_market_source, bar_repository, instrument_directory, tencent_source=None, market_overview_service=None, clock: Callable[[], datetime] | None = None) -> None:
        self.local_market_source = local_market_source
        self.bar_repository = bar_repository
        self.instrument_directory = instrument_directory
        self.tencent_source = tencent_source
        self.market_overview_service = market_overview_service
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._enrichment_observed_at: datetime | None = None
        self._enrichment: dict[str, object] = {}

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
            return self._unavailable(trading_date, local_now, phase, "本地通达信全市场实时快照尚未就绪")
        enriched = self._enrich(quotes, now)
        evaluated: list[LateSessionCandidateResult] = []
        for raw in quotes:
            data = enriched.get(raw.symbol, {})
            average = data.get("intraday_average_price") or getattr(raw, "intraday_average_price", None)
            volume_ratio = data.get("volume_ratio") or self._volume_ratio(raw.symbol, raw.volume)
            quote = LateSessionQuote(
                symbol=raw.symbol,
                name=raw.name or (self.instrument_directory.resolve(raw.symbol).name if self.instrument_directory.resolve(raw.symbol) else raw.symbol),
                price=raw.price,
                previous_close=raw.previous_close,
                change_percent=raw.change_percent,
                volume_ratio=volume_ratio,
                turnover_rate=data.get("turnover_rate"),
                market_cap_yi=data.get("market_cap_yi") or raw.market_cap_yi,
                twenty_day_limit_up_count=self._twenty_day_limit_count(raw.symbol, trading_date),
                intraday_average_price=average,
                observed_at=raw.observed_at or now,
                source="tdx-local-realtime" + ("+tencent" if data else ""),
            )
            result = evaluate_candidate(quote, settings=settings)
            above = None if average is None else raw.price > average
            tags = classify_behavior(change_percent=raw.change_percent, volume_ratio=quote.volume_ratio, above_average=above)
            evaluated.append(result.model_copy(update={"behavior_tags": tags}))
        passed = [item for item in evaluated if item.passed]
        pre_screened = [
            item for item in evaluated
            if all(rule.status in {"passed", "disabled"} for rule in item.rules if rule.key != "time_window")
        ]
        candidates = tuple((passed if phase != "pre_screen" else pre_screened)[: max(1, limit)])
        source_quality = "ready" if all(item.quote.turnover_rate is not None and item.quote.market_cap_yi is not None for item in evaluated) else "partial"
        limitations: list[str] = []
        if any(item.quote.intraday_average_price is None for item in evaluated):
            limitations.append("本地快照未提供真实分时黄线，相关规则保持不可用")
        if not self.tencent_source:
            limitations.append("未接入腾讯补充字段，换手率和市值可能不可用")
        if phase == "pre_screen":
            limitations.append("14:30前展示六项条件预筛结果，时间闸门和尾盘行为需实时窗口确认")
        if phase == "post_close":
            limitations.append("15:00后停止高频刷新，结果为收盘冻结快照")
        return LateSessionSelectionResponse(
            status="ready" if candidates else ("partial" if evaluated else "unavailable"),
            trading_date=trading_date,
            server_time=local_now,
            phase=phase,
            refresh_interval_ms=REFRESH_INTERVAL_MS if phase == "live_monitor" else 15000,
            next_refresh_ms=REFRESH_INTERVAL_MS if phase == "live_monitor" else 15000,
            source_quality=source_quality,
            universe_count=len(quotes),
            quote_count=len(evaluated),
            candidate_count=len(candidates),
            rules=self._summary_rules(evaluated, settings),
            data_state=("ready" if candidates else "partial" if any(rule.status == "unavailable" for item in evaluated for rule in item.rules) else "no_candidates"),
            no_data_reason=None if candidates else self._no_data_reason(evaluated, quotes_count=len(quotes), phase=phase, limitations=limitations),
            settings=settings,
            default_settings=DEFAULT_LATE_SESSION_RULE_SETTINGS,
            candidates=candidates,
            behaviors=self._behaviors(phase, evaluated),
            source_evidence=("通达信本地全市场实时快照", "本地日线仓储20交易日窗口") + (("腾讯行情补充市值/换手率",) if self.tencent_source else ()),
            limitations=tuple(limitations),
        )

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

    def _enrich(self, quotes: tuple[object, ...], now: datetime) -> dict[str, dict[str, Decimal | None]]:
        if self.tencent_source is None:
            return {}
        if self._enrichment_observed_at is not None and (now - self._enrichment_observed_at).total_seconds() < 5:
            return self._enrichment
        result: dict[str, dict[str, Decimal | None]] = {}
        symbols = [quote.symbol for quote in quotes]
        for start in range(0, len(symbols), 100):
            batch = tuple(symbols[start:start + 100])
            try:
                rows, _warnings = self.tencent_source.fetch_stocks(batch)
            except Exception:
                continue
            for row in rows:
                result[row.symbol] = {
                    "market_cap_yi": row.market_cap_yi,
                    "turnover_rate": row.turnover_rate,
                    "volume_ratio": None,
                    "intraday_average_price": None,
                }
        self._enrichment = result
        self._enrichment_observed_at = now
        return result

    def _twenty_day_limit_count(self, symbol: str, as_of: date) -> int | None:
        try:
            bars = self.bar_repository.latest(symbol, limit=20, cutoff=None)
        except Exception:
            return None
        if len(bars) < 20:
            return None
        count = 0
        for bar in bars:
            previous = bar.open if bar.open > 0 else bar.close
            if previous <= 0:
                continue
            rate = Decimal("0.2") if symbol.startswith(("300", "301", "688", "689")) else Decimal("0.1")
            if bar.close >= (previous * (Decimal(1) + rate) * Decimal("0.995")):
                count += 1
        return count

    def _volume_ratio(self, symbol: str, current_volume: Decimal) -> Decimal | None:
        try:
            bars = self.bar_repository.latest(symbol, limit=6, cutoff=None)
        except Exception:
            return None
        if len(bars) < 6 or current_volume < 0:
            return None
        baseline = sum((bar.volume for bar in bars[1:6]), Decimal("0")) / Decimal("5")
        if baseline <= 0:
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
        return LateSessionSelectionResponse(status="unavailable", trading_date=trading_date, server_time=now, phase=phase, refresh_interval_ms=1000, next_refresh_ms=1000, source_quality="unavailable", universe_count=0, quote_count=0, candidate_count=0, rules=(), data_state="no_market_data", no_data_reason=detail, behaviors=(), limitations=(detail,))
