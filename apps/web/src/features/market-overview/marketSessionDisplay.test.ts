import { describe, expect, it } from "vitest";

import { marketSessionDisplay } from "./marketSessionDisplay";

describe("marketSessionDisplay", () => {
  it("counts down to 09:30 before call auction", () => {
    expect(marketSessionDisplay({
      now: new Date("2026-08-19T09:10:00+08:00"), phase: "premarket", points: [],
    })).toMatchObject({ stage: "waiting_open", secondsToOpen: 1200, title: "等待开盘" });
  });

  it("labels call auction separately and keeps the same opening target", () => {
    expect(marketSessionDisplay({
      now: new Date("2026-08-19T09:20:00+08:00"), phase: "premarket", points: [],
    })).toMatchObject({ stage: "call_auction", secondsToOpen: 600, title: "集合竞价进行中" });
  });

  it("waits for the first verified point after the opening bell", () => {
    expect(marketSessionDisplay({
      now: new Date("2026-08-19T09:30:05+08:00"), phase: "intraday", points: [],
    })).toMatchObject({ stage: "awaiting_first_tick", secondsToOpen: 0, title: "正在接收今日首笔行情" });
  });

  it("does not accept a previous-day minute point as live", () => {
    expect(marketSessionDisplay({
      now: new Date("2026-08-19T09:31:00+08:00"), phase: "intraday",
      points: [{ observed_at: "2026-08-18T15:00:00+08:00", price: "1", volume: "1", amount: "1" }],
    }).stage).toBe("awaiting_first_tick");
  });

  it("switches to live only after a current-day minute arrives", () => {
    expect(marketSessionDisplay({
      now: new Date("2026-08-19T09:31:00+08:00"), phase: "intraday",
      points: [{ observed_at: "2026-08-19T09:31:00+08:00", price: "1", volume: "1", amount: "1" }],
    }).stage).toBe("live");
  });

  it("distinguishes postclose and non-trading days", () => {
    const point = [{ observed_at: "2026-08-19T15:00:00+08:00", price: "1", volume: "1", amount: "1" }];
    expect(marketSessionDisplay({ now: new Date("2026-08-19T15:10:00+08:00"), phase: "postclose", points: point }).stage).toBe("postclose");
    expect(marketSessionDisplay({ now: new Date("2026-08-22T09:20:00+08:00"), phase: "closed", points: [] })).toMatchObject({ stage: "closed", title: "今日休市" });
  });
});
