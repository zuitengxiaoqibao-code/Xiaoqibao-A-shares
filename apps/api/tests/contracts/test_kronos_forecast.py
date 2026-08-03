from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.kronos_forecast import KronosForecastResponse


def test_forecast_response_accepts_ready_payload() -> None:
    response = KronosForecastResponse(
        status="ready",
        symbol="600000",
        as_of=date(2026, 7, 24),
        observed_through=date(2026, 7, 24),
        model="Kronos-mini",
        frequency="1d",
        lookback_bars=250,
        horizon_bars=5,
        sample_count=20,
        summary={
            "median_return_pct": Decimal("3.4"),
            "upper_return_pct": Decimal("11.2"),
            "lower_return_pct": Decimal("-6.1"),
            "path_dispersion_pct": Decimal("8.7"),
            "downside_probability_pct": Decimal("35"),
        },
        points=[],
        sources=("local-daily-bars", "kronos"),
    )

    assert response.status == "ready"
    assert response.symbol == "600000"


def test_forecast_response_rejects_non_a_share_symbol() -> None:
    with pytest.raises(ValidationError):
        KronosForecastResponse(
            status="unavailable",
            symbol="BTCUSDT",
            as_of=date(2026, 7, 24),
            observed_through=None,
            model="Kronos-mini",
            frequency="1d",
            lookback_bars=0,
            horizon_bars=0,
            sample_count=0,
        )
