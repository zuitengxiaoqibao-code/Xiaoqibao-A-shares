import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DrilldownMetric, MetricDrilldownPanel } from "./MetricDrilldown";

describe("MetricDrilldown", () => {
  it("keeps the whole metric card keyboard-drillable and names stock details", () => {
    const onSelect = vi.fn();
    render(<DrilldownMetric
      item={{ label: "涨停家数", value: 12, source: "本地日线", stocks: [{ symbol: "600519", name: "贵州茅台", reason: "涨停" }] }}
      selected={false}
      onSelect={onSelect}
    >
      <span>涨停家数</span><b>12</b>
    </DrilldownMetric>);

    const trigger = screen.getByRole("button", { name: "筛选：涨停家数 12" });
    fireEvent.click(trigger);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("shows aggregate limitations instead of implying a missing drilldown", () => {
    render(<MetricDrilldownPanel
      selection={{ label: "成交热度", value: "1.20", source: "市场复盘", unavailableReason: "资金流仅覆盖 42% 股票。" }}
      onClose={vi.fn()}
      actions={{}}
    />);

    expect(screen.getByRole("region", { name: "成交热度 明细" })).toBeInTheDocument();
    expect(screen.getByText("资金流仅覆盖 42% 股票。")).toBeInTheDocument();
  });
});
