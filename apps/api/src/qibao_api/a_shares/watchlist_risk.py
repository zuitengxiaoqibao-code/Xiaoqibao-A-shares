from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from math import sqrt
from statistics import pstdev

from qibao_api.contracts.watchlist_risk import (
    WatchlistConcentration,
    WatchlistCorrelation,
    WatchlistRiskItem,
    WatchlistRiskResponse,
)
from qibao_api.contracts.instruments import validate_a_share_code


def _returns(bars) -> dict[date, float]:
    ordered = sorted(bars, key=lambda item: item.trade_date)
    values = {}
    for previous, current in zip(ordered, ordered[1:]):
        if previous.close and previous.close > 0:
            values[current.trade_date] = float(current.close / previous.close - 1)
    return values


def _correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) < 20 or len(left) != len(right):
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    covariance = sum((a - left_mean) * (b - right_mean) for a, b in zip(left, right))
    left_scale = sqrt(sum((a - left_mean) ** 2 for a in left))
    right_scale = sqrt(sum((b - right_mean) ** 2 for b in right))
    if left_scale == 0 or right_scale == 0:
        return None
    return covariance / (left_scale * right_scale)


class WatchlistRiskService:
    def __init__(self, directory, bar_repository) -> None:
        self.directory = directory
        self.bar_repository = bar_repository

    def analyze(
        self,
        symbols: tuple[str, ...],
        *,
        as_of: date,
        observed_at: datetime,
    ) -> WatchlistRiskResponse:
        validated = tuple(validate_a_share_code(symbol) for symbol in symbols)
        if len(set(validated)) != len(validated):
            raise ValueError("观察篮子中的 A 股代码不能重复")
        bars_by_symbol = self.bar_repository.latest_many(
            list(validated), limit=61, as_of=as_of
        )
        return_series = {symbol: _returns(bars_by_symbol.get(symbol, ())) for symbol in validated}
        items = []
        industries: dict[str, list[str]] = defaultdict(list)
        themes: dict[str, list[str]] = defaultdict(list)
        sources = set()
        for symbol in validated:
            identity = self.directory.resolve(symbol)
            series = return_series[symbol]
            usable = list(series.values())[-20:]
            limitations = []
            if identity is None:
                limitations.append("本地证券目录缺少名称与行业身份")
            if len(usable) < 20:
                limitations.append(f"日收益样本不足 20 个，当前 {len(usable)} 个")
            for bar in bars_by_symbol.get(symbol, ()):
                sources.add(bar.source)
            volatility = (
                Decimal(str(round(pstdev(usable) * sqrt(250) * 100, 2)))
                if len(usable) >= 20 else None
            )
            if identity and identity.industry:
                industries[identity.industry].append(symbol)
            if identity:
                for sector in identity.sectors:
                    themes[sector].append(symbol)
            items.append(WatchlistRiskItem(
                symbol=symbol,
                name=identity.name if identity is not None else symbol,
                industry=identity.industry if identity is not None else None,
                sectors=identity.sectors if identity is not None else (),
                volatility_20d_percent=volatility,
                return_sample_count=len(series),
                status="ready" if not limitations else "partial" if series or identity else "unavailable",
                limitations=tuple(limitations),
            ))
        ready_count = sum(item.status == "ready" for item in items)
        valid_count = sum(item.status != "unavailable" for item in items)
        pairs = []
        for index, left_symbol in enumerate(validated):
            for right_symbol in validated[index + 1:]:
                overlap = sorted(set(return_series[left_symbol]) & set(return_series[right_symbol]))[-60:]
                value = _correlation(
                    [return_series[left_symbol][day] for day in overlap],
                    [return_series[right_symbol][day] for day in overlap],
                )
                if value is not None and abs(value) >= 0.7:
                    pairs.append(WatchlistCorrelation(
                        left_symbol=left_symbol,
                        right_symbol=right_symbol,
                        correlation=Decimal(str(round(value, 3))),
                        overlap_days=len(overlap),
                    ))
        def concentration(groups) -> tuple[WatchlistConcentration, ...]:
            return tuple(
                WatchlistConcentration(
                    label=label,
                    symbol_count=len(members),
                    observation_weight_percent=Decimal(str(round(len(members) / len(validated) * 100, 2))),
                    symbols=tuple(sorted(members)),
                )
                for label, members in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
            )
        warnings = []
        if any(len(members) / len(validated) >= 0.5 for members in industries.values()):
            warnings.append("观察篮子行业集中度达到 50% 或以上")
        if pairs:
            warnings.append("观察篮子存在绝对相关系数不低于 0.70 的股票组合")
        if valid_count < len(validated):
            warnings.append("部分标的缺少足够真实日线或身份数据")
        status = "ready" if ready_count == len(validated) else "partial" if valid_count else "unavailable"
        return WatchlistRiskResponse(
            status=status,
            as_of=as_of,
            observed_at=observed_at,
            valid_count=valid_count,
            total_count=len(validated),
            coverage_percent=Decimal(str(round(valid_count / len(validated) * 100, 2))),
            items=tuple(items),
            industries=concentration(industries),
            themes=concentration(themes),
            high_correlation_pairs=tuple(sorted(pairs, key=lambda item: abs(item.correlation), reverse=True)),
            warnings=tuple(warnings),
            sources=tuple(sorted(sources)),
        )
