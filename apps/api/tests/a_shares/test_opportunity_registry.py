from qibao_api.a_shares.opportunity_registry import (
    OpportunityRegistry,
    build_default_opportunity_registry,
)


def test_default_opportunities_cover_seven_distinct_research_types() -> None:
    items = build_default_opportunity_registry().definitions()

    assert len(items) == 7
    assert {item.opportunity_id for item in items} == {
        "trend_continuation",
        "volume_breakout",
        "oversold_recovery",
        "quality_improvement",
        "valuation_recovery",
        "event_driven",
        "defensive_low_volatility",
    }
    assert len({item.invalidation_rules for item in items}) == 7
    assert all(item.required_evidence for item in items)


def test_registry_rejects_duplicate_opportunity_ids() -> None:
    item = build_default_opportunity_registry().definitions()[0]
    registry = OpportunityRegistry()
    registry.register(item)

    try:
        registry.register(item)
    except ValueError as error:
        assert "already registered" in str(error)
    else:
        raise AssertionError("duplicate opportunity id must be rejected")


def test_opportunity_definitions_keep_scoring_separate_from_probability() -> None:
    items = build_default_opportunity_registry().definitions()

    assert all("win_rate" not in item.score_components for item in items)
    assert all("probability" not in item.score_components for item in items)
