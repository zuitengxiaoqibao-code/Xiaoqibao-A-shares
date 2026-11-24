import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient, resetApiClientForTests } from "./apiClient";
import { resetCoalescedFetchForTests } from "./coalescedFetch";

afterEach(() => {
  resetApiClientForTests();
  resetCoalescedFetchForTests();
  vi.unstubAllGlobals();
});

describe("apiClient", () => {
  it.each(["get", "getOptional"] as const)("keeps %s timeout active while the response body stalls", async (method) => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, status: 200,
      text: () => new Promise<string>(() => {}),
    })));
    await expect(apiClient[method]("/api/slow-body", {
      context: "行情数据", timeoutMs: 15,
    })).rejects.toThrow("行情数据请求超时");
  });

  it("cancels a body read after headers have arrived", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({
      ok: true, status: 200,
      text: () => new Promise<string>(() => {}),
    })));
    const controller = new AbortController();
    const request = apiClient.getOptional("/api/slow-body", { signal: controller.signal });
    await new Promise((resolve) => setTimeout(resolve, 5));
    controller.abort();
    await expect(request).rejects.toMatchObject({ name: "AbortError" });
  });

  it("returns parsed JSON and response provenance for a GET", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ value: 7 }),
      { headers: { "Content-Type": "application/json", "X-Qibao-Source": "local-tdx", "X-Qibao-State": "ready" } },
    )));

    const result = await apiClient.getResult<{ value: number }>("/api/value", { context: "行情数据" });

    expect(result.data).toEqual({ value: 7 });
    expect(result.meta).toMatchObject({ cacheState: "live", source: "local-tdx", state: "ready", statusCode: 200 });
  });

  it("turns an English service failure into a contextual Chinese error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(
      JSON.stringify({ detail: "upstream provider failed" }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    )));

    await expect(apiClient.get("/api/value", { context: "公司研究" })).rejects.toThrow("公司研究服务暂不可用");
  });

  it("stops an unbounded request at the configured timeout with a Chinese reason", async () => {
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
    })));

    await expect(apiClient.get("/api/slow", { context: "量化分析", timeoutMs: 5 })).rejects.toThrow("量化分析请求超时");
  });

  it("returns the last good value with stale metadata when an explicit refresh fails", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ value: 7 }), { headers: { "Content-Type": "application/json" } }))
      .mockRejectedValueOnce(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);

    await apiClient.getCached<{ value: number }>("/api/value", { cacheKey: "value", context: "行情数据" });
    const fallback = await apiClient.getCached<{ value: number }>("/api/value", { cacheKey: "value", context: "行情数据", refresh: true });

    expect(fallback.data).toEqual({ value: 7 });
    expect(fallback.meta.cacheState).toBe("stale");
    expect(fallback.meta.error).toContain("网络连接失败");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("never retries a side-effect request automatically", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(apiClient.post("/api/tasks", { value: 1 }, { context: "创建任务" })).rejects.toThrow("网络连接失败");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("returns null for an explicitly optional resource that is not found", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("", { status: 404 })));

    await expect(apiClient.getOptional("/api/optional", { context: "缓存诊断" })).resolves.toBeNull();
  });
});
