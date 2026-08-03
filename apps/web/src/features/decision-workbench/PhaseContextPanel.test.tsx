import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PhaseContextPanel, qualityReasonLabel } from "./PhaseContextPanel";

describe("PhaseContextPanel", () => {
  it.each([
    ["live_quotes_unavailable", "盘中行情暂未返回"],
    ["live_quote_quality_blocked", "盘中行情质量未通过"],
    ["live_quote_timestamp_invalid", "盘中行情时间晚于本次评估"],
    ["live_quotes_stale", "盘中行情已超过有效时间"],
    ["risk_unavailable", "市场风险数据不可用"],
    ["compliance_unavailable", "合规检查数据不可用"],
    ["compliance_not_allowed", "当前数据来源未通过合规授权"],
  ])("translates %s into beginner copy", (reason, expected) => {
    expect(qualityReasonLabel(reason)).toBe(expected);
  });

  it("shows verified market topics, industries and candidate fund flow", () => {
    render(<PhaseContextPanel context={{
      market_state: "strong", window_start: null, window_end: null,
      candidate_snapshot_id: "candidate-1", risk_event_count: 0, quality_reasons: [],
      market_overview: {
        summary: "候选因子宽度；已核验热点 1 个",
        hot_topics: ["人工智能"], industries: ["软件服务"],
        pending_hot_topics: ["机器人"], pending_industries: ["电子"],
        fund_flow: { inflow: 2, outflow: 1, available: 3 },
      },
      news: { status: "empty", events: [], missing_event_ids: [], error_code: null },
    }} />);

    expect(screen.getByText("人工智能")).toBeInTheDocument();
    expect(screen.getByText("软件服务")).toBeInTheDocument();
    expect(screen.getByText("流入 2 · 流出 1")).toBeInTheDocument();
    expect(screen.getByText("机器人")).toBeInTheDocument();
    expect(screen.getByText("电子")).toBeInTheDocument();
    expect(screen.getByText("仅作信息流，不进入建议依据")).toBeInTheDocument();
  });

  it("shows the newest three news events first and expands the remaining evidence", () => {
    const events = [1, 5, 2, 4, 3].map((day) => ({
      event_id: `news-${day}`, event_type: "company_update", headline: `新闻 ${day}`,
      occurred_at: `2026-07-${String(day).padStart(2, "0")}T10:00:00+08:00`,
      industries: ["软件"], themes: [], affected_symbols: ["600000"],
      association_confidence: "0.9", publisher: null, source_url: null,
    }));
    render(<PhaseContextPanel context={{
      market_state: "range", window_start: null, window_end: null,
      candidate_snapshot_id: "candidate-1", risk_event_count: 0, quality_reasons: [],
      news: { status: "ready", events, missing_event_ids: [], error_code: null },
    }} />);

    expect(screen.getByText("显示 3 / 共 5 条相关已验证新闻")).toBeInTheDocument();
    expect(screen.getByText("新闻 5")).toBeInTheDocument();
    expect(screen.getByText("新闻 4")).toBeInTheDocument();
    expect(screen.getByText("新闻 3")).toBeInTheDocument();
    expect(screen.queryByText("新闻 2")).not.toBeInTheDocument();
    expect(screen.queryByText("新闻 1")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "查看其余 2 条" }));
    expect(screen.getByText("显示 5 / 共 5 条相关已验证新闻")).toBeInTheDocument();
    expect(screen.getByText("新闻 2")).toBeInTheDocument();
    expect(screen.getByText("新闻 1")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "收起新闻证据" }));
    expect(screen.queryByText("新闻 2")).not.toBeInTheDocument();
  });
});
