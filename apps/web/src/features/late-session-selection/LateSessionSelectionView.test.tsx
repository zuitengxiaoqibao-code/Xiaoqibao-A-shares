import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LateSessionSelectionView } from "./LateSessionSelectionView";

const response = {
  status: "partial" as const, trading_date: "2026-08-17", server_time: "2026-08-17T06:30:00Z",
  phase: "live_monitor" as const, refresh_interval_ms: 1000, next_refresh_ms: 1000,
  source_quality: "partial" as const, universe_count: 1, quote_count: 1, candidate_count: 0,
  rules: [{ key: "change_percent", label: "涨幅", actual: "5", target: "3%–6%", status: "passed" as const, detail: "实际 5" }],
  candidates: [], behaviors: [{ key: "weak_rally", title: "尾盘拉升量能不足", level: "risk" as const, description: "风险", evidence: ["需要分时"] }],
  source_evidence: ["通达信本地全市场实时快照"], limitations: ["分时黄线不可用"],
};

describe("LateSessionSelectionView", () => {
  it("shows phase, strict rule result and honest limitation", async () => {
    const load = vi.fn().mockResolvedValue(response);
    render(<LateSessionSelectionView load={load} />);
    await waitFor(() => expect(screen.getByText("14:30–15:00实时监控")).toBeInTheDocument());
    expect(screen.getByText("涨幅")).toBeInTheDocument();
    expect(screen.getByText("当前没有完整通过七项规则的股票")).toBeInTheDocument();
    expect(screen.getAllByText("分时黄线不可用").length).toBeGreaterThan(0);
  });
});
