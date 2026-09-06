import { ArrowRight, CircleAlert, Link2, ShieldCheck } from "lucide-react";

import type { EvidenceGraph } from "./types";

const kindLabels: Record<Exclude<EvidenceGraph["nodes"][number]["kind"], "evidence">, string> = {
  fact: "事实",
  inference: "推导",
  judgement: "判断",
  unavailable: "不可用",
};

function nodeLabel(graph: EvidenceGraph, nodeId: string) {
  return graph.nodes.find((node) => node.node_id === nodeId)?.label ?? nodeId;
}

export function ResearchEvidenceGraph({ graph }: { graph?: EvidenceGraph }) {
  if (!graph || graph.nodes.length === 0) return null;
  const conclusions = graph.nodes.filter((node) => node.kind !== "evidence");
  return <section className="research-evidence-graph" role="region" aria-label="公司研究证据图">
    <header>
      <div><span>DIRECTED EVIDENCE GRAPH</span><h2>公司研究证据图</h2></div>
      <small>{graph.edges.length} 条有向关系 · {graph.nodes.length} 个节点</small>
    </header>
    <div className="research-evidence-graph__nodes">
      {conclusions.map((node) => <article key={node.node_id} data-kind={node.kind}>
        <header><b>{node.label}</b><span>{node.kind === "unavailable" ? <CircleAlert size={14} /> : <ShieldCheck size={14} />}{node.kind === "unavailable" ? "不可用" : node.kind === "evidence" ? "证据" : kindLabels[node.kind]}</span></header>
        <p>{node.claim}</p>
        {node.limitations[0] && <small>{node.limitations[0]}</small>}
      </article>)}
    </div>
    {graph.edges.length > 0 && <details className="research-evidence-graph__edges" role="group" aria-label="证据图关系">
      <summary>查看 {graph.edges.length} 条证据关系（支持与推导）</summary>
      <div className="research-evidence-graph__edge-list">
        {graph.edges.map((edge) => <div key={`${edge.source_node_id}-${edge.target_node_id}-${edge.relation}`}>
          <Link2 size={14} /><span>{edge.relation === "supports" ? "支持" : "推导"} · {nodeLabel(graph, edge.source_node_id)}</span><ArrowRight size={14} /><b>{nodeLabel(graph, edge.target_node_id)}</b>
        </div>)}
      </div>
    </details>}
  </section>;
}
