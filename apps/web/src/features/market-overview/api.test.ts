import { afterEach, describe, expect, it, vi } from "vitest";

import { loadMarketOverview } from "./api";

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
});
