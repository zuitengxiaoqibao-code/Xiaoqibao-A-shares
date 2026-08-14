from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from qibao_api.contracts.market_overview import (
    MarketOverviewResponse,
    OverviewBreadth,
    OverviewIndexQuote,
    OverviewFeatureStock,
    OverviewLimitEcology,
    OverviewLiquidity,
    OverviewSentiment,
)


NOW = datetime(2026, 7, 29, 1, 35, tzinfo=timezone.utc)


def response() -> MarketOverviewResponse:
    return MarketOverviewResponse(
        status="partial",
        as_of="2026-07-29",
        observed_at=NOW,
        sentiment=OverviewSentiment(
            score=Decimal("76"), band="active", coverage_percent=Decimal("82"),
            quality="partial", observed_at=NOW,
        ),
        breadth=OverviewBreadth(
            rising_count=4439, falling_count=699, flat_count=20, valid_count=5158,
        ),
        limit_ecology=OverviewLimitEcology(
            limit_up_count=78, limit_down_count=6, broken_limit_up_count=19,
            seal_rate_percent=Decimal("80.41"),
        ),
        liquidity=OverviewLiquidity(
            total_amount_yi=Decimal("15862.96"), baseline_amount_yi=Decimal("19444.39"),
            relative_amount=Decimal("0.82"),
        ),
        indices=(OverviewIndexQuote(
            instrument="sh000001", name="上证指数", value=Decimal("3823.73"),
            change=Decimal("9.53"), change_percent=Decimal("0.25"),
            observed_at=NOW, source="tencent", quality="ready",
        ),),
        warnings=("minute_series_unavailable",),
        sources=("market-sentiment-cache", "tencent"),
    )


def test_market_overview_accepts_partial_regions_without_fabricated_rows() -> None:
    result = response()
    assert result.status == "partial"
    assert result.minute_series == ()
    assert result.sectors == ()
    assert result.sentiment.score == Decimal("76")
    assert result.field_evidence == ()


def test_index_quote_rejects_non_positive_values() -> None:
    with pytest.raises(ValidationError):
        OverviewIndexQuote(
            instrument="sh000001", name="上证指数", value=Decimal("0"),
            change=Decimal("0"), change_percent=Decimal("0"),
            observed_at=NOW, source="tencent", quality="ready",
        )


def test_ready_overview_requires_an_index_and_minute_series() -> None:
    payload = response().model_dump()
    payload["status"] = "ready"
    with pytest.raises(ValidationError):
        MarketOverviewResponse.model_validate(payload)


def test_feature_stock_preserves_local_quote_evidence() -> None:
    stock = OverviewFeatureStock(
        symbol="600000", name="浦发银行", price=Decimal("9.33"),
        previous_close=Decimal("9.19"), open=Decimal("9.19"),
        high=Decimal("9.34"), low=Decimal("9.17"), volume=Decimal("655951"),
        amount_yi=Decimal("6.09"), change_percent=Decimal("1.52"),
        state="active", observed_at=NOW, source="tdx-local-rpc", quality="ready",
    )

    assert stock.high == Decimal("9.34")
    assert stock.state == "active"
