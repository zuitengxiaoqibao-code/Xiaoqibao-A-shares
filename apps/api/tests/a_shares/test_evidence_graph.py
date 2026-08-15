from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from qibao_api.a_shares.evidence_graph import build_evidence_graph
from qibao_api.contracts.company_research import (
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    ResearchConclusion,
)


NOW = datetime(2026, 8, 15, tzinfo=timezone.utc)


def conclusion(**changes) -> ResearchConclusion:
    values = {
        "key": "business_model",
        "label": "Business model",
        "kind": "fact",
        "claim": "Verified filing describes the core business.",
        "evidence_ids": ("filing-1",),
        "source_count": 1,
        "observed_at": NOW,
        "limitations": (),
    }
    values.update(changes)
    return ResearchConclusion(**values)


def test_build_evidence_graph_links_sources_to_layered_research_conclusions() -> None:
    graph = build_evidence_graph((
        conclusion(),
        conclusion(
            key="competitive_position",
            label="Competitive position",
            kind="inference",
            claim="The filing supports a competitive-position inference.",
            evidence_ids=("filing-1", "peer-1"),
            source_count=2,
        ),
        conclusion(
            key="contrary_risks",
            label="Contrary risks",
            kind="judgement",
            claim="The evidence requires a cautious judgement.",
            evidence_ids=("peer-1",),
            source_count=1,
        ),
        conclusion(
            key="industry_space",
            label="Industry space",
            kind="unavailable",
            claim="Industry evidence is unavailable.",
            evidence_ids=(),
            source_count=0,
            observed_at=None,
            limitations=("No point-in-time industry source.",),
        ),
    ))

    nodes = {item.node_id: item for item in graph.nodes}
    edges = {
        (item.source_node_id, item.target_node_id, item.relation)
        for item in graph.edges
    }
    assert nodes["evidence:filing-1"].kind == "evidence"
    assert nodes["conclusion:business_model"].kind == "fact"
    assert nodes["conclusion:competitive_position"].kind == "inference"
    assert nodes["conclusion:contrary_risks"].kind == "judgement"
    assert nodes["conclusion:industry_space"].kind == "unavailable"
    assert (
        "evidence:filing-1",
        "conclusion:business_model",
        "supports",
    ) in edges
    assert (
        "conclusion:business_model",
        "conclusion:competitive_position",
        "derives_from",
    ) in edges
    assert (
        "conclusion:competitive_position",
        "conclusion:contrary_risks",
        "derives_from",
    ) in edges
    assert nodes["conclusion:industry_space"].limitations == (
        "No point-in-time industry source.",
    )
    assert not any(
        item.target_node_id == "conclusion:industry_space" for item in graph.edges
    )


def test_evidence_graph_rejects_unknown_edges_and_unavailable_proxy_evidence() -> None:
    unavailable = EvidenceGraphNode(
        node_id="conclusion:industry_space",
        kind="unavailable",
        label="Industry space",
        claim="Unavailable",
        limitations=("No source.",),
    )
    with pytest.raises(ValidationError, match="known graph nodes"):
        EvidenceGraph(
            nodes=(unavailable,),
            edges=(EvidenceGraphEdge(
                source_node_id="evidence:proxy",
                target_node_id=unavailable.node_id,
                relation="supports",
            ),),
        )

    with pytest.raises(ValidationError, match="unavailable node cannot claim evidence"):
        EvidenceGraphNode(
            node_id="conclusion:industry_space",
            kind="unavailable",
            label="Industry space",
            claim="Unavailable",
            evidence_ids=("proxy-value",),
            limitations=("No source.",),
        )
