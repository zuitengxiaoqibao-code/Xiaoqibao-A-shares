import type { CompanyResearchSection } from "./types";

const statusLabels: Record<CompanyResearchSection["status"], string> = {
  ready: "证据已核验",
  partial: "证据不完整",
  unavailable: "证据不可用",
  clear: "当前未触发",
  triggered: "需要复核",
};

export function CompanyResearchSections({ sections }: { sections: CompanyResearchSection[] }) {
  if (sections.length === 0) return null;
  return <section className="company-research-sections" aria-label="十段公司研究账本">
    <header>
      <div><span>10-SECTION RESEARCH LEDGER</span><h2>十段公司研究账本</h2></div>
      <p>先读结论与证据状态，再展开事实和限制；缺失项保持缺失。</p>
    </header>
    <div>
      {sections.map((section, index) => <details key={section.key} data-status={section.status} role="group" open={section.status === "triggered"}>
        <summary>
          <span>{String(index + 1).padStart(2, "0")}</span>
          <div><b>{section.label}</b><small>{section.summary}</small></div>
          <em>{statusLabels[section.status]}</em>
        </summary>
        <div className="company-research-section-detail">
          {section.facts.length > 0 && <ul>{section.facts.map((fact) => <li key={fact}>{fact}</li>)}</ul>}
          {section.facts.length === 0 && <p>当前没有更多可核验事实。</p>}
          {section.limitation && <p className="company-research-section-limit">{section.limitation}</p>}
          <small>证据引用 {section.evidence_ids.length} 项</small>
        </div>
      </details>)}
    </div>
  </section>;
}
