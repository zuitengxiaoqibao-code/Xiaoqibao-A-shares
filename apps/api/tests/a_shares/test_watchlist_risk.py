from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from qibao_api.a_shares.watchlist_risk import WatchlistRiskService
from qibao_api.contracts.bars import DailyBar


NOW = datetime(2026, 8, 14, 8, 0, tzinfo=UTC)


class Directory:
    def resolve(self, symbol):
        values = {
            "600000": ("浦发银行", "银行", ("金融",)),
            "601398": ("工商银行", "银行", ("金融",)),
        }
        if symbol not in values:
            return None
        name, industry, sectors = values[symbol]
        return SimpleNamespace(name=name, industry=industry, sectors=sectors)


class Bars:
    def latest_many(self, symbols, limit, as_of):
        assert limit == 61
        start = as_of - timedelta(days=29)
        result = {}
        for offset, symbol in enumerate(symbols):
            result[symbol] = [DailyBar(
                symbol=symbol,
                trade_date=start + timedelta(days=index),
                open=Decimal(10 + offset) + Decimal(index) / 100,
                high=Decimal(10 + offset) + Decimal(index) / 100 + Decimal("0.2"),
                low=Decimal(10 + offset) + Decimal(index) / 100 - Decimal("0.2"),
                close=Decimal(10 + offset) + Decimal(index) / 100,
                volume=Decimal(1000 + index),
                amount=Decimal(10000 + index),
                source="tdx-local-daily",
            ) for index in range(30)]
        return result


def test_watchlist_risk_is_explicitly_observation_only() -> None:
    result = WatchlistRiskService(Directory(), Bars()).analyze(
        ("600000", "601398"), as_of=date(2026, 8, 14), observed_at=NOW
    )

    assert result.mode == "observation_basket"
    assert result.status == "ready"
    assert result.coverage_percent == Decimal("100.0")
    assert result.industries[0].label == "银行"
    assert result.industries[0].observation_weight_percent == Decimal("100.0")
    assert "持仓" not in result.model_dump_json()
    assert result.sources == ("tdx-local-daily",)

