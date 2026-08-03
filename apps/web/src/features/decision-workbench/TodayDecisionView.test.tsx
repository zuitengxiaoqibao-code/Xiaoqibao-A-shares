import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { MarketSentimentResponse } from "../market-sentiment/types";
import { TodayDecisionView } from "./TodayDecisionView";
import type { DecisionResponse, PhaseSlot } from "./types";
import type { BreakingNewsAlertResponse } from "../news-alerts/types";

const emptySlot: PhaseSlot = {
  phase_status: "empty",
  quality: "empty",
  aggregate_version: null,
  ai_status: "not_requested",
  advice: [],
  evidence: [],
};

const decision: DecisionResponse = {
  server_time: "2026-07-29T10:30:00+08:00",
  trading_date: "2026-07-29",
  current_phase: "intraday",
  market_session: "open",
  phases: { premarket: emptySlot, intraday: emptySlot, postclose: emptySlot },
  polling: {
    status: "normal",
    focus_interval_seconds: 60,
    universe_interval_seconds: 240,
    stale_after_seconds: 180,
    next_check_seconds: 60,
  },
};

const sentiment: MarketSentimentResponse = {
  trading_date: "2026-07-29",
  phase: "intraday",
  display_mode: "unavailable",
  current: null,
  previous_close: null,
  trajectory: [],
};

const alertResponse: BreakingNewsAlertResponse = {
  status: "ready", observed_at: "2026-07-29T10:30:00+08:00", sources: ["证券时报"], warnings: [],
  alerts: [{
    event_id: "decision-alert", headline: "当前股票出现已核验重要事件", occurred_at: "2026-07-29T10:12:00+08:00",
    verification_state: "verified", urgency: "breaking", association_kind: "direct",
    association_reasons: ["security_code:600519"], affected_symbols: ["600519"], themes: [],
    publishers: ["证券时报"], source_urls: ["https://news.example/decision"], source_count: 1,
    impact_direction: "uncertain", impact_confidence: null, ai_degraded: true,
  }],
};

describe("TodayDecisionView", () => {
  it("uses the shared terminal shell and keeps the decision workspaces", async () => {
    render(<TodayDecisionView
      loadCurrent={() => Promise.resolve(decision)}
      loadSentiment={() => Promise.resolve(sentiment)}
    />);

    expect(screen.getByRole("region", { name: "A 股监控首页" })).toHaveClass("terminal-page");
    expect(screen.getByRole("heading", { name: "A 股决策监控" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "研判运行状态" })).toHaveTextContent("全市场");
    expect(screen.getByRole("region", { name: "市场情绪监视窗" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "三阶段决策监视窗" })).toBeInTheDocument();
    expect(await screen.findByRole("tab", { name: "盘中监测" })).toBeInTheDocument();
  });

  it("switches the alert scope between market and the selected stock", async () => {
    const loadAlerts = vi.fn().mockResolvedValue(alertResponse);
    render(<TodayDecisionView
      loadCurrent={() => Promise.resolve(decision)}
      selectedSymbol="600519"
      loadAlerts={loadAlerts}
    />);

    expect(await screen.findByRole("region", { name: "突发事件" })).toHaveTextContent("当前股票出现已核验重要事件");
    expect(loadAlerts).toHaveBeenCalledWith(undefined, expect.any(AbortSignal), 4);

    fireEvent.click(screen.getByRole("button", { name: "只看 600519" }));

    await waitFor(() => expect(loadAlerts).toHaveBeenCalledWith("600519", expect.any(AbortSignal), 4));
  });
});
