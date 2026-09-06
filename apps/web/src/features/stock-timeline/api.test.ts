import { afterEach, describe, expect, it, vi } from "vitest";

import { loadStockTimeline } from "./api";


describe("loadStockTimeline", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("registers stock-observation sampling without letting registration failure block timeline data", async () => {
    const payload = {
      symbol: "600519", as_of: "2026-08-28", cutoff: "2026-08-28T10:00:00+08:00",
      status: "ready", bars: [], events: [], sources: [], warnings: [],
      intraday_status: "waiting", intraday_points: [], intraday_sources: [], intraday_warnings: [],
    };
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/600519/intraday-focus")) return new Response("down", { status: 503 });
      return new Response(JSON.stringify(payload), { status: 200, headers: { "Content-Type": "application/json" } });
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadStockTimeline("600519")).resolves.toEqual(payload);
    await vi.waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
    expect(fetchMock.mock.calls.map(([input]) => String(input))).toEqual(expect.arrayContaining([
      "/api/v1/a-shares/600519/intraday-focus",
      "/api/v1/a-shares/600519/timeline",
    ]));
  });
});
