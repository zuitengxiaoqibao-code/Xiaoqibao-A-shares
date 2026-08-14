import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const chartSpy = vi.fn();

vi.mock("../quant-analysis/QuantChart", () => ({
  QuantChart: ({ option, ariaLabel }: { option: unknown; ariaLabel: string }) => {
    chartSpy(option);
    return <div role="img" aria-label={ariaLabel} />;
  },
}));

import { ValuationComparisonChart } from "./ValuationComparisonChart";

describe("ValuationComparisonChart", () => {
  it("compares current PE and PB with verified peer medians", () => {
    chartSpy.mockClear();
    render(<ValuationComparisonChart pe={25} pb={4.2} peerPe={30} peerPb={3.8} source="腾讯行情" observedAt="2026-08-07T15:00:00+08:00" />);

    expect(screen.getByRole("img", { name: "当前估值与同行中位双轴图" })).toBeInTheDocument();
    const option = chartSpy.mock.calls.at(-1)?.[0] as { series: Array<{ data: Array<number | null> }> };
    expect(option.series[0].data).toEqual([25, 30]);
    expect(option.series[1].data).toEqual([4.2, 3.8]);
    expect(screen.getByText(/历史估值序列尚未接入/)).toBeInTheDocument();
  });

  it("keeps missing peer values null instead of substituting zero", () => {
    chartSpy.mockClear();
    render(<ValuationComparisonChart pe={25} pb={null} peerPe={null} peerPb={null} source="腾讯行情" observedAt={null} />);

    const option = chartSpy.mock.calls.at(-1)?.[0] as { series: Array<{ data: Array<number | null> }> };
    expect(option.series[0].data).toEqual([25, null]);
    expect(option.series[1].data).toEqual([null, null]);
    expect(JSON.stringify(option)).not.toContain("NaN");
  });
});
