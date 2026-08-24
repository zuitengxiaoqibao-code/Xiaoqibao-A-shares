import { afterEach, describe, expect, it, vi } from "vitest";

import { loadCompanyResearch, loadCompanyResearchComparison } from "./api";
import { readTaskActivities, resetTaskActivityForTests } from "../../shared/taskActivity";

describe("company research api", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
    resetTaskActivityForTests();
  });

  it("requests the stable company research route with the optional date", async () => {
    const result = { symbol: "600519" };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "暂无缓存" }), { status: 404 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ progress: { task_id: "task-1", status: "queued", stage: "queued", processed: 0, total: 6, percent: 0, detail: "等待", error: null }, result: null }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ progress: { task_id: "task-1", status: "succeeded", stage: "complete", processed: 6, total: 6, percent: 100, detail: "完成", error: null }, result }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();

    await loadCompanyResearch("600519", "2026-08-01", controller.signal);

    expect(fetchMock).toHaveBeenNthCalledWith(1,
      "/api/v1/a-shares/600519/company-research?as_of=2026-08-01&cache_only=true",
      expect.objectContaining({ method: "GET", signal: expect.any(AbortSignal) }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2,
      "/api/v1/a-shares/600519/company-research/tasks?as_of=2026-08-01",
      expect.objectContaining({ signal: expect.any(AbortSignal), method: "POST" }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(3,
      "/api/v1/a-shares/company-research/tasks/task-1",
      { signal: expect.any(AbortSignal) },
    );
  });

  it("preserves the verified backend error message", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ detail: { message: "财务源暂不可用" } }), { status: 503 })));
    await expect(loadCompanyResearch("600519")).rejects.toThrow("财务源暂不可用");
  });

  it("forwards response progress to the research loading status", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "暂无缓存" }), { status: 404 }))
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

  it("ends a stalled research poll with a Chinese stage error", async () => {
    vi.useFakeTimers();
    const running = { progress: { task_id: "task-stalled", status: "running", stage: "financials", processed: 2, total: 6, percent: 33.33, detail: "正在等待财务来源", error: null }, result: null };
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "暂无缓存" }), { status: 404 }))
      .mockImplementation(async () => new Response(JSON.stringify(running), { status: 200 })));

    const pending = loadCompanyResearch("600519");
    await vi.advanceTimersByTimeAsync(1);
    const assertion = expect(pending).rejects.toThrow("公司研究停滞：正在等待财务来源超过10秒无进展");
    await vi.advanceTimersByTimeAsync(11_000);
    await assertion;

    expect(readTaskActivities()[0]).toMatchObject({
      id: "company-research:600519:latest",
      state: "failed",
      stage: "公司研究失败",
      error: "公司研究停滞：正在等待财务来源超过10秒无进展",
    });
  });

  it("posts a bounded set of verified symbols for comparison", async () => {
    const payload = { status: "partial", as_of: "2026-08-14", generated_at: "2026-08-14T08:00:00Z", companies: [], sources: [], limitations: [] };
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      expect(init?.method).toBe("POST");
      expect(init?.body).toContain("600519");
      return new Response(JSON.stringify(payload), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    await expect(loadCompanyResearchComparison(["600519", "000001"])).resolves.toEqual(payload);
  });
});
