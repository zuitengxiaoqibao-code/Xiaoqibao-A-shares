import { afterEach, expect, it, vi } from "vitest";
import { apiClient } from "../../shared/apiClient";
import { loadLateSessionAIAnalysis } from "./api";
import type { LateSessionSelectionResponse } from "./types";

afterEach(() => vi.restoreAllMocks());

it("sends only the server snapshot reference for AI analysis", async () => {
  const post = vi.spyOn(apiClient, "post").mockResolvedValue({ status: "ready" });
  const selection = { snapshot_id: "a".repeat(64), candidate_count: 999 } as LateSessionSelectionResponse;
  await loadLateSessionAIAnalysis(selection);
  expect(post).toHaveBeenCalledWith(
    "/api/v1/a-shares/late-session-selection/ai-analysis",
    { snapshot_id: selection.snapshot_id }, expect.anything(),
  );
});

it("requests a refresh if the selection has no server snapshot", async () => {
  const post = vi.spyOn(apiClient, "post");
  await expect(loadLateSessionAIAnalysis({} as LateSessionSelectionResponse)).rejects.toThrow("请刷新");
  expect(post).not.toHaveBeenCalled();
});
