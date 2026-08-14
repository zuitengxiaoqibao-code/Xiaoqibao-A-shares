import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

  it("turns summary counts into exact named filters with all research destinations", async () => {
    const load = vi.fn().mockResolvedValue({
      requested_start_date: "2026-07-01", requested_end_date: "2026-07-29",
      start_date: "2026-07-01", end_date: "2026-07-29", observed_at: "2026-07-29T08:30:00Z",
      source: "tdx-local-day", quality: "ready", universe_count: 2, valid_count: 2,
      rows: [
        { symbol: "600010", name: "上涨样本", start_date: "2026-07-01", end_date: "2026-07-29", start_close: "10", end_close: "10.8", return_percent: "8", amplitude_percent: "12", amount_yi: "25", source: "tdx-local-day" },
        { symbol: "600011", name: "下跌样本", start_date: "2026-07-01", end_date: "2026-07-29", start_close: "10", end_close: "9.5", return_percent: "-5", amplitude_percent: "9", amount_yi: "18", source: "tdx-local-day" },
      ],
      warnings: [], formula_version: "a-share-interval-review-v1",
    });
    const onOpenAShare = vi.fn();
    const onOpenCompanyResearch = vi.fn();
    const onOpenQuantAnalysis = vi.fn();

    render(<IntervalStatisticsWorkspace
      asOf="2026-07-29"
      load={load}
      onOpenAShare={onOpenAShare}
      onOpenCompanyResearch={onOpenCompanyResearch}
      onOpenQuantAnalysis={onOpenQuantAnalysis}
    />);

    await waitFor(() => expect(screen.getByRole("button", { name: "筛选：区间上涨 1" })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "筛选：区间上涨 1" }));
    const detail = screen.getByRole("region", { name: "区间上涨 明细" });
    expect(detail).toHaveTextContent("上涨样本");
    expect(detail).not.toHaveTextContent("下跌样本");
    fireEvent.click(within(detail).getByRole("button", { name: "个股观察：600010 上涨样本" }));
    fireEvent.click(within(detail).getByRole("button", { name: "公司研究：600010 上涨样本" }));
    fireEvent.click(within(detail).getByRole("button", { name: "量化分析：600010 上涨样本" }));
    expect(onOpenAShare).toHaveBeenCalledWith("600010");
    expect(onOpenCompanyResearch).toHaveBeenCalledWith("600010");
    expect(onOpenQuantAnalysis).toHaveBeenCalledWith("600010");
  });
});
