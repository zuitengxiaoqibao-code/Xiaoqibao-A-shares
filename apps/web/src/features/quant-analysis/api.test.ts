import { afterEach, describe, expect, it, vi } from "vitest";

import { loadKronosForecast, loadQuantStrategy } from "./api";

describe("loadKronosForecast", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the selected symbol, evidence date and forecast horizon", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ status: "unavailable" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await loadKronosForecast("600000", "2026-07-24", 10);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/a-shares/first-limit-up/quant-forecast?symbol=600000&horizon=10&as_of=2026-07-24",
    );
  });

  it("rejects a non-success response instead of returning fabricated evidence", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("down", { status: 503 })));

    await expect(loadKronosForecast("600000")).rejects.toThrow("Kronos 预测请求失败 (503)");
  });
});

describe("loadQuantStrategy", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the requested recommendation limit", async () => {
    const payload = { status: "partial", candidates: [] };
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadQuantStrategy(8)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/a-shares/quant-strategy?limit=8");
  });
});
