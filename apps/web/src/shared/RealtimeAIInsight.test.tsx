import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RealtimeAIInsight } from "./RealtimeAIInsight";

describe("RealtimeAIInsight", () => {
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
  });
});
