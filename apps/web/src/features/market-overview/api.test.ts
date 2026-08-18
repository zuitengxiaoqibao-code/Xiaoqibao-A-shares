import { afterEach, describe, expect, it, vi } from "vitest";

import { loadMarketIntervalReview, loadMarketOverview, parseMarketOverviewSseBuffer } from "./api";

describe("market overview api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads the aggregated A-share overview with an abort signal", async () => {
    const payload = { status: "partial", as_of: "2026-07-29" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await expect(loadMarketOverview(controller.signal)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/a-shares/market-overview",
      { signal: controller.signal },
    );
  });

  it("surfaces the structured backend message", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: { code: "overview_unavailable", message: "市场聚合暂不可用" } }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    )));

    await expect(loadMarketOverview()).rejects.toThrow("市场聚合暂不可用");
  });

  it("does not replace abort errors with a network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new DOMException("Aborted", "AbortError")));

    await expect(loadMarketOverview()).rejects.toMatchObject({ name: "AbortError" });
  });

  it("loads an explicit historical interval without using a live snapshot proxy", async () => {
    const payload = { formula_version: "a-share-interval-review-v1", rows: [] };
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await expect(loadMarketIntervalReview("2026-07-01", "2026-07-29", controller.signal)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/a-shares/market-overview/interval?start_date=2026-07-01&end_date=2026-07-29",
      { signal: controller.signal },
    );
  });
});

describe("market overview SSE parser", () => {
  it("parses complete frames and keeps an incomplete frame for the next chunk", () => {
    const first = parseMarketOverviewSseBuffer(
      'event: market_overview\ndata: {"kind":"market_overview","payload":{"status":"ready"}}\n\n' +
      'event: market_overview\ndata: {"kind":"market_overview","payload":{"status":"partial"}}',
    );
    expect(first.events).toHaveLength(1);
    expect(first.events[0].status).toBe("ready");
    expect(first.rest).toContain('"status":"partial"');

    const second = parseMarketOverviewSseBuffer(`${first.rest}\n\n`);
    expect(second.events).toHaveLength(1);
    expect(second.events[0].status).toBe("partial");
  });

  it("ignores keep-alive and unrelated event frames", () => {
    const result = parseMarketOverviewSseBuffer(
      ': keep-alive\n\n' +
      'event: news_events\ndata: {"kind":"news_events","payload":{}}\n\n',
    );
    expect(result.events).toEqual([]);
    expect(result.rest).toBe("");
  });
});
