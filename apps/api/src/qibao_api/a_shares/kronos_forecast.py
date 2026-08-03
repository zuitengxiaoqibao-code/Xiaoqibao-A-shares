import asyncio
from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from qibao_api.contracts.kronos_forecast import (
    KronosForecastPoint,
    KronosForecastResponse,
    KronosForecastSummary,
)
from qibao_api.contracts.bars import DailyBar
from qibao_api.a_shares.kronos_runtime import KronosUnavailableError


_PERCENT_QUANT = Decimal("0.01")


class KronosPathPredictor(Protocol):
    def predict_paths(
        self,
        bars: Sequence[DailyBar],
        future_dates: Sequence[date],
        sample_count: int,
    ) -> list[list[Decimal]]: ...


class KronosForecastService:
    def __init__(
        self,
        *,
        bar_repository,
        trading_calendar,
        predictor: KronosPathPredictor,
        enabled: bool = True,
        model_name: str = "Kronos-mini",
        lookback_bars: int = 250,
        sample_count: int = 20,
        minimum_history: int = 120,
    ) -> None:
        self.bar_repository = bar_repository
        self.trading_calendar = trading_calendar
        self.predictor = predictor
        self.enabled = enabled
        self.model_name = model_name
        self.lookback_bars = lookback_bars
        self.sample_count = sample_count
        self.minimum_history = minimum_history

    async def forecast(
        self,
        symbol: str,
        *,
        as_of: date,
        horizon: int = 20,
    ) -> KronosForecastResponse:
        if not 5 <= horizon <= 20:
            raise ValueError("horizon must be between 5 and 20")
        if not self.enabled:
            return self._status_response(
                "unavailable", symbol, as_of, reasons=("kronos_disabled",)
            )
        bars = sorted(
            [
                bar
                for bar in self.bar_repository.latest(symbol, self.lookback_bars)
                if bar.trade_date <= as_of
            ],
            key=lambda item: item.trade_date,
        )
        if len(bars) < self.minimum_history:
            return self._status_response(
                "insufficient",
                symbol,
                as_of,
                observed_through=bars[-1].trade_date if bars else None,
                lookback_bars=len(bars),
                reasons=("daily_history_insufficient",),
            )
        observed_through = bars[-1].trade_date
        future_dates = _future_trading_dates(
            self.trading_calendar,
            max(as_of, observed_through),
            horizon,
        )
        if len(future_dates) < horizon:
            return self._status_response(
                "insufficient",
                symbol,
                as_of,
                observed_through=observed_through,
                lookback_bars=len(bars),
                reasons=("future_trading_dates_insufficient",),
            )
        try:
            paths = await asyncio.to_thread(
                self.predictor.predict_paths,
                bars,
                future_dates,
                self.sample_count,
            )
            points, summary = summarize_forecast_paths(
                last_close=bars[-1].close,
                future_dates=future_dates,
                paths=paths,
            )
        except KronosUnavailableError as error:
            return self._status_response(
                "unavailable",
                symbol,
                as_of,
                observed_through=observed_through,
                lookback_bars=len(bars),
                reasons=(str(error),),
            )
        except Exception:
            return self._status_response(
                "error",
                symbol,
                as_of,
                observed_through=observed_through,
                lookback_bars=len(bars),
                reasons=("kronos_runtime_error",),
            )
        return KronosForecastResponse(
            status="ready",
            symbol=symbol,
            as_of=as_of,
            observed_through=observed_through,
            model=self.model_name,
            lookback_bars=len(bars),
            horizon_bars=horizon,
            sample_count=self.sample_count,
            summary=summary,
            points=points,
            sources=("local-daily-bars", "kronos"),
        )

    def _status_response(
        self,
        status,
        symbol: str,
        as_of: date,
        *,
        observed_through: date | None = None,
        lookback_bars: int = 0,
        reasons: tuple[str, ...] = (),
    ) -> KronosForecastResponse:
        return KronosForecastResponse(
            status=status,
            symbol=symbol,
            as_of=as_of,
            observed_through=observed_through,
            model=self.model_name,
            lookback_bars=lookback_bars,
            horizon_bars=0,
            sample_count=0,
            reasons=reasons,
            sources=("local-daily-bars",),
        )


def _future_trading_dates(calendar, start: date, horizon: int) -> list[date]:
    dates: list[date] = []
    cursor = start + timedelta(days=1)
    while len(dates) < horizon and (cursor - start).days <= horizon * 4:
        if calendar.is_trading_day(cursor):
            dates.append(cursor)
        cursor += timedelta(days=1)
    return dates


def summarize_forecast_paths(
    *,
    last_close: Decimal,
    future_dates: Sequence[date],
    paths: Sequence[Sequence[Decimal]],
) -> tuple[tuple[KronosForecastPoint, ...], KronosForecastSummary]:
    if last_close <= 0:
        raise ValueError("last_close must be positive")
    if not paths:
        raise ValueError("at least one path is required")
    horizon = len(future_dates)
    if horizon < 1:
        raise ValueError("future_dates must not be empty")
    if any(len(path) != horizon for path in paths):
        raise ValueError("all paths must have the same horizon")
    if any(value <= 0 for path in paths for value in path):
        raise ValueError("forecast prices must be positive")

    points = tuple(
        KronosForecastPoint(
            trade_date=trade_date,
            median_close=_quantile([path[index] for path in paths], Decimal("0.5")),
            lower_close=_quantile([path[index] for path in paths], Decimal("0.1")),
            upper_close=_quantile([path[index] for path in paths], Decimal("0.9")),
        )
        for index, trade_date in enumerate(future_dates)
    )
    final_values = [path[-1] for path in paths]
    lower_return = _return_pct(min(final_values), last_close)
    median_return = _return_pct(_quantile(final_values, Decimal("0.5")), last_close)
    upper_return = _return_pct(max(final_values), last_close)
    downside_probability = Decimal(
        sum(value < last_close for value in final_values) * 100
    ) / Decimal(len(final_values))
    summary = KronosForecastSummary(
        median_return_pct=median_return,
        upper_return_pct=upper_return,
        lower_return_pct=lower_return,
        path_dispersion_pct=(upper_return - lower_return).quantize(
            _PERCENT_QUANT, rounding=ROUND_HALF_UP
        ),
        downside_probability_pct=downside_probability.quantize(
            _PERCENT_QUANT, rounding=ROUND_HALF_UP
        ),
    )
    return points, summary


def _quantile(values: Sequence[Decimal], quantile: Decimal) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * Decimal(len(ordered) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - Decimal(lower_index)
    value = ordered[lower_index] + (ordered[upper_index] - ordered[lower_index]) * fraction
    return value.quantize(_PERCENT_QUANT, rounding=ROUND_HALF_UP)


def _return_pct(value: Decimal, last_close: Decimal) -> Decimal:
    return ((value / last_close) - Decimal("1")) * Decimal("100")
