import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EventImpactPanel } from "./EventImpactPanel";
import type { EventImpactReport } from "./types";

const report: EventImpactReport = {
  status: "partial",
  event_id: "event-1",
  headline: "公司公告",
  event_type: "company_announcement",
  first_published_at: "2026-08-04T02:00:00Z",
  affected_symbols: ["600519"],
  related_sectors: ["白酒"],
  association_confidence: "0.69",
  association_status: "low_confidence",
  duplicate_status: "duplicate_cluster",
  duplicate_article_count: 2,
  targets: [{
    target_type: "stock",
    target_id: "600519",
    status: "partial",
    windows: [
      { horizon_days: 1, status: "ready", baseline_trade_date: "2026-08-03", end_trade_date: "2026-08-04", baseline_close: "100", end_close: "105", return_percent: "5.00", reason: null },
      { horizon_days: 3, status: "ready", baseline_trade_date: "2026-08-03", end_trade_date: "2026-08-06", baseline_close: "100", end_close: "110", return_percent: "10.00", reason: null },
      { horizon_days: 5, status: "unavailable", baseline_trade_date: null, end_trade_date: null, baseline_close: null, end_close: null, return_percent: null, reason: "5_day_market_window_unavailable" },
      { horizon_days: 20, status: "unavailable", baseline_trade_date: null, end_trade_date: null, baseline_close: null, end_close: null, return_percent: null, reason: "20_day_market_window_unavailable" },
    ],
    limitations: ["5_day_market_window_unavailable", "20_day_market_window_unavailable"],
  }, {
    target_type: "sector",
    target_id: "白酒",
    status: "unavailable",
    windows: ([1, 3, 5, 20] as const).map((horizon_days) => ({ horizon_days, status: "unavailable", baseline_trade_date: null, end_trade_date: null, baseline_close: null, end_close: null, return_percent: null, reason: "sector_daily_bar_series_unavailable" })),
    limitations: ["sector_daily_bar_series_unavailable"],
  }],
  evidence_ledger: [],
  limitations: ["low_confidence_association", "5_day_market_window_unavailable"],
};

describe("EventImpactPanel", () => {
  it("uses red for gains, green for losses, and explicit unavailable states", () => {
    render(<EventImpactPanel report={report} />);

    expect(screen.getByRole("region", { name: "新闻事件影响复盘" })).toBeInTheDocument();
    expect(screen.getByText("重复新闻 2 篇")).toBeInTheDocument();
    expect(screen.getByText("关联置信度低")).toBeInTheDocument();
    expect(screen.getByText("+5.00%")).toHaveClass("positive");
    expect(screen.getAllByText("5日")[0].nextElementSibling).toHaveTextContent("不可用");
    expect(screen.getAllByText("板块日线收益不可用").length).toBeGreaterThan(0);
    expect(screen.getByText("5日行情窗口不足")).toBeInTheDocument();
    expect(screen.getByText(/关联置信度不足/)).toBeInTheDocument();
    expect(screen.queryByText(/5_day_market_window_unavailable|low_confidence_association/)).not.toBeInTheDocument();
  });
});
