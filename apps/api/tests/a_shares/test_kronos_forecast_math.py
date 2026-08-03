from datetime import date
from decimal import Decimal

import pytest

from qibao_api.a_shares.kronos_forecast import summarize_forecast_paths


def test_summarize_forecast_paths_returns_quantile_band_and_risk_summary() -> None:
    points, summary = summarize_forecast_paths(
        last_close=Decimal("10"),
        future_dates=[date(2026, 7, 27)],
        paths=[
            [Decimal("10")],
            [Decimal("12")],
            [Decimal("14")],
        ],
    )

    assert points[0].median_close == Decimal("12")
    assert points[0].lower_close == Decimal("10.40")
    assert points[0].upper_close == Decimal("13.60")
    assert summary.median_return_pct == Decimal("20")
    assert summary.upper_return_pct == Decimal("40")
    assert summary.lower_return_pct == Decimal("0")
    assert summary.path_dispersion_pct == Decimal("40")
    assert summary.downside_probability_pct == Decimal("0")


def test_summarize_forecast_paths_rejects_empty_or_mismatched_paths() -> None:
    with pytest.raises(ValueError, match="at least one path"):
        summarize_forecast_paths(
            last_close=Decimal("10"), future_dates=[date(2026, 7, 27)], paths=[]
        )

    with pytest.raises(ValueError, match="same horizon"):
        summarize_forecast_paths(
            last_close=Decimal("10"),
            future_dates=[date(2026, 7, 27)],
            paths=[[Decimal("11")], [Decimal("11"), Decimal("12")]],
        )
