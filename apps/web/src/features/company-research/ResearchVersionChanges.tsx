import type { CompanyResearchVersion } from "./types";

const categories: Record<CompanyResearchVersion["changes"][number]["category"], string> = {
  conclusion: "结论变化",
  data: "数据变化",
  source: "来源变化",
};

export function ResearchVersionChanges({ version }: { version?: CompanyResearchVersion | null }) {
  if (!version) return null;
  return <section className="research-version-changes" aria-label="研究版本变化">
    <header>
      <div><span>VERSION DIFF</span><h2>研究版本 V{version.version_number}</h2></div>
      <small>{version.previous_snapshot_id ? `相较 V${version.version_number - 1}` : "首个冻结版本"} · {new Date(version.generated_at).toLocaleString("zh-CN", { hour12: false })}</small>
    </header>
    {version.changes.length === 0
      ? <p>本次真实内容与已有版本一致，复用原冻结版本，没有制造重复历史。</p>
      : <div>{version.changes.map((change, index) => <article key={`${change.category}-${change.label}-${index}`} data-category={change.category}>
        <header><b>{change.label}</b><span>{categories[change.category]}</span></header>
        <div><span>上次<small>{change.before ?? "无"}</small></span><i aria-hidden="true">→</i><span>本次<small>{change.after ?? "无"}</small></span></div>
      </article>)}</div>}
  </section>;
}
