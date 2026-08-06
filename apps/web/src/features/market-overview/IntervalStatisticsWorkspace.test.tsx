import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IntervalStatisticsWorkspace } from "./IntervalStatisticsWorkspace";

describe("IntervalStatisticsWorkspace", () => {
  it("loads a selected date window and renders real interval rows", async () => {
    const load = vi.fn().mockResolvedValue({
      requested_start_date: "2026-07-01",
      requested_end_date: "2026-07-29",
      start_date: "2026-07-01",
      end_date: "2026-07-29",
      observed_at: "2026-07-29T08:30:00Z",
      source: "tdx-local-day",
      quality: "partial",
      universe_count: 1,
      valid_count: 1,
      rows: [{
        symbol: "600010",
        name: "区间样本",
        start_date: "2026-07-01",
        end_date: "2026-07-29",
        start_close: "10",
        end_close: "10.8",
        return_percent: "8",
        amplitude_percent: "12",
        amount_yi: "25",
        source: "tdx-local-day",
      }],
      warnings: [],
      formula_version: "a-share-interval-review-v1",
    });

    render(<IntervalStatisticsWorkspace asOf="2026-07-29" load={load} />);

    await waitFor(() => expect(screen.getByRole("table")).toHaveTextContent("区间样本"));
    expect(screen.getAllByText("+8.00%").length).toBeGreaterThanOrEqual(1);
    expect(load).toHaveBeenCalledWith("2026-07-01", "2026-07-29", expect.any(AbortSignal));
  });

  it("shows the data-source reason when the interval has no verified rows", async () => {
    const load = vi.fn().mockResolvedValue({
      requested_start_date: "2026-07-01",
      requested_end_date: "2026-07-29",
      start_date: null,
      end_date: null,
      observed_at: "2026-07-29T08:30:00Z",
      source: "unavailable",
      quality: "unavailable",
      universe_count: 0,
      valid_count: 0,
      rows: [],
      warnings: ["tdx_vipdoc_unavailable"],
      formula_version: "a-share-interval-review-v1",
    });

    render(<IntervalStatisticsWorkspace asOf="2026-07-29" load={load} />);

    await waitFor(() => expect(screen.getByText(/未返回可验证的区间样本/)).toBeInTheDocument());
    expect(screen.getByText(/tdx_vipdoc_unavailable/)).toBeInTheDocument();
  });
});
