import { afterEach, describe, expect, it, vi } from "vitest";

import { loadAShareCandidateScores } from "./api";


describe("A-share candidate score API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests every watchlist symbol with the selected horizon", async () => {
    const payload = {
      as_of: "2026-07-14", horizon: "short_term", factor_version: "a-share-factors-v1",
      universe_size: 8, eligible_size: 7, latest_trade_date: "2026-07-14",
      sources: ["baidu"], items: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify(payload),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadAShareCandidateScores(["600000", "000001"])).resolves.toEqual(payload);

    const requested = new URL(fetchMock.mock.calls[0][0], "http://localhost");
    expect(requested.pathname).toBe("/api/v1/a-shares/candidate-scores");
    expect(requested.searchParams.getAll("symbols")).toEqual(["600000", "000001"]);
    expect(requested.searchParams.get("horizon")).toBe("short_term");
  });
});
