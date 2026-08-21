from datetime import date
from decimal import Decimal

from qibao_api.a_shares.quant_risk_gates import evaluate_risk_gates
from qibao_api.contracts.quant_research import QuantRiskContext
from qibao_api.contracts.quant_strategy import QuantStrategyCandidate


def candidate(**updates) -> QuantStrategyCandidate:
    values = {
        "symbol": "600000",
        "name": "浦发银行",
        "model": "权重容量低吸模型",
        "strategy_score": Decimal("82"),
        "regime_match": Decimal("0.9"),
        "stock_score": Decimal("0.8"),
        "trigger_score": Decimal("0"),
        "rr_score": Decimal("0.8"),
        "risk_penalty": Decimal("5"),
        "status": "pending_trigger",
        "trigger_confirmed": False,
        "position": Decimal("0"),
        "planned_position": Decimal("0.1"),
        "evidence_coverage_percent": Decimal("90"),
        "buy_triggers": ("回踩均价不破",),
        "invalidation_rules": ("跌破均价且资金转负",),
        "factor_as_of": date(2026, 8, 21),
        "sources": ("tdx-local-daily",),
    }
    values.update(updates)
    return QuantStrategyCandidate(**values)


def by_key(result, key: str):
    return next(item for item in result.checks if item.key == key)


def test_missing_financial_fields_are_unavailable_not_pass() -> None:
    result = evaluate_risk_gates(candidate(), QuantRiskContext())

    assert by_key(result, "financial_anomaly").status == "unavailable"
    assert result.overall_status == "warn"


def test_untradeable_limit_state_is_a_hard_block() -> None:
    context = QuantRiskContext(
        suspended=False,
        limit_untradeable=True,
        average_amount_20d=Decimal("500000000"),
    )

    result = evaluate_risk_gates(candidate(), context)

    assert by_key(result, "tradability").status == "block"
    assert result.overall_status == "block"
    assert "涨跌停价格不可成交" in result.blockers


def test_candidate_missing_evidence_never_passes_evidence_gate() -> None:
    result = evaluate_risk_gates(
        candidate(
            evidence_coverage_percent=Decimal("40"),
            missing_evidence=("盘中资金净流入",),
        ),
        QuantRiskContext(),
    )

    assert by_key(result, "evidence").status == "block"
    assert result.overall_status == "block"


def test_complete_beneish_components_are_calculated_deterministically() -> None:
    context = QuantRiskContext(beneish_components={
        "dsri": Decimal("1.4"),
        "gmi": Decimal("1.2"),
        "aqi": Decimal("1.1"),
        "sgi": Decimal("1.3"),
        "depi": Decimal("1.1"),
        "sgai": Decimal("1.1"),
        "lvgi": Decimal("1.1"),
        "tata": Decimal("0.2"),
    })

    result = evaluate_risk_gates(candidate(), context)
    gate = by_key(result, "financial_anomaly")

    assert gate.status == "warn"
    assert gate.metric_value is not None
    assert gate.metric_value > Decimal("-1.78")


def test_concentration_without_exposure_data_is_unavailable() -> None:
    result = evaluate_risk_gates(candidate(), QuantRiskContext())

    assert by_key(result, "concentration").status == "unavailable"

