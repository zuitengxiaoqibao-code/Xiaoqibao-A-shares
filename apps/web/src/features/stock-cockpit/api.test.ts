import { afterEach, describe, expect, it, vi } from "vitest";

import { loadStockCockpit, loadStockCockpitAI, loadStockQuotePulse } from "./api";


describe("stock cockpit API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests AI explanation through the non-blocking follow-up query", async () => {
    const payload = { symbol: "600000", ai_status: "ready" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify(payload),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadStockCockpitAI("600000", "2026-07-15")).resolves.toEqual(payload);

    const requested = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(requested.pathname).toBe("/api/v1/a-shares/600000/cockpit");
    expect(requested.searchParams.get("as_of")).toBe("2026-07-15");
    expect(requested.searchParams.get("include_ai")).toBe("true");
  });

  it("forwards truthful response progress to the cockpit", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ symbol: "600000" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    )));
    const updates: number[] = [];

    await loadStockCockpit(
      "600000",
      undefined,
      undefined,
      (progress) => updates.push(progress.percent),
    );

    expect(updates[0]).toBe(1);
    expect(updates.at(-1)).toBe(100);
  });

  it("reads the lightweight realtime quote pulse endpoint", async () => {
    const payload = { symbol: "600000", status: "ready", freshness: "live" };
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify(payload),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);
    await expect(loadStockQuotePulse("600000")).resolves.toEqual(payload);
    const requested = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(requested.pathname).toBe("/api/v1/a-shares/600000/quote-pulse");
  });
});
