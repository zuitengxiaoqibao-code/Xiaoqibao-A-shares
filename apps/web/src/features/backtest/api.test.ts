import { afterEach, describe, expect, it, vi } from "vitest";

import { runBacktest } from "./api";

afterEach(() => vi.unstubAllGlobals());

describe("backtest API", () => {
  it("uses a fixed research baseline that can buy one lot of high-priced A shares", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ symbol: "600519" }),
    });
    vi.stubGlobal("fetch", fetchMock);

    await runBacktest("600519", { strategy: "momentum_breakout", lookback_window: 30, initial_cash: 500_000 });

    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      strategy: "momentum_breakout",
      lookback_window: 30,
      initial_cash: 500_000,
    });
  });
});
