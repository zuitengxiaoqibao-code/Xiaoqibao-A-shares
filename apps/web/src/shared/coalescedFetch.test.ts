import { afterEach, describe, expect, it, vi } from "vitest";

import { coalescedFetch, readCoalescedFetchStats, resetCoalescedFetchForTests, setCoalescedFetchConcurrencyForTests } from "./coalescedFetch";

afterEach(() => {
  resetCoalescedFetchForTests();
  vi.unstubAllGlobals();
});

describe("coalescedFetch", () => {
  it("starts a fresh request immediately after the last caller cancels", async () => {
    const fetchMock = vi.fn()
      .mockImplementationOnce((_input: RequestInfo | URL, init?: RequestInit) => new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
      }))
      .mockResolvedValueOnce(new Response("fresh"));
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    const first = coalescedFetch("/api/retry", { signal: controller.signal });
    const cancelled = expect(first).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    const second = coalescedFetch("/api/retry");
    await cancelled;
    expect(await (await second).text()).toBe("fresh");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("shares one in-flight GET while returning an independent response to every caller", async () => {
    let resolveFetch!: (response: Response) => void;
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolveFetch = resolve; }));
    vi.stubGlobal("fetch", fetchMock);

    const first = coalescedFetch("/api/v1/a-shares/market-overview");
    const second = coalescedFetch("/api/v1/a-shares/market-overview");
    resolveFetch(new Response(JSON.stringify({ value: 7 }), { headers: { "Content-Type": "application/json" } }));

    expect(await (await first).json()).toEqual({ value: 7 });
    expect(await (await second).json()).toEqual({ value: 7 });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(readCoalescedFetchStats()).toMatchObject({ callers: 2, networkRequests: 1, coalescedCallers: 1 });
  });

  it("does not merge requests whose URL or headers differ", async () => {
    const fetchMock = vi.fn(async () => new Response("ok"));
    vi.stubGlobal("fetch", fetchMock);

    await Promise.all([
      coalescedFetch("/api/value?a=1", { headers: { Accept: "application/json" } }),
      coalescedFetch("/api/value?a=2", { headers: { Accept: "application/json" } }),
      coalescedFetch("/api/value?a=1", { headers: { Accept: "text/plain" } }),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("merges equivalent GET requests whose query parameters use a different order", async () => {
    let resolveFetch!: (response: Response) => void;
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolveFetch = resolve; }));
    vi.stubGlobal("fetch", fetchMock);

    const first = coalescedFetch("/api/value?symbol=600519&limit=20");
    const second = coalescedFetch("/api/value?limit=20&symbol=600519");
    resolveFetch(new Response("ready"));

    await expect((await first).text()).resolves.toBe("ready");
    await expect((await second).text()).resolves.toBe("ready");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("never coalesces non-GET requests", async () => {
    const fetchMock = vi.fn(async () => new Response("ok"));
    vi.stubGlobal("fetch", fetchMock);

    await Promise.all([
      coalescedFetch("/api/tasks", { method: "POST" }),
      coalescedFetch("/api/tasks", { method: "POST" }),
    ]);

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("lets one caller abort without cancelling the shared request for another caller", async () => {
    let resolveFetch!: (response: Response) => void;
    let networkSignal: AbortSignal | null = null;
    const fetchMock = vi.fn((request: RequestInfo | URL, init?: RequestInit) => {
      networkSignal = request instanceof Request ? request.signal : init?.signal ?? null;
      return new Promise<Response>((resolve) => { resolveFetch = resolve; });
    });
    vi.stubGlobal("fetch", fetchMock);
    const firstController = new AbortController();

    const first = coalescedFetch("/api/shared", { signal: firstController.signal });
    const second = coalescedFetch("/api/shared");
    firstController.abort();
    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    expect((networkSignal as AbortSignal | null)?.aborted).toBe(false);

    resolveFetch(new Response("ready"));
    await expect((await second).text()).resolves.toBe("ready");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("aborts the underlying GET after every subscriber has cancelled", async () => {
    let networkSignal: AbortSignal | null = null;
    const fetchMock = vi.fn((request: RequestInfo | URL, init?: RequestInit) => {
      networkSignal = request instanceof Request ? request.signal : init?.signal ?? null;
      return new Promise<Response>((_resolve, reject) => {
        networkSignal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      });
    });
    vi.stubGlobal("fetch", fetchMock);
    const firstController = new AbortController();
    const secondController = new AbortController();

    const first = coalescedFetch("/api/shared", { signal: firstController.signal });
    const second = coalescedFetch("/api/shared", { signal: secondController.signal });
    firstController.abort();
    secondController.abort();

    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    await expect(second).rejects.toMatchObject({ name: "AbortError" });
    expect((networkSignal as AbortSignal | null)?.aborted).toBe(true);
  });

  it("releases failed entries so a later call performs a real retry", async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(new Response("recovered"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(coalescedFetch("/api/retry")).rejects.toThrow("offline");
    await expect((await coalescedFetch("/api/retry")).text()).resolves.toBe("recovered");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("limits concurrent network requests inside one API domain", async () => {
    setCoalescedFetchConcurrencyForTests(2);
    const resolvers: Array<(response: Response) => void> = [];
    const fetchMock = vi.fn(() => new Promise<Response>((resolve) => { resolvers.push(resolve); }));
    vi.stubGlobal("fetch", fetchMock);

    const requests = [
      coalescedFetch("/api/v1/a-shares/value-a"),
      coalescedFetch("/api/v1/a-shares/value-b"),
      coalescedFetch("/api/v1/a-shares/value-c"),
    ];
    await Promise.resolve();
    expect(fetchMock).toHaveBeenCalledTimes(2);

    resolvers[0](new Response("a"));
    await requests[0];
    await Promise.resolve();
    expect(fetchMock).toHaveBeenCalledTimes(3);

    resolvers[1](new Response("b"));
    resolvers[2](new Response("c"));
    await Promise.all(requests.slice(1));
  });
});
