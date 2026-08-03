from datetime import date, timedelta
from decimal import Decimal

from qibao_api.a_shares.market_sentiment import MarketSentimentFactorBuilder
from qibao_api.contracts.bars import DailyBar


def history(symbol: str, *, start: str, drift: str) -> list[DailyBar]:
    first = date.fromisoformat(start)
    return [
        DailyBar(
            symbol=symbol,
            trade_date=first + timedelta(days=index),
            open=Decimal("10") + Decimal(drift) * index,
            high=Decimal("10.10") + Decimal(drift) * index,
            low=Decimal("9.90") + Decimal(drift) * index,
            close=Decimal("10") + Decimal(drift) * index,
            volume=1000,
            amount=Decimal("1000"),
            source="fixture",
        )
        for index in range(252)
    ]


def test_factor_builder_derives_ma_high_low_money_and_style_inputs() -> None:
    histories = {
        "600000": history("600000", start="2025-01-01", drift="0.01"),
        "000001": history("000001", start="2025-01-01", drift="0.005"),
        "000852": history("000852", start="2025-01-01", drift="0.02"),
        "000300": history("000300", start="2025-01-01", drift="0.01"),
        "511010": history("511010", start="2025-01-01", drift="0.001"),
    }

    result = MarketSentimentFactorBuilder.from_histories(
        histories,
        industry_by_symbol={"600000": "银行", "000001": "银行"},
    )

    assert result.effective_count == 2
    assert result.new_high_252_count == 2
    assert result.ma20_above_count == 2
    assert result.ma60_above_count == 2
    assert result.five_day_rising_count == 2
    assert result.sixty_day_new_low_count == 0
    assert result.effective_industry_count == 1
    assert result.rising_industry_count == 1
    assert result.benchmark_return_20d_percent is not None
    assert result.bond_etf_return_20d_percent is not None
    assert result.small_cap_return_5d_percent is not None
    assert result.large_cap_return_5d_percent is not None
