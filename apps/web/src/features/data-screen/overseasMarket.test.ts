import { afterEach, describe, expect, it, vi } from "vitest";

import { loadOverseasMarket } from "./overseasMarket";

describe("overseas market api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads all eight US indicators through the shared endpoint", async () => {
    const payload = { quality: "ready", indices: [], mag7: [], trading_label: "美股 2026-09-02 收盘" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadOverseasMarket()).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/market/overseas",
      { method: "GET", signal: expect.any(AbortSignal) },
    );
  });
});
