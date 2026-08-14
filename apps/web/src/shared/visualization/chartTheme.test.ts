import { describe, expect, it } from "vitest";

import { chartTheme } from "./chartTheme";

describe("shared chart semantic palette", () => {
  it("keeps market direction, risk, completeness and missing-data roles explicit", () => {
    expect(chartTheme.upColor).toBe("#f04f5f");
    expect(chartTheme.downColor).toBe("#2fcf91");
    expect(chartTheme.liveColor).toBe("#39c8dd");
    expect(chartTheme.unavailableColor).toBe("#7d8993");
    expect([
      chartTheme.riskLowColor,
      chartTheme.riskMediumColor,
      chartTheme.riskHighColor,
    ]).toEqual(["#e5b84b", "#f08c46", "#f04f5f"]);
  });

  it("keeps event attribution colors separate from rise, fall and the live price line", () => {
    const reserved = new Set<string>([
      chartTheme.upColor,
      chartTheme.downColor,
      chartTheme.liveColor,
    ]);
    const eventColors = Object.values(chartTheme.eventColors);

    expect(new Set(eventColors).size).toBe(eventColors.length);
    expect(eventColors.filter((color) => reserved.has(color))).toEqual([]);
  });
});
