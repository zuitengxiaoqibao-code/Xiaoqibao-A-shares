from datetime import datetime, timezone
from decimal import Decimal

import pytest

from qibao_api.gongbu.tdx_formula import (
    TdxFormulaDataUnavailable,
    TdxLocalFormulaSource,
    parse_tdx_formula_batch,
)


NOW = datetime(2026, 8, 6, 8, 0, tzinfo=timezone.utc)


def test_parse_tdx_formula_batch_keeps_explicit_indicator_values() -> None:
    result = parse_tdx_formula_batch(
        {
            "ErrorId": "0",
            "Value": [
                {
                    "Code": "600000.SH",
                    "Name": "浦发银行",
                    "MACD": "0.25",
                    "DIF": "0.10",
                    "DEA": "0.05",
                }
            ],
        },
        formula_name="formula_process_mul_zb",
        fetched_at=NOW,
    )

    assert len(result) == 1
    assert result[0].symbol == "600000"
    assert result[0].values == {
        "MACD": Decimal("0.25"),
        "DIF": Decimal("0.10"),
        "DEA": Decimal("0.05"),
    }
    assert result[0].source == "tdx-local-rpc"


def test_parse_tdx_formula_batch_preserves_missing_values_as_missing() -> None:
    result = parse_tdx_formula_batch(
        {"ErrorId": "0", "Value": [{"Code": "600000.SH", "MACD": "--"}]},
        formula_name="formula_process_mul_zb",
        fetched_at=NOW,
    )

    assert len(result) == 1
    assert result[0].values == {}


def test_parse_tdx_formula_batch_rejects_error_or_empty_payload() -> None:
    with pytest.raises(TdxFormulaDataUnavailable):
        parse_tdx_formula_batch(
            {"ErrorId": "0", "Value": []},
            formula_name="formula_process_mul_zb",
            fetched_at=NOW,
        )
    with pytest.raises(TdxFormulaDataUnavailable):
        parse_tdx_formula_batch(
            {"ErrorId": "12"},
            formula_name="formula_process_mul_zb",
            fetched_at=NOW,
        )


def test_local_formula_source_uses_explicit_formula_method_and_codes() -> None:
    class Rpc:
        def __init__(self) -> None:
            self.calls = []

        def available(self) -> bool:
            return True

        def call(self, method, params):
            self.calls.append((method, params))
            return {"ErrorId": "0", "Value": [{"Code": "600000.SH", "MACD": "0.1"}]}

        def close(self) -> None:
            return None

    rpc = Rpc()
    source = TdxLocalFormulaSource(lambda: rpc, clock=lambda: NOW)
    result = source.fetch(
        formula_name="formula_process_mul_zb",
        stock_codes=("600000",),
    )

    assert result[0].values["MACD"] == Decimal("0.1")
    assert rpc.calls == [
        ("formula_process_mul_zb", {"stock_list": ["600000.SH"]})
    ]
