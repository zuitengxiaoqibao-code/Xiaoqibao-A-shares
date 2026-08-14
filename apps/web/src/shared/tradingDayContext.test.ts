import { describe, expect, it } from "vitest";

import { marketPhase, shanghaiDay, isUsableSnapshotDay } from "./tradingDayContext";

describe("trading day context", () => {
  it("uses the Shanghai calendar date across UTC boundaries", () => {
    expect(shanghaiDay(new Date("2026-08-12T15:59:59.000Z"))).toBe("2026-08-12");
    expect(shanghaiDay(new Date("2026-08-12T16:00:00.000Z"))).toBe("2026-08-13");
  });

  it("classifies the market session without treating overnight as live data", () => {
    expect(marketPhase(new Date("2026-08-13T08:59:00+08:00"))).toBe("premarket");
    expect(marketPhase(new Date("2026-08-13T10:00:00+08:00"))).toBe("intraday");
    expect(marketPhase(new Date("2026-08-13T16:00:00+08:00"))).toBe("postclose");
    expect(marketPhase(new Date("2026-08-13T23:00:00+08:00"))).toBe("overnight");
  });

  it("allows a previous close only before the next session opens", () => {
    expect(isUsableSnapshotDay("2026-08-12", new Date("2026-08-13T09:20:00+08:00"))).toBe(true);
    expect(isUsableSnapshotDay("2026-08-12", new Date("2026-08-13T09:30:00+08:00"))).toBe(false);
    expect(isUsableSnapshotDay("2026-08-08", new Date("2026-08-13T09:20:00+08:00"))).toBe(false);
  });
});
