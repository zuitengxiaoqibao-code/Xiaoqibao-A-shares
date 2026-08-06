import { act, render, screen } from "@testing-library/react";
import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

import type { QuantStrategyDashboard } from "./types";
import { QuantLiveStatusBar } from "./QuantLiveStatusBar";

const pendingStrategy = {
  candidate_scan_state: "pending",
  candidate_scan_started_at: "2026-08-07T02:59:55.000Z",
  candidate_scan_error: null,
  candidate_scan_phase: "loading_history",
  candidate_scan_processed: null,
  candidate_scan_total: null,
  generated_at: "2026-08-07T03:00:00.000Z",
  data_age_seconds: 0,
  refresh_mode: "live",
  sources: ["local-daily"],
  candidate_scan_cached: false,
  candidate_scan_age_seconds: null,
  trigger_evidence_cached: false,
  trigger_evidence_age_seconds: null,
} as unknown as QuantStrategyDashboard;

describe("QuantLiveStatusBar candidate scan progress", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-08-07T03:00:00.000Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows truthful indeterminate progress and elapsed time while the scan runs", () => {
    render(
      <QuantLiveStatusBar
        board={null}
        boardStatus="live"
        boardLastSuccessAt={null}
        latestTick={null}
        tickStatus="paused"
        strategy={pendingStrategy}
        strategyStatus="live"
        strategyEnabled
      />,
    );

    expect(screen.getByText(/后台预热中 · 首次扫描不会阻塞页面/)).toBeInTheDocument();
    const progress = screen.getByRole("progressbar", { name: "候选扫描后台预热" });
    expect(progress).toHaveAttribute("aria-busy", "true");
    expect(progress).not.toHaveAttribute("aria-valuenow");
    expect(screen.getByText("已运行 5 秒 · 进度由本地扫描决定")).toBeInTheDocument();

    act(() => { vi.advanceTimersByTime(2000); });
    expect(screen.getByText("已运行 7 秒 · 进度由本地扫描决定")).toBeInTheDocument();
  });

  it("uses an exact processed ratio when the backend reports factor progress", () => {
    render(
      <QuantLiveStatusBar
        board={null}
        boardStatus="live"
        boardLastSuccessAt={null}
        latestTick={null}
        tickStatus="paused"
        strategy={{
          ...pendingStrategy,
          candidate_scan_phase: "computing_factors",
          candidate_scan_processed: 25,
          candidate_scan_total: 100,
        }}
        strategyStatus="live"
        strategyEnabled
      />,
    );

    const progress = screen.getByRole("progressbar", { name: "候选扫描后台预热" });
    expect(progress).toHaveAttribute("aria-valuenow", "25");
    expect(screen.getByText("因子扫描 25/100 · 25%")).toBeInTheDocument();
  });
});
