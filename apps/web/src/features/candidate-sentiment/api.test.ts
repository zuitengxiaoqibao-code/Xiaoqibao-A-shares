import { afterEach, describe, expect, it, vi } from "vitest";

import {
  loadCandidateSentiments,
  refreshCandidateSentiments,
} from "./api";


describe("candidate sentiment api", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("posts the candidate snapshot id for current and refresh", async () => {
    const payload = {
      candidate_snapshot_id: "candidate-1",
      candidate_input_hash: "a".repeat(64),
      items: [],
    };
    const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(
      JSON.stringify(payload),
      { status: 200, headers: { "Content-Type": "application/json" } },
    )));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadCandidateSentiments("candidate-1")).resolves.toEqual(payload);
    await expect(refreshCandidateSentiments("candidate-1")).resolves.toEqual(payload);

    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/a-shares/candidate-sentiment/batch");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/a-shares/candidate-sentiment/batch/refresh");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST", body: JSON.stringify({ candidate_snapshot_id: "candidate-1" }) });
    expect(new Headers(fetchMock.mock.calls[0][1]?.headers).get("Content-Type")).toBe("application/json");
  });

  it("uses the API message and hides raw transport details", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({
        detail: { code: "candidate_snapshot_not_found", message: "候选快照已失效" },
      }), { status: 404, headers: { "Content-Type": "application/json" } }))
      .mockRejectedValueOnce(new Error("https://secret.example/token"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadCandidateSentiments("missing")).rejects.toThrow("候选快照已失效");
    await expect(refreshCandidateSentiments("candidate-1")).rejects.toThrow(
      "短线候选情绪网络连接失败",
    );
  });
});
