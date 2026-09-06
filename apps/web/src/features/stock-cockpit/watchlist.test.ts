import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  hydrateAShareWatchlist,
  readAShareWatchlist,
  writeAShareWatchlist,
} from "./watchlist";


describe("A-share watchlist persistence", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => vi.unstubAllGlobals());

  it("hydrates the local snapshot from the portable application configuration", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(
      JSON.stringify({ symbols: ["600519", "000001"], updated_at: "2026-08-26T02:00:00Z" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));

    await expect(hydrateAShareWatchlist()).resolves.toEqual(["600519", "000001"]);
    expect(readAShareWatchlist()).toEqual(["600519", "000001"]);
  });

  it("keeps the visible local snapshot when remote loading fails", async () => {
    localStorage.setItem("qibao.a_share.watchlist.v1", '["600519"]');
    vi.mocked(fetch).mockRejectedValue(new Error("offline"));

    await expect(hydrateAShareWatchlist()).resolves.toEqual(["600519"]);
    expect(readAShareWatchlist()).toEqual(["600519"]);
  });

  it("writes immediately and persists the same ordered list to the backend", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response(
      JSON.stringify({ symbols: ["600519"], updated_at: "2026-08-26T02:00:00Z" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    ));

    expect(writeAShareWatchlist(["600519", "600519"])).toEqual(["600519"]);
    await vi.waitFor(() => expect(fetch).toHaveBeenCalled());
    const [url, request] = vi.mocked(fetch).mock.calls[0];
    expect(url).toBe("/api/v1/a-shares/watchlist");
    expect(request).toMatchObject({ method: "PUT" });
    expect(JSON.parse(String(request?.body))).toEqual({ symbols: ["600519"] });
  });
});
