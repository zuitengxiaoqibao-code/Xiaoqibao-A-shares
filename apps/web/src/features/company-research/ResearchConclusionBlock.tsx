import type { ResearchConclusion } from "./types";

const kindLabel: Record<ResearchConclusion["kind"], string> = {
  fact: "事实",
  inference: "推导",
  judgement: "判断",
  unavailable: "不可用",
};

function ConclusionItem({ item }: { item: ResearchConclusion }) {
  return <article data-kind={item.kind}>
    <header><b>{item.label}</b><span>{kindLabel[item.kind]}</span></header>
    <p>{item.claim}</p>
    <footer>
      <span>{item.source_count > 0 ? `${item.source_count}项证据` : "无可追溯证据"}</span>
      {item.limitations[0] && <em>{item.limitations[0]}</em>}
    </footer>
  </article>;
}

export function ResearchConclusionBlock({ conclusions }: { conclusions: ResearchConclusion[] }) {
  if (!conclusions.length) return null;
  const available = conclusions.filter((item) => item.kind !== "unavailable").slice(0, 3);
  const unavailable = conclusions.find((item) => item.kind === "unavailable");
  const visible = [...available, ...(unavailable ? [unavailable] : [])].slice(0, 4);
  const visibleKeys = new Set(visible.map((item) => item.key));
  const remaining = conclusions.filter((item) => !visibleKeys.has(item.key));
  const counts = conclusions.reduce<Record<ResearchConclusion["kind"], number>>(
    (current, item) => ({ ...current, [item.kind]: current[item.kind] + 1 }),
    { fact: 0, inference: 0, judgement: 0, unavailable: 0 },
  );

  return <section className="research-conclusion-block" role="region" aria-label="研究结论分层">
    <header>
      <div><span>RESEARCH CLAIMS</span><h2>研究结论分层</h2></div>
      <nav aria-label="结论分类统计">
        {(Object.keys(kindLabel) as ResearchConclusion["kind"][]).map((kind) => (
          <span data-kind={kind} key={kind}>{kindLabel[kind]} {counts[kind]}</span>
        ))}
      </nav>
    </header>
    <div>{visible.map((item) => <ConclusionItem item={item} key={item.key} />)}</div>
    {remaining.length > 0 && <details>
      <summary>查看其余 {remaining.length} 条结论</summary>
      <div>{remaining.map((item) => <ConclusionItem item={item} key={item.key} />)}</div>
    </details>}
  </section>;
}
