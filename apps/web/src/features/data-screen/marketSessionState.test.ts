import { describe, expect, it } from "vitest";

import { dataScreenSessionLabel, dataScreenSessionState } from "./marketSessionState";

describe("data screen session state", () => {
  it("keeps the previous close visible overnight and waits only after 08:00", () => {
    expect(dataScreenSessionState("premarket", new Date("2026-09-04T06:30:00+08:00"))).toBe("closed");
    expect(dataScreenSessionState("premarket", new Date("2026-09-04T08:01:00+08:00"))).toBe("waiting_open");
    expect(dataScreenSessionLabel("waiting_open")).toBe("等待开盘中");
  });

  it("keeps postclose data available and marks intraday as live", () => {
    expect(dataScreenSessionState("postclose", new Date("2026-09-04T16:00:00+08:00"))).toBe("postclose");
    expect(dataScreenSessionState("intraday", new Date("2026-09-04T10:00:00+08:00"))).toBe("live");
  });
});
