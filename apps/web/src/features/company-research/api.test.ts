import { afterEach, describe, expect, it, vi } from "vitest";

import { loadCompanyResearch } from "./api";

describe("company research api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the stable company research route with the optional date", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ symbol: "600519" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await loadCompanyResearch("600519", "2026-08-01", controller.signal);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/a-shares/600519/company-research?as_of=2026-08-01",
      { signal: controller.signal },
    );
  });

  it("preserves the verified backend error message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: { message: "财务源暂不可用" } }), { status: 503 })));
    await expect(loadCompanyResearch("600519")).rejects.toThrow("财务源暂不可用");
  });

  it("forwards response progress to the research loading status", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ symbol: "600519" }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    )));
    const updates: number[] = [];

    await loadCompanyResearch(
      "600519",
      undefined,
      undefined,
      (progress) => updates.push(progress.percent),
    );

    expect(updates[0]).toBe(1);
    expect(updates.at(-1)).toBe(100);
  });
});
