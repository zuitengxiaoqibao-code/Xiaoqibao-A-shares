import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MarketDataWatermarkCenter } from "./MarketDataWatermarkCenter";

describe("MarketDataWatermarkCenter", () => {
  it("shows dominant date, coverage, fragmented records, and blockers", () => {
    render(<MarketDataWatermarkCenter watermark={{
      dominant_trade_date: "2026-08-10",
      latest_available_trade_date: "2026-08-11",
      universe_count: 5200,
      history_ready_count: 5000,
      coverage_percent: "96.15",
      fragmented_latest_count: 4,
      missing_history_count: 200,
      quality: "partial",
      blockers: ["history_dates_fragmented"],
    }} />);

    expect(screen.getByRole("region", { name: "全市场数据水位中心" })).toBeInTheDocument();
    expect(screen.getByText("2026-08-10")).toBeInTheDocument();
    expect(screen.getByText("96.2%")).toBeInTheDocument();
    expect(screen.getByText("4 只")).toBeInTheDocument();
    expect(screen.getByText("历史日期存在零散分片")).toBeInTheDocument();
  });

  it("translates backend history blocker codes into readable Chinese labels", () => {
    render(<MarketDataWatermarkCenter watermark={{
      dominant_trade_date: "2026-07-29",
      latest_available_trade_date: "2026-08-13",
      universe_count: 5296,
      history_ready_count: 5121,
      coverage_percent: "96.7",
      fragmented_latest_count: 175,
      missing_history_count: 175,
      quality: "partial",
      blockers: [
        "tdx_daily_history_unavailable",
        "history_not_ready_for_all_symbols",
        "history_coverage_below_98_percent",
      ],
    }} />);

    expect(screen.getByText("通达信本地日线历史不可用")).toBeInTheDocument();
    expect(screen.getByText("仍有股票未达到完整历史要求")).toBeInTheDocument();
    expect(screen.getByText("历史覆盖率低于 98% 就绪门槛")).toBeInTheDocument();
    expect(screen.queryByText("history_not_ready_for_all_symbols")).not.toBeInTheDocument();
  });
});
