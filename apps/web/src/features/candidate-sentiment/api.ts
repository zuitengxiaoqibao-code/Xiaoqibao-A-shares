import { apiClient } from "../../shared/apiClient";
import type { CandidateSentimentBatch } from "./types";


async function request(
  endpoint: string,
  candidateSnapshotId: string,
): Promise<CandidateSentimentBatch> {
  return apiClient.post<CandidateSentimentBatch>(
    endpoint,
    { candidate_snapshot_id: candidateSnapshotId },
    { context: "短线候选情绪" },
  );
}

export const loadCandidateSentiments = (candidateSnapshotId: string) =>
  request("/api/v1/a-shares/candidate-sentiment/batch", candidateSnapshotId);

export const refreshCandidateSentiments = (candidateSnapshotId: string) =>
  request(
    "/api/v1/a-shares/candidate-sentiment/batch/refresh",
    candidateSnapshotId,
  );
