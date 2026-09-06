import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CompanyResearchAIInsight } from "./CompanyResearchAIInsight";

describe("CompanyResearchAIInsight", () => {
  it("shows AI counter-case as a separate evidence-bound supplement", () => {
    render(<CompanyResearchAIInsight loading={false} error="" result={{
      status: "ready", snapshot_id: "version-2", provider: "openai-compatible", model: "model",
      prompt_version: "company-research-ai-v1", generated_at: "2026-08-12T15:00:00+08:00",
      analysis: {
        executive_summary: "现金流证据较强，但估值风险仍需核验。",
        contrary_risks: [{ title: "估值压力", detail: "估值规则已触发。", evidence_ids: ["risk-1"] }],
        verification_questions: ["现金流能否继续覆盖利润？"],
      },
    }} />);

    const region = screen.getByRole("region", { name: "AI 证据总结与反方审查" });
    expect(region).toHaveTextContent("现金流证据较强");
    expect(region).toHaveTextContent("估值压力");
    expect(region).not.toHaveTextContent("risk-1");
    expect(region).toHaveTextContent("已绑定 1 条研究证据");
    expect(region).toHaveTextContent("不生成新事实");
  });

  it("shows a configured provider failure instead of calling it unconfigured", () => {
    render(<CompanyResearchAIInsight loading={false} error="" result={{
      status: "http_error", snapshot_id: "version-2", provider: "openai-compatible", model: "model",
      prompt_version: "company-research-ai-v1", generated_at: "2026-08-12T15:00:00+08:00",
      ai_state: "rate_limited", ai_message: "AI 接口触发限流，稍后将自动重试", analysis: null,
    }} />);

    expect(screen.getByText(/AI 接口触发限流/)).toBeInTheDocument();
    expect(screen.getByText(/完整确定性研究仍可正常查看/)).toBeInTheDocument();
    expect(screen.queryByText(/未配置/)).not.toBeInTheDocument();
  });
});
