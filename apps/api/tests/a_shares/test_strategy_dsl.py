import pytest

from qibao_api.a_shares.strategy_dsl import StrategyDSL


def test_dsl_compiles_whitelisted_expression():
    compiled = StrategyDSL.compile("close > ma20", {"close", "ma20"})
    assert compiled.expression == "close > ma20"


@pytest.mark.parametrize("expression", ["os.system('x')", "unknown > close"])
def test_dsl_rejects_code_and_unknown_fields(expression):
    with pytest.raises(ValueError):
        StrategyDSL.compile(expression, {"close", "ma20"})
