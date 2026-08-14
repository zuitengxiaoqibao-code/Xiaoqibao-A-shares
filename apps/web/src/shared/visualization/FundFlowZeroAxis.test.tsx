import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const chartSpy = vi.fn();

vi.mock("../../features/quant-analysis/QuantChart", () => ({
  QuantChart: ({ option, ariaLabel }: { option: unknown; ariaLabel: string }) => {
    chartSpy(option);
    return <div role="img" aria-label={ariaLabel} />;
  },
}));

import { FundFlowZeroAxis } from "./FundFlowZeroAxis";

describe("FundFlowZeroAxis", () => {
  it("renders verified inflow above zero and outflow below zero", () => {
    chartSpy.mockClear();
    render(<FundFlowZeroAxis inflow={18} outflow={7} available={25} source="阶段候选资金流" observedAt="2026-08-07T10:00:00+08:00" />);

    expect(screen.getByRole("img", { name: "候选资金流入流出零轴图" })).toBeInTheDocument();
    const option = chartSpy.mock.calls.at(-1)?.[0] as { series: Array<{ data: Array<{ value: number }> }> };
    expect(option.series[0].data[0].value).toBe(18);
    expect(option.series[0].data[1].value).toBe(-7);
    expect(screen.getByText(/25 个有效样本/)).toBeInTheDocument();
  });

  it("does not render synthetic zero bars when evidence is unavailable", () => {
    chartSpy.mockClear();
    render(<FundFlowZeroAxis inflow={0} outflow={0} available={0} source="阶段候选资金流" observedAt={null} />);

    expect(screen.getByRole("status", { name: "候选资金流：数据不可用" })).toBeInTheDocument();
    expect(screen.queryByRole("img", { name: "候选资金流入流出零轴图" })).not.toBeInTheDocument();
    expect(chartSpy).not.toHaveBeenCalled();
  });
});
