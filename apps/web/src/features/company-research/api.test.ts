import { afterEach, describe, expect, it, vi } from "vitest";

import { loadCompanyResearch } from "./api";

describe("company research api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the stable company research route with the optional date", async () => {
    const result = { symbol: "600519" };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ progress: { task_id: "task-1", status: "queued", stage: "queued", processed: 0, total: 6, percent: 0, detail: "等待", error: null }, result: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ progress: { task_id: "task-1", status: "succeeded", stage: "complete", processed: 6, total: 6, percent: 100, detail: "完成", error: null }, result }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await loadCompanyResearch("600519", "2026-08-01", controller.signal);

    expect(fetchMock).toHaveBeenNthCalledWith(1,
      "/api/v1/a-shares/600519/company-research/tasks?as_of=2026-08-01",
      { signal: controller.signal, method: "POST" },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2,
      "/api/v1/a-shares/company-research/tasks/task-1",
      { signal: controller.signal },
    );
  });

  it("preserves the verified backend error message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: { message: "财务源暂不可用" } }), { status: 503 })));
    await expect(loadCompanyResearch("600519")).rejects.toThrow("财务源暂不可用");
  });

  it("forwards response progress to the research loading status", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ progress: { task_id: "task-1", status: "running", stage: "financials", processed: 3, total: 6, percent: 50, detail: "财务完成", error: null }, result: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ progress: { task_id: "task-1", status: "succeeded", stage: "complete", processed: 6, total: 6, percent: 100, detail: "完成", error: null }, result: { symbol: "600519" } }), { status: 200 })));
    const updates: number[] = [];

    await loadCompanyResearch(
      "600519",
      undefined,
      undefined,
      (progress) => updates.push(progress.percent),
    );

    expect(updates).toContain(50);
    expect(updates.at(-1)).toBe(100);
  });
});
