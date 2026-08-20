import type { CompanyResearchAIResult } from "./types";

type Props = {
  result?: CompanyResearchAIResult | null;
  loading: boolean;
  error: string;
};

export function CompanyResearchAIInsight({ result = null, loading, error }: Props) {
  return <section className="company-research-ai" aria-label="AI 证据总结与反方审查" aria-busy={loading}>
    <header>
      <div><span>AI EVIDENCE REVIEW</span><h2>AI 证据总结与反方审查</h2></div>
      <small>只读取冻结研究版本，不生成新事实、不改变评分</small>
    </header>
    {loading && !result && <p>正在基于冻结证据进行后台总结，确定性研究内容可正常使用。</p>}
    {error && !result && <p className="error">{error}</p>}
    {result && result.status !== "ready" && <p>{result.ai_message
      ? `${result.ai_message}，完整确定性研究仍可正常查看。`
      : result.status === "unconfigured"
        ? "AI 接口未配置，确定性十段研究不受影响。"
        : "AI 总结暂不可用，已保留完整确定性研究。"}</p>}
    {result?.status === "ready" && result.analysis && <div>
      <article className="company-research-ai-summary"><b>证据摘要</b><p>{result.analysis.executive_summary}</p></article>
      <article><b>反方风险</b>{result.analysis.contrary_risks.length > 0 ? <ul>{result.analysis.contrary_risks.map((risk) => <li key={`${risk.title}-${risk.detail}`}><strong>{risk.title}</strong><span>{risk.detail}</span><small>证据 {risk.evidence_ids.join(" · ")}</small></li>)}</ul> : <p>AI 未在冻结证据中识别额外反方风险。</p>}</article>
      <article><b>继续核验</b><ul>{result.analysis.verification_questions.map((question) => <li key={question}>{question}</li>)}</ul></article>
    </div>}
  </section>;
}
