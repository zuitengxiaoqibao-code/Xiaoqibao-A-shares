from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from qibao_api.a_shares.portfolio_risk import PortfolioRiskService, PortfolioRiskStore
from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.portfolio_risk import PortfolioPositionInput


NOW = datetime(2026, 8, 11, 8, tzinfo=timezone.utc)


def test_portfolio_risk_store_persists_upserts_and_deletes_positions(tmp_path) -> None:
    store = PortfolioRiskStore(tmp_path / "portfolio-risk.sqlite3")

    assert store.current() == ()

    store.upsert(PortfolioPositionInput(
        symbol="600519", shares=Decimal("100"), cost_price=Decimal("1500"),
    ))
    store.upsert(PortfolioPositionInput(
        symbol="000001", shares=Decimal("200"), cost_price=Decimal("10"),
    ))
    store.upsert(PortfolioPositionInput(
        symbol="600519", shares=Decimal("120"), cost_price=Decimal("1490"),
    ))

    assert [(item.symbol, item.shares, item.cost_price) for item in store.current()] == [
        ("000001", Decimal("200"), Decimal("10")),
        ("600519", Decimal("120"), Decimal("1490")),
    ]

    assert store.delete("600519") is True
    assert store.delete("600519") is False
    assert [item.symbol for item in store.current()] == ["000001"]


def test_portfolio_risk_empty_store_returns_a_truthful_manual_input_state() -> None:
    class Bars:
        def latest_many(self, symbols, limit, as_of):
            raise AssertionError("empty portfolio must not query daily bars")

    class Enrichment:
        def latest(self, symbol):
            raise AssertionError("empty portfolio must not query enrichment")

    result = PortfolioRiskService(Bars(), Enrichment(), clock=lambda: NOW).analyze(
        [], as_of=date(2026, 8, 11), market_regime=None,
    )

    assert result.status == "unavailable"
    assert result.positions == ()
    assert result.warnings == ("尚未录入真实持仓，组合风险暂不计算",)


def _bars(symbol: str, start: Decimal, step: Decimal) -> list[DailyBar]:
    values = []
    for index in range(61):
        close = start + step * Decimal(index)
        values.append(DailyBar(
            symbol=symbol,
            trade_date=date(2026, 5, 12) + timedelta(days=index),
            open=close,
            high=close,
            low=close,
            close=close,
            volume=100,
            amount=close * 100,
            source="tdx-local-daily",
        ))
    return values


def test_portfolio_risk_uses_real_prices_weights_industries_and_correlations() -> None:
    history = {
        "600001": _bars("600001", Decimal("10"), Decimal("0.10")),
        "600002": _bars("600002", Decimal("20"), Decimal("0.20")),
    }

    class Bars:
        def latest_many(self, symbols, limit, as_of):
            assert symbols == ["600001", "600002"]
            assert limit == 61
            return history

    class Enrichment:
        def latest(self, symbol):
            return SimpleNamespace(industry_name="银行", sources=("eastmoney-industry",))

    service = PortfolioRiskService(Bars(), Enrichment(), clock=lambda: NOW)
    result = service.analyze(
        [
            PortfolioPositionInput(symbol="600001", shares=Decimal("100"), cost_price=Decimal("12")),
            PortfolioPositionInput(symbol="600002", shares=Decimal("50"), cost_price=Decimal("25")),
        ],
        as_of=date(2026, 8, 11),
        market_regime="轮动震荡",
    )

    assert result.status == "ready"
    assert result.total_market_value == Decimal("3200.00")
    assert result.total_cost == Decimal("2450.00")
    assert result.total_pnl == Decimal("750.00")
    assert result.positions[0].weight_percent == Decimal("50.00")
    assert result.positions[1].weight_percent == Decimal("50.00")
    assert result.hhi == Decimal("5000.00")
    assert result.industries[0].industry == "银行"
    assert result.industries[0].weight_percent == Decimal("100.00")
    assert result.high_correlation_pairs[0].correlation >= Decimal("0.99")
    assert result.market_position_cap_percent == Decimal("50.00")
    assert result.stress_scenarios[0].estimated_loss == Decimal("-64.00")


def test_portfolio_risk_keeps_industry_and_correlation_unavailable_when_evidence_is_missing() -> None:
    class Bars:
        def latest_many(self, symbols, limit, as_of):
            return {"600001": _bars("600001", Decimal("10"), Decimal("0.10"))[:5]}

    class Enrichment:
        def latest(self, symbol):
            return None

    result = PortfolioRiskService(Bars(), Enrichment(), clock=lambda: NOW).analyze(
        [PortfolioPositionInput(symbol="600001", shares=Decimal("100"), cost_price=Decimal("12"))],
        as_of=date(2026, 8, 11),
        market_regime=None,
    )

    assert result.status == "partial"
    assert result.positions[0].industry is None
    assert result.average_correlation is None
    assert result.market_position_cap_percent is None
    assert any("行业" in warning for warning in result.warnings)
    assert any("市场风格" in warning for warning in result.warnings)


def test_portfolio_risk_excludes_blocked_bar_series_from_value_and_correlation() -> None:
    valid = _bars("600001", Decimal("10"), Decimal("0.10"))
    invalid = _bars("600002", Decimal("20"), Decimal("0.20"))
    invalid[20] = invalid[19].model_copy(update={"symbol": "600002"})

    class Bars:
        def latest_many(self, symbols, limit, as_of):
            return {"600001": valid, "600002": invalid}

    class Enrichment:
        def latest(self, symbol):
            return SimpleNamespace(industry_name="银行", sources=("eastmoney-industry",))

    result = PortfolioRiskService(Bars(), Enrichment(), clock=lambda: NOW).analyze(
        [
            PortfolioPositionInput(symbol="600001", shares=Decimal("100"), cost_price=Decimal("12")),
            PortfolioPositionInput(symbol="600002", shares=Decimal("50"), cost_price=Decimal("25")),
        ],
        as_of=date(2026, 8, 11),
        market_regime="轮动震荡",
    )

    assert result.status == "partial"
    assert result.total_market_value == Decimal("1600.00")
    assert result.total_cost == Decimal("1200.00")
    assert result.positions[0].status == "ready"
    assert result.positions[0].weight_percent == Decimal("100.00")
    assert result.positions[1].status == "unavailable"
    assert result.positions[1].market_value is None
    assert result.high_correlation_pairs == ()
    assert "重复交易日" in result.positions[1].limitations[0]
    assert any("600002" in warning and "质量" in warning for warning in result.warnings)


def test_portfolio_risk_keeps_warning_series_and_surfaces_quality_warning() -> None:
    warning_bars = _bars("600001", Decimal("10"), Decimal("0.10"))
    warning_bars[30] = warning_bars[30].model_copy(update={
        "open": Decimal("30"),
        "high": Decimal("30"),
        "low": Decimal("30"),
        "close": Decimal("30"),
        "amount": Decimal("3000"),
    })

    class Bars:
        def latest_many(self, symbols, limit, as_of):
            return {"600001": warning_bars}

    class Enrichment:
        def latest(self, symbol):
            return SimpleNamespace(industry_name="银行", sources=("eastmoney-industry",))

    result = PortfolioRiskService(Bars(), Enrichment(), clock=lambda: NOW).analyze(
        [PortfolioPositionInput(symbol="600001", shares=Decimal("100"), cost_price=Decimal("12"))],
        as_of=date(2026, 8, 11),
        market_regime="轮动震荡",
    )

    assert result.positions[0].status == "ready"
    assert result.total_market_value is not None
    assert any("600001" in warning and "跳变超过 35%" in warning for warning in result.warnings)
