import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchJsonWithProgress, type LoadProgress } from "./fetchJsonWithProgress";

describe("fetchJsonWithProgress", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("keeps advancing with a clearly labelled estimate while the backend prepares the response", async () => {
    vi.useFakeTimers();
    let release!: (response: Response) => void;
    vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>((resolve) => { release = resolve; })));
    const updates: LoadProgress[] = [];

    const request = fetchJsonWithProgress<{ ok: boolean }>(
      "/api/test",
      undefined,
      (progress) => updates.push(progress),
    );

    expect(updates.at(-1)).toMatchObject({ percent: 1, stage: "connecting", mode: "estimated" });
    await vi.advanceTimersByTimeAsync(2_400);

    const estimated = updates.filter((item) => item.mode === "estimated");
    expect(estimated.length).toBeGreaterThan(3);
    expect(estimated.at(-1)!.percent).toBeGreaterThan(1);
    expect(estimated.at(-1)!.percent).toBeLessThanOrEqual(45);
    expect(estimated.at(-1)!.elapsedMs).toBeGreaterThanOrEqual(2_000);
    expect(estimated.at(-1)!.detail).toContain("阶段估算");

    release(new Response('{"ok":true}', {
      status: 200,
      headers: { "Content-Length": "11", "Content-Type": "application/json" },
    }));
    await expect(request).resolves.toEqual({ ok: true });
    expect(updates.at(-1)).toMatchObject({ percent: 100, stage: "complete", mode: "verified" });
  });

  it("reports real byte progress before parsing and completing", async () => {
    const encoder = new TextEncoder();
    const chunks = [encoder.encode('{"ok":'), encoder.encode("true}")];
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(chunk));
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn(async () => new Response(body, {
      status: 200,
      headers: { "Content-Length": "11", "Content-Type": "application/json" },
    })));
    const updates: LoadProgress[] = [];

    const result = await fetchJsonWithProgress<{ ok: boolean }>(
      "/api/test",
      undefined,
      (progress) => updates.push(progress),
    );

    expect(result).toEqual({ ok: true });
    expect(updates[0]).toMatchObject({ percent: 1, stage: "connecting", mode: "estimated" });
    expect(updates.some((item) => item.stage === "receiving" && item.percent > 5 && item.percent <= 92 && item.mode === "measured")).toBe(true);
    expect(updates.some((item) => item.stage === "parsing" && item.percent === 96 && item.mode === "verified")).toBe(true);
    expect(updates.at(-1)).toMatchObject({ percent: 100, stage: "complete", mode: "verified" });
  });

  it("reports received bytes when content length is unavailable", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response('{"value":1}', {
      status: 200,
      headers: { "Content-Type": "application/json" },
    })));
    const updates: LoadProgress[] = [];

    await fetchJsonWithProgress("/api/test", undefined, (progress) => updates.push(progress));

    expect(updates.some((item) => item.stage === "receiving" && item.detail.includes("字节"))).toBe(true);
    expect(updates.at(-1)?.percent).toBe(100);
  });

  it("uses the API error message without reporting completion", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      detail: { message: "数据源暂不可用" },
    }), { status: 503, headers: { "Content-Type": "application/json" } })));
    const updates: LoadProgress[] = [];

    await expect(fetchJsonWithProgress(
      "/api/test",
      undefined,
      (progress) => updates.push(progress),
      (status) => `请求失败 (${status})`,
    )).rejects.toThrow("数据源暂不可用");
    expect(updates.at(-1)?.stage).not.toBe("complete");
  });

  it("ends a stalled request with a visible timeout instead of leaving the page loading forever", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => (
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      })
    )));

    const request = fetchJsonWithProgress("/api/stalled");
    const assertion = expect(request).rejects.toThrow("请求超时，请稍后重试");
    await vi.advanceTimersByTimeAsync(120_000);
    await assertion;
  });

  it("keeps caller cancellation distinct from a timeout", async () => {
    vi.useFakeTimers();
    vi.stubGlobal("fetch", vi.fn((_input: RequestInfo | URL, init?: RequestInit) => (
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")), { once: true });
      })
    )));
    const controller = new AbortController();
    const request = fetchJsonWithProgress("/api/cancelled", { signal: controller.signal });
    const assertion = expect(request).rejects.toMatchObject({ name: "AbortError" });
    controller.abort();
    await assertion;
  });
});
