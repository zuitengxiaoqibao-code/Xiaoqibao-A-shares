import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.market_sentiment import (
    HotspotSentimentInput,
    LiquidityBaseline,
    MarketFactorObservation,
    MarketBreadthObservation,
    MarketSentimentSnapshot,
    SentimentBand,
    SentimentComponent,
    SentimentPhase,
)


FORMULA_VERSION = "a-share-sentiment-v2"
MIN_SCORE_COVERAGE = Decimal("70")
HUNDRED = Decimal("100")
ZERO = Decimal("0")
SCORE_QUANTUM = Decimal("0.01")
WEIGHTS = {
    "volatility": Decimal("15"),
    "activity": Decimal("15"),
    "price_strength": Decimal("10"),
    "risk_appetite": Decimal("10"),
    "breadth": Decimal("15"),
    "limit_ecology": Decimal("15"),
    "money_making": Decimal("10"),
    "sector_diffusion": Decimal("5"),
    "style_risk_preference": Decimal("5"),
}
FACTOR_LABELS = {
    "volatility": "波动率情绪",
    "activity": "成交活跃度",
    "price_strength": "价格强度",
    "risk_appetite": "风险偏好",
    "breadth": "市场广度",
    "limit_ecology": "涨跌停情绪",
    "money_making": "赚钱效应",
    "sector_diffusion": "板块扩散情绪",
    "style_risk_preference": "风格风险偏好",
}
CHINA_TZ = ZoneInfo("Asia/Shanghai")
INTRADAY_FRESHNESS = timedelta(minutes=20)


class MarketSentimentWrongPhase(RuntimeError):
    pass


class MarketSentimentNotTradingDay(RuntimeError):
    pass


class MarketSentimentResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    trading_date: date
    phase: Literal["premarket", "intraday", "postclose"]
    display_mode: Literal[
        "current", "previous_close_baseline", "unavailable"
    ]
    current: MarketSentimentSnapshot | None
    previous_close: MarketSentimentSnapshot | None
    trajectory: tuple[MarketSentimentSnapshot, ...]


def _clamp(value: Decimal, lower: Decimal = ZERO, upper: Decimal = HUNDRED) -> Decimal:
    return max(lower, min(upper, value))


def _score(value: Decimal) -> Decimal:
    return _clamp(value).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def sentiment_band(value: Decimal | None) -> SentimentBand:
    if value is None:
        return "unavailable"
    if value < Decimal("20"):
        return "panic"
    if value < Decimal("40"):
        return "cold"
    if value < Decimal("60"):
        return "neutral"
    if value < Decimal("80"):
        return "active"
    return "overheated"


