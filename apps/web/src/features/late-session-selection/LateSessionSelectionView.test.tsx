import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { LateSessionSelectionView } from "./LateSessionSelectionView";
import type { LateSessionAIAnalysis } from "./types";

const response = {
  status: "partial" as const, trading_date: "2026-08-17", server_time: "2026-08-17T06:30:00Z",
  phase: "live_monitor" as const, refresh_interval_ms: 1000, next_refresh_ms: 1000,
  source_quality: "partial" as const, universe_count: 1, quote_count: 1, candidate_count: 0,
  data_state: "no_candidates" as const, no_data_reason: "全市场已扫描 1 只，但分时黄线不可用导致严格筛选无法完成",
  rules: [{ key: "change_percent", label: "涨幅", actual: "5", target: "3%–6%", status: "passed" as const, detail: "实际 5" }],
  settings: { time_enabled: true, start_time: "14:30:00", end_time: "15:00:00", change_enabled: true, change_min: "3", change_max: "6", volume_ratio_enabled: true, volume_ratio_min: "2", volume_ratio_max: "5", turnover_rate_enabled: true, turnover_rate_min: "6", turnover_rate_max: "15", market_cap_enabled: true, market_cap_min: "60", market_cap_max: "300", twenty_day_limit_up_enabled: true, twenty_day_limit_up_min: 1, twenty_day_limit_up_max: null, intraday_average_enabled: true, intraday_relation: "above" as const },
  default_settings: { time_enabled: true, start_time: "14:30:00", end_time: "15:00:00", change_enabled: true, change_min: "3", change_max: "6", volume_ratio_enabled: true, volume_ratio_min: "2", volume_ratio_max: "5", turnover_rate_enabled: true, turnover_rate_min: "6", turnover_rate_max: "15", market_cap_enabled: true, market_cap_min: "60", market_cap_max: "300", twenty_day_limit_up_enabled: true, twenty_day_limit_up_min: 1, twenty_day_limit_up_max: null, intraday_average_enabled: true, intraday_relation: "above" as const },
  candidates: [], behaviors: [{ key: "weak_rally", title: "尾盘拉升量能不足", level: "risk" as const, description: "风险", evidence: ["需要分时"] }],
  source_evidence: ["通达信本地全市场实时快照"], limitations: ["分时黄线不可用"],
};

const analysis: LateSessionAIAnalysis = {
  status: "no_candidates", mode: "unavailable", title: "暂不生成 AI 结论",
  summary: "当前没有产生候选股票。", key_points: [], risk_points: [], data_gaps: ["分时黄线不可用"],
  candidate_count: 0, source_evidence: ["通达信本地全市场实时快照"], observed_at: response.server_time,
  reason: response.no_data_reason,
};

describe("LateSessionSelectionView", () => {
  it("shows phase, strict rule result and honest limitation", async () => {
    let resolve!: (value: typeof response) => void;
    const pending = new Promise<typeof response>((done) => { resolve = done; });
    const load = vi.fn((_settings, onProgress) => {
      onProgress?.({ percent: 42, stage: "receiving", mode: "estimated", detail: "正在扫描真实行情" });
      return pending;
    });
    const analyze = vi.fn().mockResolvedValue(analysis);
    render(<LateSessionSelectionView load={load} analyze={analyze} />);
    expect(screen.getByRole("progressbar", { name: "尾盘选股最新数据加载进度" })).toHaveAttribute("aria-valuenow", "42");
    resolve(response);
    await waitFor(() => expect(screen.getByText("14:30–15:00实时监控")).toBeInTheDocument());
    expect(screen.getAllByText("涨幅").length).toBeGreaterThan(0);
    expect(screen.getByText("当前没有完整通过当前规则的股票")).toBeInTheDocument();
    expect(screen.getByText("自由设定筛选规则")).toBeInTheDocument();
    expect(screen.getAllByText("分时黄线不可用").length).toBeGreaterThan(0);
    await waitFor(() => expect(screen.getByText("暂不生成 AI 结论")).toBeInTheDocument());
    expect(screen.getAllByText(response.no_data_reason).length).toBeGreaterThan(0);
    expect(analyze).toHaveBeenCalled();
  });
});
