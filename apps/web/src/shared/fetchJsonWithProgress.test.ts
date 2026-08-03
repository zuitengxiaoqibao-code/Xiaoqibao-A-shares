import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchJsonWithProgress, type LoadProgress } from "./fetchJsonWithProgress";

describe("fetchJsonWithProgress", () => {
  afterEach(() => vi.unstubAllGlobals());

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
    expect(updates[0]).toMatchObject({ percent: 1, stage: "connecting" });
    expect(updates.some((item) => item.stage === "receiving" && item.percent > 5 && item.percent <= 92)).toBe(true);
    expect(updates.some((item) => item.stage === "parsing" && item.percent === 96)).toBe(true);
    expect(updates.at(-1)).toMatchObject({ percent: 100, stage: "complete" });
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
});
