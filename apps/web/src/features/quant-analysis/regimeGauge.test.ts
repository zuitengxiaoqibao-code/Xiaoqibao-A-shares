import { describe, expect, it } from "vitest";

import type { QuantStrategyDashboard } from "./types";
import { regimeGauge } from "./ShortTermStrategyWorkbench";

const dashboard = {
  regime: { regime: "情绪主升", emotion_score: "76" },
} as unknown as QuantStrategyDashboard;

describe("regimeGauge", () => {
  it("keeps scale labels readable and avoids repeating fractional ticks", () => {
    const option = regimeGauge(dashboard);
    const series = option.series as Array<Record<string, any>>;
    const axisLabel = series[0].axisLabel as { formatter: (value: number) => string };

    expect(axisLabel.formatter(0)).toBe("0");
    expect(axisLabel.formatter(50)).toBe("50");
    expect(axisLabel.formatter(100)).toBe("100");
    expect(axisLabel.formatter(33.333333333333336)).toBe("");
    expect(axisLabel).toMatchObject({
      backgroundColor: "#071018",
      fontWeight: 700,
    });
    expect(series[0].detail).toMatchObject({
      lineHeight: 28,
      offsetCenter: [0, "43%"],
      formatter: "{regime|情绪主升}\n{label|情绪 }{score|76.0}",
      rich: {
        regime: { fontSize: 18, fontWeight: 700 },
        score: { fontSize: 22, fontWeight: 800 },
      },
    });
  });
});
