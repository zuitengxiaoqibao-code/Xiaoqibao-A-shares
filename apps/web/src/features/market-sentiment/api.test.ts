import { afterEach, describe, expect, it, vi } from "vitest";

import { loadCurrentMarketSentiment, refreshMarketSentiment } from "./api";


describe("market sentiment api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads the current A-share sentiment response", async () => {
    const payload = { trading_date: "2026-07-18", display_mode: "unavailable" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify(payload),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadCurrentMarketSentiment()).resolves.toEqual(payload);
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/a-shares/market-sentiment/current");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "GET" });
  });

  it("uses POST for refresh and maps raw failures to a safe message", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ snapshot_id: "sentiment-1" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }))
      .mockRejectedValueOnce(new Error("https://secret.example/token"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(refreshMarketSentiment()).resolves.toEqual({ snapshot_id: "sentiment-1" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/a-shares/market-sentiment/refresh");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
    await expect(loadCurrentMarketSentiment()).rejects.toThrow(
      "A 股市场情绪网络连接失败",
    );
  });
});
