"""Portfolio-level concentration and correlation risk from verified local evidence."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import sqrt
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Callable, Sequence

from qibao_api.a_shares.data_quality import assess_bar_series
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.portfolio_risk import (
    CorrelationPair,
    IndustryConcentration,
    PortfolioPositionInput,
    PortfolioPositionRisk,
    PortfolioRiskResponse,
    PortfolioStressScenario,
)


TWO = Decimal("0.01")
FOUR = Decimal("0.0001")
REGIME_POSITION_CAPS = {
    "情绪主升": Decimal("100"),
    "指数权重进攻": Decimal("80"),
    "轮动震荡": Decimal("50"),
    "冰点修复": Decimal("40"),
    "高位退潮": Decimal("20"),
    "缩量混沌": Decimal("20"),
}


class PortfolioRiskStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS portfolio_positions (
                    symbol TEXT PRIMARY KEY,
                    shares TEXT NOT NULL,
                    cost_price TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def current(self) -> tuple[PortfolioPositionInput, ...]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT symbol, shares, cost_price FROM portfolio_positions ORDER BY symbol"
            ).fetchall()
        return tuple(
            PortfolioPositionInput(
                symbol=row["symbol"],
                shares=Decimal(row["shares"]),
                cost_price=Decimal(row["cost_price"]),
            )
            for row in rows
        )

    def upsert(self, position: PortfolioPositionInput) -> PortfolioPositionInput:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT INTO portfolio_positions (symbol, shares, cost_price, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    shares = excluded.shares,
                    cost_price = excluded.cost_price,
                    updated_at = excluded.updated_at
                """,
                (
                    position.symbol,
                    str(position.shares),
                    str(position.cost_price),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        return position

    def delete(self, symbol: str) -> bool:
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM portfolio_positions WHERE symbol = ?",
                (symbol,),
            )
        return cursor.rowcount > 0


