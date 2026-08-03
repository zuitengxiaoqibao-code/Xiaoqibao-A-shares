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

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/a-shares/candidate-sentiment/batch",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_snapshot_id: "candidate-1" }),
      },
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/a-shares/candidate-sentiment/batch/refresh",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate_snapshot_id: "candidate-1" }),
      },
    );
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
      "短线候选情绪暂不可用，请稍后重试。",
    );
  });
});