class MarketSentimentEvaluator:
    def evaluate(
        self,
        *,
        observation: MarketBreadthObservation,
        liquidity_baseline: LiquidityBaseline | None,
        hotspot: HotspotSentimentInput | None,
        factors: MarketFactorObservation | None = None,
        trading_date: date,
        phase: SentimentPhase,
        generated_at: datetime,
        previous_snapshot_id: str | None = None,
    ) -> MarketSentimentSnapshot:
        components = self._factor_components(
            observation, liquidity_baseline, factors or MarketFactorObservation(),
        )
        coverage = sum(
            item.weight * item.coverage_percent / HUNDRED for item in components
        ).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
        breadth_ready = observation.valid_count > 0
        value = self._total_score(components, coverage) if breadth_ready else None
        band = sentiment_band(value)
        quality = (
            "unavailable"
            if value is None
            else "ready" if coverage == HUNDRED else "partial"
        )
        drivers = self._drivers(observation, liquidity_baseline, hotspot, components)
        risks = self._risks(observation, value, coverage, breadth_ready, components)
        source_ids = tuple(dict.fromkeys((
            *observation.source_snapshot_ids,
            *(liquidity_baseline.evidence_ids if liquidity_baseline else ()),
            *(hotspot.evidence_ids if hotspot else ()),
        )))
        content = {
            "previous_snapshot_id": previous_snapshot_id,
            "trading_date": trading_date.isoformat(),
            "phase": phase,
            "quality": quality,
            "freshness": "current",
            "score": str(value) if value is not None else None,
            "band": band,
            "coverage_percent": str(coverage),
            "components": [item.model_dump(mode="json") for item in components],
            "drivers": drivers,
            "risks": risks,
            "beginner_guidance": self._guidance(band),
            "observed_at": observation.observed_at.isoformat(),
            "generated_at": generated_at.isoformat(),
            "source_snapshot_ids": source_ids,
            "formula_version": FORMULA_VERSION,
        }
        encoded = json.dumps(
            content, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        snapshot_id = f"sentiment-{hashlib.sha256(encoded).hexdigest()[:24]}"
        return MarketSentimentSnapshot(
            snapshot_id=snapshot_id,
            previous_snapshot_id=previous_snapshot_id,
            trading_date=trading_date,
            phase=phase,
            quality=quality,
            freshness="current",
            score=value,
            band=band,
            coverage_percent=coverage,
            components=components,
            drivers=drivers,
            risks=risks,
            beginner_guidance=self._guidance(band),
            observed_at=observation.observed_at,
            generated_at=generated_at,
            source_snapshot_ids=source_ids,
            formula_version=FORMULA_VERSION,
        )

    @staticmethod
    def _factor_components(
        observation: MarketBreadthObservation,
        baseline: LiquidityBaseline | None,
        factors: MarketFactorObservation,
    ) -> tuple[SentimentComponent, ...]:
        evidence = tuple(dict.fromkeys((*observation.source_snapshot_ids, *factors.evidence_ids)))
        relative_amount = factors.relative_amount
        if relative_amount is None and baseline and observation.total_amount_wan is not None:
            relative_amount = observation.total_amount_wan / baseline.amount_wan

        def ratio(numerator: int | None, denominator: int | None) -> Decimal | None:
            if numerator is None or denominator in (None, 0):
                return None
            return _score(Decimal(numerator) / Decimal(denominator) * HUNDRED)

        def average(values: list[Decimal]) -> tuple[Decimal | None, Decimal]:
            if not values:
                return None, ZERO
            return _score(sum(values, ZERO) / Decimal(len(values))), _score(
                Decimal(len(values)) / Decimal(3) * HUNDRED
            )

        volatility = None
        if factors.volatility_current_percent is not None and factors.volatility_baseline_percent:
            volatility = _score(
                Decimal("50")
                + (factors.volatility_baseline_percent - factors.volatility_current_percent)
                / factors.volatility_baseline_percent
                * HUNDRED
            )
        activity = (
            _score(Decimal("50") + (relative_amount - Decimal("1")) * HUNDRED)
            if relative_amount is not None else None
        )
        activity_coverage = (
            Decimal("100")
            if factors.relative_amount is not None or baseline is None or baseline.quality == "ready"
            else Decimal("80")
        )
        price_strength = ratio(factors.new_high_252_count, factors.effective_count)
        risk_appetite = None
        if (
            factors.benchmark_return_20d_percent is not None
            and factors.bond_etf_return_20d_percent is not None
        ):
            risk_appetite = _score(
                Decimal("50")
                + (factors.benchmark_return_20d_percent - factors.bond_etf_return_20d_percent)
                * Decimal("5")
            )

        breadth_parts = (
            (ratio(observation.rising_count, observation.valid_count), Decimal("0.40")),
            (ratio(factors.ma20_above_count, factors.effective_count), Decimal("0.35")),
            (ratio(factors.ma60_above_count, factors.effective_count), Decimal("0.25")),
        )
        breadth_ready = [(value, weight) for value, weight in breadth_parts if value is not None]
        breadth_weight = sum((weight for _, weight in breadth_ready), ZERO)
        breadth = (
            _score(sum((value * weight for value, weight in breadth_ready), ZERO) / breadth_weight)
            if breadth_ready else None
        )
        breadth_coverage = _score(breadth_weight * HUNDRED)

        limit_parts: list[tuple[Decimal, Decimal]] = []
        limit_total = observation.limit_up_count + observation.limit_down_count
        if limit_total:
            limit_parts.append((
                _score(Decimal(observation.limit_up_count) / Decimal(max(observation.limit_down_count, 1)) * HUNDRED),
                Decimal("0.40"),
            ))
        seal_total = observation.limit_up_count + observation.broken_limit_up_count
        if seal_total:
            broken_rate = Decimal(observation.broken_limit_up_count) / Decimal(seal_total) * HUNDRED
            limit_parts.append((_score(HUNDRED - broken_rate), Decimal("0.30")))
        if factors.yesterday_limit_up_return_percent is not None:
            limit_parts.append((
                _score(Decimal("50") + factors.yesterday_limit_up_return_percent * Decimal("5")),
                Decimal("0.30"),
            ))
        limit_weight = sum((weight for _, weight in limit_parts), ZERO)
        limit_ecology = (
            _score(sum((value * weight for value, weight in limit_parts), ZERO) / limit_weight)
            if limit_parts else None
        )
        limit_coverage = _score(limit_weight * HUNDRED / Decimal("1.00"))

        money_values = [
            ratio(factors.five_day_rising_count, factors.effective_count),
            (
                _score(HUNDRED - ratio(factors.sixty_day_new_low_count, factors.effective_count))
                if ratio(factors.sixty_day_new_low_count, factors.effective_count) is not None
                else None
            ),
        ]
        money_ready = [value for value in money_values if value is not None]
        money_making = (
            _score(sum(money_ready, ZERO) / Decimal(len(money_ready)))
            if money_ready else None
        )
        money_coverage = _score(Decimal(len(money_ready)) / Decimal("2") * HUNDRED)

        sector_diffusion = ratio(
            factors.rising_industry_count, factors.effective_industry_count,
        )
        style_risk_preference = None
        if (
            factors.small_cap_return_5d_percent is not None
            and factors.large_cap_return_5d_percent is not None
        ):
            style_risk_preference = _score(
                Decimal("50")
                + (factors.small_cap_return_5d_percent - factors.large_cap_return_5d_percent)
                * Decimal("5")
            )

        metrics = {
            "volatility": {
                "current_volatility_percent": factors.volatility_current_percent,
                "baseline_volatility_percent": factors.volatility_baseline_percent,
            },
            "activity": {
                "relative_amount": relative_amount,
                "total_amount_wan": observation.total_amount_wan,
                "baseline_amount_wan": baseline.amount_wan if baseline else None,
            },
            "price_strength": {
                "new_high_252_count": factors.new_high_252_count,
                "effective_count": factors.effective_count,
            },
            "risk_appetite": {
                "benchmark_return_20d_percent": factors.benchmark_return_20d_percent,
                "bond_etf_return_20d_percent": factors.bond_etf_return_20d_percent,
            },
            "breadth": {
                "rising_count": observation.rising_count,
                "valid_count": observation.valid_count,
                "ma20_above_count": factors.ma20_above_count,
                "ma60_above_count": factors.ma60_above_count,
            },
            "limit_ecology": {
                "limit_up_count": observation.limit_up_count,
                "limit_down_count": observation.limit_down_count,
                "broken_limit_up_count": observation.broken_limit_up_count,
                "yesterday_limit_up_return_percent": factors.yesterday_limit_up_return_percent,
            },
            "money_making": {
                "five_day_rising_count": factors.five_day_rising_count,
            "sixty_day_new_low_count": factors.sixty_day_new_low_count,
                "effective_count": factors.effective_count,
            },
            "sector_diffusion": {
                "rising_industry_count": factors.rising_industry_count,
                "effective_industry_count": factors.effective_industry_count,
            },
            "style_risk_preference": {
                "small_cap_return_5d_percent": factors.small_cap_return_5d_percent,
                "large_cap_return_5d_percent": factors.large_cap_return_5d_percent,
            },
        }
        values = (
            ("volatility", volatility, HUNDRED),
            ("activity", activity, activity_coverage),
            ("price_strength", price_strength, HUNDRED if price_strength is not None else ZERO),
            ("risk_appetite", risk_appetite, HUNDRED if risk_appetite is not None else ZERO),
            ("breadth", breadth, breadth_coverage),
            ("limit_ecology", limit_ecology, limit_coverage),
            ("money_making", money_making, money_coverage),
            ("sector_diffusion", sector_diffusion, HUNDRED if sector_diffusion is not None else ZERO),
            ("style_risk_preference", style_risk_preference, HUNDRED if style_risk_preference is not None else ZERO),
        )
        return tuple(
            SentimentComponent(
                name=name,
                score=score,
                weight=WEIGHTS[name],
                coverage_percent=coverage if score is not None else ZERO,
                metrics=metrics[name],
                evidence_ids=evidence,
            )
            for name, score, coverage in values
        )

    @staticmethod
    def _breadth(observation: MarketBreadthObservation) -> SentimentComponent:
        coverage = (
            Decimal(observation.valid_count)
            / Decimal(observation.requested_count)
            * HUNDRED
        )
        if observation.valid_count == 0 or observation.median_change_percent is None:
            value = None
        else:
            advance = (
                Decimal(observation.rising_count)
                + Decimal(observation.flat_count) * Decimal("0.5")
            ) / Decimal(observation.valid_count) * HUNDRED
            median = _clamp(
                Decimal("50")
                + observation.median_change_percent * Decimal("12.5")
            )
            value = _score(advance * Decimal("0.70") + median * Decimal("0.30"))
        return SentimentComponent(
            name="breadth",
            score=value,
            weight=WEIGHTS["breadth"],
            coverage_percent=_score(coverage),
            metrics={
                "requested_count": observation.requested_count,
                "valid_count": observation.valid_count,
                "rising_count": observation.rising_count,
                "falling_count": observation.falling_count,
                "flat_count": observation.flat_count,
                "median_change_percent": observation.median_change_percent,
            },
            evidence_ids=observation.source_snapshot_ids,
        )

    @staticmethod
    def _limit_ecology(observation: MarketBreadthObservation) -> SentimentComponent:
        quote_coverage = (
            Decimal(observation.valid_count)
            / Decimal(observation.requested_count)
            * HUNDRED
        )
        subcoverage = HUNDRED if observation.max_limit_streak is not None else Decimal("85")
        coverage = quote_coverage * subcoverage / HUNDRED
        if observation.valid_count == 0:
            value = None
        else:
            limit_total = observation.limit_up_count + observation.limit_down_count
            balance = (
                Decimal("50")
                if limit_total == 0
                else _clamp(
                    Decimal("50")
                    + Decimal("50")
                    * Decimal(observation.limit_up_count - observation.limit_down_count)
                    / Decimal(limit_total)
                )
            )
            seal_total = observation.limit_up_count + observation.broken_limit_up_count
            seal = (
                Decimal("50")
                if seal_total == 0
                else Decimal(observation.limit_up_count) / Decimal(seal_total) * HUNDRED
            )
            weighted = balance * Decimal("0.55") + seal * Decimal("0.30")
            available_weight = Decimal("0.85")
            if observation.max_limit_streak is not None:
                streak = _clamp(
                    Decimal("40")
                    + Decimal(observation.max_limit_streak - 1) * Decimal("15")
                )
                weighted += streak * Decimal("0.15")
                available_weight += Decimal("0.15")
            value = _score(weighted / available_weight)
        return SentimentComponent(
            name="limit_ecology",
            score=value,
            weight=WEIGHTS["limit_ecology"],
            coverage_percent=_score(coverage),
            metrics={
                "limit_up_count": observation.limit_up_count,
                "limit_down_count": observation.limit_down_count,
                "broken_limit_up_count": observation.broken_limit_up_count,
                "max_limit_streak": observation.max_limit_streak,
            },
            evidence_ids=observation.source_snapshot_ids,
        )

    @staticmethod
    def _liquidity(
        observation: MarketBreadthObservation,
        baseline: LiquidityBaseline | None,
    ) -> SentimentComponent:
        quote_coverage = (
            Decimal(observation.valid_count)
            / Decimal(observation.requested_count)
            * HUNDRED
        )
        if baseline is None or observation.total_amount_wan is None:
            coverage = ZERO
            value = None
            evidence_ids = ()
            ratio = None
        else:
            baseline_coverage = HUNDRED if baseline.quality == "ready" else Decimal("80")
            coverage = quote_coverage * baseline_coverage / HUNDRED
            ratio = observation.total_amount_wan / baseline.amount_wan
            value = _score(Decimal("50") + (ratio - Decimal("1")) * HUNDRED)
            evidence_ids = baseline.evidence_ids
        return SentimentComponent(
            name="liquidity",
            score=value,
            weight=Decimal("15"),
            coverage_percent=_score(coverage),
            metrics={
                "total_amount_wan": observation.total_amount_wan,
                "baseline_amount_wan": baseline.amount_wan if baseline else None,
                "relative_amount": ratio,
                "baseline_sample_size": baseline.sample_size if baseline else None,
            },
            evidence_ids=tuple(dict.fromkeys((*observation.source_snapshot_ids, *evidence_ids))),
        )

    @staticmethod
    def _hotspot(hotspot: HotspotSentimentInput | None) -> SentimentComponent:
        if hotspot is None:
            return SentimentComponent(
                name="hotspot", score=None, weight=Decimal("5"),
                coverage_percent=ZERO, metrics={}, evidence_ids=(),
            )
        theme = _clamp(Decimal(hotspot.unique_theme_count) / Decimal("10") * HUNDRED)
        symbols = _clamp(
            Decimal(hotspot.affected_symbol_count) / Decimal("60") * HUNDRED
        )
        persistence = _clamp(
            Decimal(hotspot.persistent_theme_count) / Decimal("5") * HUNDRED
        )
        concentration = _clamp(
            HUNDRED
            - max(ZERO, hotspot.largest_theme_share_percent - Decimal("35"))
            * Decimal("2")
        )
        value = _score(
            theme * Decimal("0.25")
            + symbols * Decimal("0.35")
            + persistence * Decimal("0.25")
            + concentration * Decimal("0.15")
        )
        return SentimentComponent(
            name="hotspot", score=value, weight=Decimal("5"),
            coverage_percent=HUNDRED,
            metrics={
                "unique_theme_count": hotspot.unique_theme_count,
                "affected_symbol_count": hotspot.affected_symbol_count,
                "persistent_theme_count": hotspot.persistent_theme_count,
                "largest_theme_share_percent": hotspot.largest_theme_share_percent,
            },
            evidence_ids=hotspot.evidence_ids,
        )

    @staticmethod
    def _total_score(
        components: tuple[SentimentComponent, ...], coverage: Decimal
    ) -> Decimal | None:
        if coverage < MIN_SCORE_COVERAGE:
            return None
        weighted = ZERO
        effective_weight = ZERO
        for component in components:
            if component.score is None or component.coverage_percent == ZERO:
                continue
            weight = component.weight * component.coverage_percent / HUNDRED
            weighted += component.score * weight
            effective_weight += weight
        return _score(weighted / effective_weight) if effective_weight else None

    @staticmethod
    def _drivers(
        observation: MarketBreadthObservation,
        baseline: LiquidityBaseline | None,
        hotspot: HotspotSentimentInput | None,
        components: tuple[SentimentComponent, ...] = (),
    ) -> tuple[str, ...]:
        values = []
        if observation.valid_count:
            rise_ratio = Decimal(observation.rising_count) / Decimal(observation.valid_count)
            if rise_ratio >= Decimal("0.6"):
                values.append("上涨股票覆盖扩大")
        if observation.median_change_percent is not None and observation.median_change_percent > 1:
            values.append("全市场涨跌幅中位数偏强")
        if observation.limit_up_count > observation.limit_down_count * 2:
            values.append("涨停数量明显多于跌停")
        if baseline and observation.total_amount_wan is not None:
            if observation.total_amount_wan / baseline.amount_wan >= Decimal("1.2"):
                values.append("成交额较同阶段基线放大")
        if hotspot and hotspot.persistent_theme_count:
            values.append("已核验热点出现跨阶段延续")
        for component in components:
            if component.score is not None and component.score >= Decimal("70"):
                values.append(f"{FACTOR_LABELS.get(component.name, component.name)}分项偏强")
        return tuple(values[:3])

    @staticmethod
    def _risks(
        observation: MarketBreadthObservation,
        value: Decimal | None,
        coverage: Decimal,
        breadth_ready: bool,
        components: tuple[SentimentComponent, ...] = (),
    ) -> tuple[str, ...]:
        values = []
        if not breadth_ready:
            values.append("市场宽度不可用")
        if coverage < MIN_SCORE_COVERAGE:
            values.append("有效数据覆盖不足 70%")
        elif coverage < HUNDRED:
            values.append("部分组件数据不可用，分数仅供阶段观察")
        if value is not None and value >= Decimal("80"):
            values.append("市场情绪过热，追高和分歧风险上升")
        seal_total = observation.limit_up_count + observation.broken_limit_up_count
        if seal_total and Decimal(observation.broken_limit_up_count) / Decimal(seal_total) >= Decimal("0.3"):
            values.append("炸板率较高，强势股分歧增加")
        if observation.limit_down_count > observation.limit_up_count:
            values.append("跌停数量多于涨停，风险释放仍在继续")
        for component in components:
            if component.score is not None and component.score < Decimal("35"):
                values.append(f"{FACTOR_LABELS.get(component.name, component.name)}分项偏弱")
        return tuple(values[:3])

    @staticmethod
    def _guidance(band: SentimentBand) -> str:
        return {
            "panic": "市场处于恐慌区，优先观察风险是否停止扩散。",
            "cold": "市场情绪低迷，等待宽度和成交活跃度修复。",
            "neutral": "市场方向不清，等待量价和热点形成一致信号。",
            "active": "市场较活跃，可观察强势方向，但仍需量价确认。",
            "overheated": "市场情绪过热，不要把高分理解为低风险，避免盲目追高。",
            "unavailable": "核心数据不足，等待来源恢复后再判断市场情绪。",
        }[band]


class MarketSentimentFactorBuilder:
    """Build the nine-factor raw inputs from verified daily bars."""

    BENCHMARK_SYMBOLS = {"000852", "000300", "511010"}

    def __init__(self, *, bar_repository=None, classification_repository=None) -> None:
        self.bar_repository = bar_repository
        self.classification_repository = classification_repository

    def build(self, *, as_of: date, cutoff: datetime | None = None) -> MarketFactorObservation:
        if self.bar_repository is None:
            return MarketFactorObservation()
        symbols = self.bar_repository.symbols_with_history(60, as_of, cutoff=cutoff)
        histories = self.bar_repository.latest_many(symbols, 252, as_of, cutoff=cutoff)
        industries = {}
        if self.classification_repository is not None:
            for symbol in symbols:
                snapshot = self.classification_repository.latest(symbol, as_of, cutoff=cutoff)
                if snapshot is not None and snapshot.shenwan_industry is not None:
                    industries[symbol] = snapshot.shenwan_industry.name
        return self.from_histories(histories, industry_by_symbol=industries)

    @classmethod
    def from_histories(
        cls,
        histories: Mapping[str, Sequence[DailyBar]],
        *,
        industry_by_symbol: Mapping[str, str] | None = None,
    ) -> MarketFactorObservation:
        stock_histories = {
            symbol: sorted(bars, key=lambda item: item.trade_date)
            for symbol, bars in histories.items()
            if symbol not in cls.BENCHMARK_SYMBOLS
        }
        eligible = {
            symbol: bars for symbol, bars in stock_histories.items() if len(bars) >= 60
        }
        effective_count = len(eligible) or None

        ma20_count = sum(
            bars[-1].close > sum((item.close for item in bars[-20:]), ZERO) / Decimal("20")
            for bars in eligible.values()
            if len(bars) >= 20
        )
        ma60_count = sum(
            bars[-1].close > sum((item.close for item in bars[-60:]), ZERO) / Decimal("60")
            for bars in eligible.values()
        )
        five_day_rising_count = sum(
            bars[-1].close > bars[-6].close for bars in eligible.values() if len(bars) >= 6
        )
        sixty_day_new_low_count = sum(
            bars[-1].close <= min(item.close for item in bars[-60:])
            for bars in eligible.values()
        )
        new_high_252_count = sum(
            len(bars) >= 252 and bars[-1].close >= max(item.close for item in bars[-252:])
            for bars in stock_histories.values()
        )
        yesterday_limit_up_returns = []
        for symbol, bars in eligible.items():
            if len(bars) < 3:
                continue
            previous_return = bars[-2].close / bars[-3].close - Decimal("1")
            limit_threshold = Decimal("0.195") if symbol.startswith(("300", "301", "688", "689")) else Decimal("0.095")
            if previous_return >= limit_threshold:
                yesterday_limit_up_returns.append(bars[-1].close / bars[-2].close - Decimal("1"))

        current_vols = []
        baseline_vols = []
        for bars in eligible.values():
            if len(bars) < 61:
                continue
            current_returns = [
                bars[-index].close / bars[-index - 1].close - Decimal("1")
                for index in range(1, 21)
            ]
            baseline_returns = [
                bars[-index].close / bars[-index - 1].close - Decimal("1")
                for index in range(21, 41)
            ]
            current_vols.append(cls._annualized_volatility(current_returns))
            baseline_vols.append(cls._annualized_volatility(baseline_returns))

        benchmark = histories.get("000852", ())
        large_cap = histories.get("000300", ())
        bond = histories.get("511010", ())
        return MarketFactorObservation(
            volatility_current_percent=cls._mean(current_vols),
            volatility_baseline_percent=cls._mean(baseline_vols),
            new_high_252_count=new_high_252_count,
            effective_count=effective_count,
            benchmark_return_20d_percent=cls._return_percent(benchmark, 20),
            bond_etf_return_20d_percent=cls._return_percent(bond, 20),
            ma20_above_count=ma20_count,
            ma60_above_count=ma60_count,
            five_day_rising_count=five_day_rising_count,
            sixty_day_new_low_count=sixty_day_new_low_count,
            rising_industry_count=cls._rising_industry_count(eligible, industry_by_symbol or {}),
            effective_industry_count=cls._industry_count(industry_by_symbol or {}),
            small_cap_return_5d_percent=cls._return_percent(benchmark, 5),
            large_cap_return_5d_percent=cls._return_percent(large_cap, 5),
            yesterday_limit_up_return_percent=(
                cls._mean(yesterday_limit_up_returns) * HUNDRED
                if yesterday_limit_up_returns else None
            ),
            evidence_ids=("daily-bars",) if eligible else (),
        )

    @staticmethod
    def _return_percent(bars: Sequence[DailyBar], days: int) -> Decimal | None:
        if len(bars) <= days:
            return None
        return (bars[-1].close / bars[-1 - days].close - Decimal("1")) * HUNDRED

    @staticmethod
    def _annualized_volatility(values: Sequence[Decimal]) -> Decimal:
        if not values:
            return ZERO
        mean = sum(values, ZERO) / Decimal(len(values))
        variance = sum(((value - mean) ** 2 for value in values), ZERO) / Decimal(len(values))
        return variance.sqrt() * Decimal("252").sqrt() * HUNDRED

    @staticmethod
    def _mean(values: Sequence[Decimal]) -> Decimal | None:
        return sum(values, ZERO) / Decimal(len(values)) if values else None

    @staticmethod
    def _industry_count(industries: Mapping[str, str]) -> int | None:
        values = {value for value in industries.values() if value}
        return len(values) or None

    @staticmethod
    def _rising_industry_count(
        histories: Mapping[str, Sequence[DailyBar]], industries: Mapping[str, str]
    ) -> int | None:
        grouped: dict[str, list[Decimal]] = defaultdict(list)
        for symbol, bars in histories.items():
            industry = industries.get(symbol)
            if industry and len(bars) >= 2:
                grouped[industry].append(bars[-1].close / bars[-2].close - Decimal("1"))
        if not grouped:
            return None
        return sum(
            sum(values, ZERO) / Decimal(len(values)) > 0
            for values in grouped.values()
        )


class MarketSentimentService:
    def __init__(
        self,
        *,
        repository,
        source,
        evaluator: MarketSentimentEvaluator,
        trading_calendar,
        news_repository=None,
        factor_builder: MarketSentimentFactorBuilder | None = None,
    ) -> None:
        self.repository = repository
        self.source = source
        self.evaluator = evaluator
        self.trading_calendar = trading_calendar
        self.news_repository = news_repository
        self.factor_builder = factor_builder

    def refresh(self, now: datetime) -> MarketSentimentSnapshot:
        local_now = self._local_now(now)
        trading_date = local_now.date()
        self._require_trading_day(trading_date)
        phase = self._phase(local_now)
        if phase == "premarket":
            raise MarketSentimentWrongPhase(
                "market sentiment cannot refresh before the A-share session"
            )
        previous = self.repository.latest(cutoff=now)
        result = self.source.fetch(cutoff=now)
        baseline = self.repository.liquidity_baseline(
            phase=phase,
            before_trading_date=trading_date,
            formula_version=FORMULA_VERSION,
        )
        hotspot = self._hotspot_input(now, trading_date)
        factors = (
            self.factor_builder.build(as_of=trading_date, cutoff=now)
            if self.factor_builder is not None else None
        )
        snapshot = self.evaluator.evaluate(
            observation=result.observation,
            liquidity_baseline=baseline,
            hotspot=hotspot,
            factors=factors,
            trading_date=trading_date,
            phase=phase,
            generated_at=now,
            previous_snapshot_id=(
                previous.snapshot_id if previous is not None else None
            ),
        )
        self.repository.append(snapshot, result.raw_batches)
        return snapshot

    def current(self, now: datetime) -> MarketSentimentResponse:
        local_now = self._local_now(now)
        trading_date = local_now.date()
        if not self.trading_calendar.is_trading_day(trading_date):
            return self._nontrading_response(now, trading_date)
        phase = self._phase(local_now)
        previous_close = self._stale(
            self.repository.previous_postclose(
                trading_date, formula_version=FORMULA_VERSION
            )
        )
        trajectory = self.repository.trajectory(
            trading_date, cutoff=now, formula_version=FORMULA_VERSION
        )
        current = None
        if phase in {"intraday", "postclose"}:
            current = self.repository.latest(
                trading_date=trading_date,
                phase=phase,
                cutoff=now,
                formula_version=FORMULA_VERSION,
            )
            current = self._with_freshness(current, now)
        if current is not None:
            display_mode = "current"
        elif phase == "premarket" and previous_close is not None:
            display_mode = "previous_close_baseline"
        else:
            display_mode = "unavailable"
        current_id = current.snapshot_id if current is not None else None
        displayed_trajectory = tuple(
            item
            if item.snapshot_id == current_id
            else item.model_copy(update={"freshness": "stale"})
            for item in trajectory
        )
        return MarketSentimentResponse(
            trading_date=trading_date,
            phase=phase,
            display_mode=display_mode,
            current=current,
            previous_close=previous_close,
            trajectory=displayed_trajectory,
        )

    def _nontrading_response(
        self, now: datetime, calendar_date: date
    ) -> MarketSentimentResponse:
        previous_close = self._stale(
            self.repository.latest(
                phase="postclose", cutoff=now, formula_version=FORMULA_VERSION
            )
        )
        if previous_close is None:
            return MarketSentimentResponse(
                trading_date=calendar_date,
                phase="postclose",
                display_mode="unavailable",
                current=None,
                previous_close=None,
                trajectory=(),
            )
        trajectory = tuple(
            item.model_copy(update={"freshness": "stale"})
            for item in self.repository.trajectory(
                previous_close.trading_date,
                cutoff=now,
                formula_version=FORMULA_VERSION,
            )
        )
        return MarketSentimentResponse(
            trading_date=previous_close.trading_date,
            phase="postclose",
            display_mode="previous_close_baseline",
            current=None,
            previous_close=previous_close,
            trajectory=trajectory,
        )

    def history(
        self, trading_date: date
    ) -> tuple[MarketSentimentSnapshot, ...]:
        self._require_trading_day(trading_date)
        return self.repository.trajectory(
            trading_date, formula_version=FORMULA_VERSION
        )

    def _hotspot_input(
        self, cutoff: datetime, trading_date: date
    ) -> HotspotSentimentInput | None:
        if self.news_repository is None:
            return None
        events = self.news_repository.effective_events(cutoff=cutoff)
        selected = []
        for event in events:
            if (
                getattr(event, "event_type", None) != "market_hotspot"
                or getattr(event, "review_state", None) != "verified"
                or event.occurred_at > cutoff
                or event.normalized_at > cutoff
                or event.occurred_at.astimezone(CHINA_TZ).date() != trading_date
            ):
                continue
            selected.append(event)
        if not selected:
            return None

        theme_symbols: dict[str, set[str]] = defaultdict(set)
        theme_observations: dict[str, set[datetime]] = defaultdict(set)
        affected_symbols: set[str] = set()
        evidence_ids: list[str] = []
        for event in selected:
            symbols = {
                str(code)
                for asset, code in event.affected_instruments
                if self._asset_value(asset) == "a_share"
            }
            if not symbols:
                continue
            affected_symbols.update(symbols)
            evidence_ids.append(event.event_id)
            for theme in event.themes:
                if not theme:
                    continue
                theme_symbols[theme].update(symbols)
                theme_observations[theme].add(event.normalized_at)
        if not theme_symbols or not affected_symbols:
            return None
        largest = max(len(symbols) for symbols in theme_symbols.values())
        concentration = (
            Decimal(largest)
            / Decimal(len(affected_symbols))
            * HUNDRED
        ).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
        return HotspotSentimentInput(
            unique_theme_count=len(theme_symbols),
            affected_symbol_count=len(affected_symbols),
            persistent_theme_count=sum(
                len(observations) >= 2
                for observations in theme_observations.values()
            ),
            largest_theme_share_percent=concentration,
            evidence_ids=tuple(dict.fromkeys(evidence_ids)),
        )

    def _with_freshness(
        self, snapshot: MarketSentimentSnapshot | None, now: datetime
    ) -> MarketSentimentSnapshot | None:
        if snapshot is None:
            return None
        is_stale = (
            snapshot.phase == "intraday"
            and now.astimezone(CHINA_TZ)
            - snapshot.generated_at.astimezone(CHINA_TZ)
            > INTRADAY_FRESHNESS
        )
        return snapshot.model_copy(
            update={"freshness": "stale" if is_stale else "current"}
        )

    @staticmethod
    def _stale(
        snapshot: MarketSentimentSnapshot | None,
    ) -> MarketSentimentSnapshot | None:
        return (
            snapshot.model_copy(update={"freshness": "stale"})
            if snapshot is not None
            else None
        )

    @staticmethod
    def _asset_value(asset) -> str:
        return str(getattr(asset, "value", asset))

    def _require_trading_day(self, trading_date: date) -> None:
        if not self.trading_calendar.is_trading_day(trading_date):
            raise MarketSentimentNotTradingDay(
                f"{trading_date.isoformat()} is not a confirmed A-share trading day"
            )

    @staticmethod
    def _local_now(now: datetime) -> datetime:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must include a timezone")
        return now.astimezone(CHINA_TZ)

    @staticmethod
    def _phase(
        local_now: datetime,
    ) -> Literal["premarket", "intraday", "postclose"]:
        if local_now.time() < time(9, 30):
            return "premarket"
        if local_now.time() < time(15, 0):
            return "intraday"
        return "postclose"
