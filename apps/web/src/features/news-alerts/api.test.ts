import { afterEach, describe, expect, it, vi } from "vitest";

import { loadBreakingNewsAlerts } from "./api";


describe("loadBreakingNewsAlerts", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("loads a symbol-filtered stream without inventing request fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: "empty", observed_at: "2026-07-29T10:30:00+08:00", alerts: [], sources: [], warnings: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await loadBreakingNewsAlerts("600519", controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/news/alerts?symbol=600519&limit=30",
      { signal: controller.signal },
    );
  });

  it("reports the server message when the alert stream fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: () => Promise.resolve({ detail: { message: "新闻证据存档校验失败" } }),
    }));

    await expect(loadBreakingNewsAlerts()).rejects.toThrow("新闻证据存档校验失败");
  });
});
