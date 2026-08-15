from datetime import date
from types import SimpleNamespace

import pytest

from qibao_api.a_shares.data_gap_repair import inspect_gaps


def test_inspect_gaps_reports_missing_dates_symbols_fields_and_source_hints():
    trading_dates = (date(2026, 8, 13), date(2026, 8, 14))
    bars = {
        "600519": [
            SimpleNamespace(
                symbol="600519", trade_date=date(2026, 8, 13), source="local-tdx",
                open=100, high=101, low=99, close=100, volume=100, amount=10000,
            ),
            SimpleNamespace(
                symbol="600519", trade_date=date(2026, 8, 14), source="local-tdx",
                open=100, high=101, low=99, close=None, volume=100, amount=10000,
            ),
        ],
        "000001": [],
    }

    result = inspect_gaps(trading_dates, ("600519", "000001"), bars)

    assert result["missing_trade_dates"]["000001"] == ["2026-08-13", "2026-08-14"]
    assert result["missing_trade_dates"].get("600519") == []
    assert result["missing_symbols"] == ["000001"]
    assert result["field_gaps"]["600519"]["2026-08-14"] == ["close"]
    assert result["source_recommendations"]["600519"] == "local-tdx"
    assert result["source_recommendations"]["000001"] == "local-tdx"
    assert result["gap_count"] == 4


def test_inspect_gaps_rejects_duplicate_dates_and_invalid_symbols():
    with pytest.raises(ValueError, match="trading_dates must be unique"):
        inspect_gaps((date(2026, 8, 14), date(2026, 8, 14)), (), {})
    with pytest.raises(ValueError, match="invalid A-share symbol"):
        inspect_gaps((date(2026, 8, 14),), ("ABC",), {})