class PortfolioRiskService:
    def __init__(self, bar_repository, enrichment_repository, *, clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> None:
        self.bar_repository = bar_repository
        self.enrichment_repository = enrichment_repository
        self.clock = clock

    def analyze(
        self,
        positions: Sequence[PortfolioPositionInput],
        *,
        as_of: date,
        market_regime: str | None,
    ) -> PortfolioRiskResponse:
        symbols = [position.symbol for position in positions]
        if len(set(symbols)) != len(symbols):
            raise ValueError("组合股票代码不能重复")
        if not positions:
            return PortfolioRiskResponse(
                status="unavailable",
                as_of=as_of,
                observed_at=self.clock(),
                warnings=("尚未录入真实持仓，组合风险暂不计算",),
            )
        history = self.bar_repository.latest_many(symbols, 61, as_of)
        rows: list[PortfolioPositionRisk] = []
        sources: list[str] = []
        quality_warnings: list[str] = []
        industry_values: dict[str, Decimal] = {}
        industry_symbols: dict[str, list[str]] = {}
        industry_missing = False
        usable_history: dict[str, list[DailyBar]] = {}

        provisional: list[
            tuple[PortfolioPositionInput, DailyBar | None, str | None, tuple[str, ...]]
        ] = []
        for position in positions:
            bars = list(history.get(position.symbol, []))
            quality = assess_bar_series(bars)
            quality_details = tuple(dict.fromkeys(issue.detail for issue in quality.issues))
            if bars:
                sources.append(bars[-1].source)
            if quality.blocked:
                latest = None
                quality_warnings.append(
                    f"{position.symbol} 日线质量阻断：{'；'.join(quality_details)}"
                )
            else:
                latest = bars[-1] if bars else None
                usable_history[position.symbol] = bars
                for detail in quality_details:
                    quality_warnings.append(f"{position.symbol} 日线质量警告：{detail}")
            enrichment = self.enrichment_repository.latest(position.symbol)
            industry = getattr(enrichment, "industry_name", None) if enrichment is not None else None
            if enrichment is not None:
                sources.extend(getattr(enrichment, "sources", ()))
            if latest is not None and not industry:
                industry_missing = True
            provisional.append((position, latest, industry, quality_details if quality.blocked else ()))

        total_market_value = sum(
            (
                position.shares * latest.close
                for position, latest, _industry, _limitations in provisional
                if latest is not None
            ),
            Decimal("0"),
        )
        total_cost = sum(
            (
                position.shares * position.cost_price
                for position, latest, _industry, _limitations in provisional
                if latest is not None
            ),
            Decimal("0"),
        )
        for position, latest, industry, limitations in provisional:
            if latest is None:
                reason = limitations or ("缺少本地日线，无法取得当前价",)
                rows.append(PortfolioPositionRisk(
                    symbol=position.symbol, shares=position.shares, cost_price=position.cost_price,
                    industry=industry, status="unavailable", limitations=reason,
                ))
                continue
            market_value = position.shares * latest.close
            cost = position.shares * position.cost_price
            pnl = market_value - cost
            weight = market_value / total_market_value * Decimal("100") if total_market_value > 0 else None
            rows.append(PortfolioPositionRisk(
                symbol=position.symbol,
                shares=position.shares,
                cost_price=position.cost_price,
                current_price=_q(latest.close),
                market_value=_q(market_value),
                pnl=_q(pnl),
                pnl_percent=_q(pnl / cost * Decimal("100")) if cost > 0 else None,
                weight_percent=_q(weight) if weight is not None else None,
                industry=industry,
                status="ready",
            ))
            if industry:
                industry_values[industry] = industry_values.get(industry, Decimal("0")) + market_value
                industry_symbols.setdefault(industry, []).append(position.symbol)

        ready_rows = [row for row in rows if row.status == "ready" and row.market_value is not None]
        if not ready_rows or total_market_value <= 0:
            return PortfolioRiskResponse(
                status="unavailable", as_of=as_of, observed_at=self.clock(), positions=tuple(rows),
                warnings=tuple(quality_warnings) + ("组合股票缺少可用本地日线，无法计算组合风险",),
                sources=tuple(dict.fromkeys(sources)),
            )

        industries = tuple(sorted((
            IndustryConcentration(
                industry=industry,
                market_value=_q(value),
                weight_percent=_q(value / total_market_value * Decimal("100")),
                symbols=tuple(industry_symbols[industry]),
            )
            for industry, value in industry_values.items()
        ), key=lambda item: item.weight_percent, reverse=True))
        ready_symbols = [row.symbol for row in ready_rows]
        all_pairs = _correlation_pairs(usable_history, ready_symbols)
        high_pairs = tuple(pair for pair in all_pairs if pair.correlation >= Decimal("0.80"))
        average_correlation = (
            _q(sum((pair.correlation for pair in all_pairs), Decimal("0")) / Decimal(len(all_pairs)), places=FOUR)
            if all_pairs else None
        )
        hhi = _q(sum(
            ((row.weight_percent or Decimal("0")) ** 2 for row in ready_rows),
            Decimal("0"),
        ))
        total_pnl = total_market_value - total_cost
        warnings: list[str] = list(quality_warnings)
        if any((row.weight_percent or Decimal("0")) > Decimal("20") for row in ready_rows):
            warnings.append("存在单只股票权重超过 20%")
        if industries and industries[0].weight_percent > Decimal("35"):
            warnings.append("最大行业权重超过 35%")
        if average_correlation is not None and average_correlation > Decimal("0.65"):
            warnings.append("组合平均相关性超过 0.65")
        if industry_missing:
            warnings.append("部分股票缺少已核验行业，行业集中度不完整")
        if market_regime not in REGIME_POSITION_CAPS:
            warnings.append("市场风格不可用，不输出市场仓位上限")
        scenarios = _stress_scenarios(total_market_value, industries, high_pairs, rows)
        status = (
            "ready"
            if not industry_missing and len(ready_rows) == len(rows) and not quality_warnings
            else "partial"
        )
        return PortfolioRiskResponse(
            status=status,
            as_of=as_of,
            observed_at=self.clock(),
            total_market_value=_q(total_market_value),
            total_cost=_q(total_cost),
            total_pnl=_q(total_pnl),
            total_pnl_percent=_q(total_pnl / total_cost * Decimal("100")) if total_cost > 0 else None,
            hhi=hhi,
            average_correlation=average_correlation,
            market_regime=market_regime,
            market_position_cap_percent=REGIME_POSITION_CAPS.get(market_regime),
            positions=tuple(rows),
            industries=industries,
            high_correlation_pairs=high_pairs,
            stress_scenarios=scenarios,
            warnings=tuple(warnings),
            sources=tuple(dict.fromkeys(sources)),
        )


def _correlation_pairs(history: dict[str, list[DailyBar]], symbols: Sequence[str]) -> tuple[CorrelationPair, ...]:
    returns = {symbol: _returns_by_date(history.get(symbol, [])) for symbol in symbols}
    pairs: list[CorrelationPair] = []
    for left_index, left_symbol in enumerate(symbols):
        for right_symbol in symbols[left_index + 1:]:
            dates = sorted(set(returns[left_symbol]) & set(returns[right_symbol]))
            if len(dates) < 20:
                continue
            left = [returns[left_symbol][day] for day in dates]
            right = [returns[right_symbol][day] for day in dates]
            correlation = _pearson(left, right)
            if correlation is None:
                continue
            pairs.append(CorrelationPair(
                left_symbol=left_symbol,
                right_symbol=right_symbol,
                correlation=_q(Decimal(str(correlation)), places=FOUR),
                overlap_days=len(dates),
            ))
    return tuple(pairs)


def _returns_by_date(bars: Sequence[DailyBar]) -> dict[date, float]:
    ordered = sorted(bars, key=lambda item: item.trade_date)
    result: dict[date, float] = {}
    for previous, current in zip(ordered, ordered[1:]):
        if previous.close > 0:
            result[current.trade_date] = float(current.close / previous.close - 1)
    return result


def _pearson(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or not left:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denominator = sqrt(left_var * right_var)
    return numerator / denominator if denominator > 0 else None


def _stress_scenarios(
    total_market_value: Decimal,
    industries: Sequence[IndustryConcentration],
    high_pairs: Sequence[CorrelationPair],
    positions: Sequence[PortfolioPositionRisk],
) -> tuple[PortfolioStressScenario, ...]:
    values = {row.symbol: row.market_value for row in positions if row.market_value is not None}
    scenarios = [PortfolioStressScenario(
        key="market_down_2", label="全市场下跌 2%", shock_percent=Decimal("-2"),
        estimated_loss=_q(total_market_value * Decimal("-0.02")), status="ready",
        detail="对全部已计价持仓施加统一 -2% 机械冲击",
    )]
    if industries:
        largest = industries[0]
        scenarios.append(PortfolioStressScenario(
            key="largest_industry_down_5", label="最大行业下跌 5%", shock_percent=Decimal("-5"),
            estimated_loss=_q(largest.market_value * Decimal("-0.05")), status="ready",
            detail=f"{largest.industry} 权重最高，仅对该行业施加 -5% 冲击",
        ))
    else:
        scenarios.append(PortfolioStressScenario(
            key="largest_industry_down_5", label="最大行业下跌 5%", shock_percent=Decimal("-5"),
            status="unavailable", detail="缺少已核验行业，无法计算",
        ))
    if high_pairs:
        pair = max(high_pairs, key=lambda item: (values.get(item.left_symbol, Decimal("0")) or Decimal("0")) + (values.get(item.right_symbol, Decimal("0")) or Decimal("0")))
        pair_value = (values.get(pair.left_symbol, Decimal("0")) or Decimal("0")) + (values.get(pair.right_symbol, Decimal("0")) or Decimal("0"))
        scenarios.append(PortfolioStressScenario(
            key="correlated_pair_down_7", label="高相关股票对下跌 7%", shock_percent=Decimal("-7"),
            estimated_loss=_q(pair_value * Decimal("-0.07")), status="ready",
            detail=f"{pair.left_symbol}/{pair.right_symbol} 相关系数 {pair.correlation}",
        ))
    else:
        scenarios.append(PortfolioStressScenario(
            key="correlated_pair_down_7", label="高相关股票对下跌 7%", shock_percent=Decimal("-7"),
            status="unavailable", detail="没有重叠不少于 20 日且相关系数至少 0.80 的股票对",
        ))
    return tuple(scenarios)


def _q(value: Decimal, *, places: Decimal = TWO) -> Decimal:
    return value.quantize(places, rounding=ROUND_HALF_UP)
