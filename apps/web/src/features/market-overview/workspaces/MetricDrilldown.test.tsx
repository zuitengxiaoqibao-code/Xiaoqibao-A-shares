import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DrilldownMetric, MetricDrilldownPanel } from "./MetricDrilldown";
import { loadWorkspaceState } from "../../../shared/workspace/workspaceState";

describe("MetricDrilldown", () => {
  beforeEach(() => localStorage.clear());
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

  it("remembers the verified symbol set and restores the drilldown filter", () => {
    const selection = {
      label: "涨停家数", value: 2, source: "本地日线",
      stocks: [
        { symbol: "000001", name: "平安银行", reason: "涨停" },
        { symbol: "600519", name: "贵州茅台", reason: "涨停" },
      ],
    };
    const view = render(<MetricDrilldownPanel selection={selection} onClose={vi.fn()} actions={{}} />);
    fireEvent.change(screen.getByRole("textbox", { name: "搜索明细" }), { target: { value: "茅台" } });
    expect(loadWorkspaceState()?.drilldownSymbols["涨停家数"]).toEqual(["000001", "600519"]);
    view.unmount();

    render(<MetricDrilldownPanel selection={selection} onClose={vi.fn()} actions={{}} />);
    expect(screen.getByRole("textbox", { name: "搜索明细" })).toHaveValue("茅台");
    expect(screen.queryByText("平安银行")).not.toBeInTheDocument();
    expect(screen.getByText("贵州茅台")).toBeInTheDocument();
  });
});
