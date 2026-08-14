import { afterEach, describe, expect, it, vi } from "vitest";

import { loadPortfolioRisk, removePortfolioPosition, savePortfolioPosition } from "./api";


describe("portfolio risk API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("uses GET, PUT and DELETE for the local portfolio store", async () => {
    const fetchMock = vi.fn<typeof fetch>().mockImplementation(async () => new Response(
      JSON.stringify({ status: "unavailable" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    await loadPortfolioRisk();
    await savePortfolioPosition({ symbol: "600519", shares: "100", cost_price: "1500" });
    await removePortfolioPosition("600519");

    expect(fetchMock.mock.calls[0]).toEqual(["/api/v1/a-shares/portfolio-risk"]);
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/a-shares/portfolio-risk/positions/600519");
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "PUT" });
    expect(fetchMock.mock.calls[2]).toEqual([
      "/api/v1/a-shares/portfolio-risk/positions/600519",
      { method: "DELETE" },
    ]);
  });
});
