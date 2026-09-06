import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RealtimeAIInsight } from "./RealtimeAIInsight";

describe("RealtimeAIInsight", () => {
  it("presents company research evidence as readable Chinese summary instead of internal fields", () => {
    render(<RealtimeAIInsight domainLabel="公司研究" insight={{
      kind: "company_research",
      reason: "initial_verified_snapshot",
      status: "ready",
      explanation: "Company research evidence for symbol 002279 as of 2026-08-28 with status partial and evidence coverage 0.65.",
      statements: [
        { kind: "fact", text: 'symbol = "002279"' },
        { kind: "fact", text: 'as_of = "2026-08-28"' },
        { kind: "fact", text: 'status = "partial"' },
        { kind: "fact", text: 'research_version.snapshot_id = "company-research-internal"' },
      ],
      generated_at: "2026-08-28T07:36:16Z",
      source: "rules",
      input_snapshot_hash: "1234567890abcdef1234",
      coverage_percent: 65,
      fallback: false,
      missing_fields: ["industry", "valuation"],
    }} />);

    expect(screen.getByText(/公司研究数据已更新/)).toBeInTheDocument();
    expect(screen.getByText("分析标的")).toBeInTheDocument();
    expect(screen.getByText("数据状态")).toBeInTheDocument();
    expect(screen.getByText("部分可用")).toBeInTheDocument();
    expect(screen.getByText(/证据覆盖率 65%/)).toBeInTheDocument();
    expect(screen.getByText("证据覆盖率")).toBeInTheDocument();
    expect(screen.queryByText("变化触发 · AI 证据分析")).toBeInTheDocument();
    expect(screen.queryByText(/symbol =|as_of =|snapshot_id|Company research evidence/)).not.toBeInTheDocument();
    expect(screen.queryByText(/EVENT-TRIGGERED|AI EVIDENCE/)).not.toBeInTheDocument();
    expect(screen.queryByText("1234567890abcdef")).not.toBeInTheDocument();
  });

  it("does not call a configured timeout unconfigured", () => {
    render(<RealtimeAIInsight domainLabel="新闻热点" insight={{
      kind: "news_events",
      reason: "模型请求超时",
      status: "unavailable",
      ai_state: "timeout",
      ai_message: "AI 接口连接超时，已保留规则分析",
      explanation: null,
      statements: [{ kind: "fact", text: "规则事实仍可用" }],
      generated_at: "2026-08-20T10:00:00+08:00",
      source: "rules",
      input_snapshot_hash: "1234567890abcdef1234",
      coverage_percent: 90,
      fallback: true,
      missing_fields: [],
    }} />);

    expect(screen.getByText("AI 接口连接超时，已保留规则分析")).toBeInTheDocument();
    expect(screen.queryByText(/AI 未配置/)).not.toBeInTheDocument();
    expect(screen.getByText("规则事实仍可用")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "实时 AI 数据依据" })).not.toHaveAttribute("open");
  });
});
