from qibao_api.a_shares.strategy_draft_gate import StrategyDraftGate


def test_draft_gate_rejects_insufficient_samples_without_probability():
    result = StrategyDraftGate.review({"sample_count": 8, "fields": ["close"]}, "version-a")
    assert result.status == "rejected"
    assert result.probability is None
    assert "样本交易不足" in result.reasons
