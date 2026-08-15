from collections.abc import Iterable

from qibao_api.contracts.company_research import (
    EvidenceGraph,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    ResearchConclusion,
)


_KIND_RANK = {"fact": 1, "inference": 2, "judgement": 3}


def build_evidence_graph(
    conclusions: Iterable[ResearchConclusion],
) -> EvidenceGraph:
    ordered = tuple(conclusions)
    nodes: list[EvidenceGraphNode] = []
    edges: list[EvidenceGraphEdge] = []
    evidence_observed_at = {
        evidence_id: min(
            item.observed_at
            for item in ordered
            if evidence_id in item.evidence_ids and item.observed_at is not None
        )
        for evidence_id in dict.fromkeys(
            evidence_id for item in ordered for evidence_id in item.evidence_ids
        )
    }
    for evidence_id, observed_at in evidence_observed_at.items():
        node_id = f"evidence:{evidence_id}"
        nodes.append(EvidenceGraphNode(
            node_id=node_id,
            kind="evidence",
            label=evidence_id,
            claim=evidence_id,
            evidence_ids=(evidence_id,),
            observed_at=observed_at,
        ))

    for item in ordered:
        node_id = f"conclusion:{item.key}"
        nodes.append(EvidenceGraphNode(
            node_id=node_id,
            kind=item.kind,
            label=item.label,
            claim=item.claim,
            evidence_ids=item.evidence_ids,
            observed_at=item.observed_at,
            limitations=item.limitations,
        ))
        edges.extend(
            EvidenceGraphEdge(
                source_node_id=f"evidence:{evidence_id}",
                target_node_id=node_id,
                relation="supports",
            )
            for evidence_id in item.evidence_ids
        )

    available = tuple(item for item in ordered if item.kind in _KIND_RANK)
    for target in available:
        target_evidence = set(target.evidence_ids)
        candidates = tuple(
            source
            for source in available
            if _KIND_RANK[source.kind] < _KIND_RANK[target.kind]
            and target_evidence.intersection(source.evidence_ids)
        )
        if not candidates:
            continue
        nearest_rank = max(_KIND_RANK[item.kind] for item in candidates)
        edges.extend(
            EvidenceGraphEdge(
                source_node_id=f"conclusion:{source.key}",
                target_node_id=f"conclusion:{target.key}",
                relation="derives_from",
            )
            for source in candidates
            if _KIND_RANK[source.kind] == nearest_rank
        )
    return EvidenceGraph(nodes=tuple(nodes), edges=tuple(edges))
