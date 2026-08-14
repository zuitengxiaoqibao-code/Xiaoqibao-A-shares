import { describe, expect, it } from "vitest";

import { sectorColor } from "./sectorPalette";

describe("sectorColor", () => {
  it("keeps a stable color for the same sector code", () => {
    expect(sectorColor("BK1036")).toBe(sectorColor("BK1036"));
  });

  it("separates common sectors without using the direction colors", () => {
    expect(sectorColor("BK1036")).not.toBe(sectorColor("BK0475"));
    expect(["#ff4d5a", "#16c784", "#8ca0ad"]).not.toContain(sectorColor("BK1036"));
  });
});
