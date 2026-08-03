import { friendlyError } from "../../shared/friendlyError";
import type { CandidateSentimentBatch } from "./types";


class CandidateSentimentAPIError extends Error {}

async function request(
  endpoint: string,
  candidateSnapshotId: string,
): Promise<CandidateSentimentBatch> {
  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_snapshot_id: candidateSnapshotId }),
    });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new CandidateSentimentAPIError(
        body.detail?.message
        ?? body.detail?.code
        ?? `短线候选情绪请求失败 (${response.status})`,
      );
    }
    return response.json();
  } catch (error) {
    if (error instanceof CandidateSentimentAPIError) throw error;
    throw new Error(friendlyError(error, "短线候选情绪"));
  }
}

export const loadCandidateSentiments = (candidateSnapshotId: string) =>
  request("/api/v1/a-shares/candidate-sentiment/batch", candidateSnapshotId);

export const refreshCandidateSentiments = (candidateSnapshotId: string) =>
  request(
    "/api/v1/a-shares/candidate-sentiment/batch/refresh",
    candidateSnapshotId,
  );
