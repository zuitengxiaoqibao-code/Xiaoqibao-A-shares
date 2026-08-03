export type CandidateSentimentComponentName = "news" | "hotspot" | "fund_flow";
export type CandidateSentimentQuality = "ready" | "partial" | "unavailable";
export type CandidateSentimentBand =
  | "strongly_bearish"
  | "cautious"
  | "neutral"
  | "positive"
  | "overheated"
  | "unavailable";

export type CandidateSentimentComponent = {
  name: CandidateSentimentComponentName;
  status: "ready" | "unavailable";
  score: string | null;
  weight: string;
  summary: string;
  observed_at: string | null;
  evidence_ids: string[];
};

export type CandidateSentimentSnapshot = {
  snapshot_id: string | null;
  candidate_snapshot_id: string;
  candidate_input_hash: string;
  symbol: string;
  quality: CandidateSentimentQuality;
  freshness: "current" | "stale";
  score: string | null;
  band: CandidateSentimentBand;
  coverage_percent: string;
  components: CandidateSentimentComponent[];
  primary_reason: string;
  primary_risk: string;
  beginner_guidance: string;
  observed_at: string;
  generated_at: string;
  source_snapshot_ids: string[];
  formula_version: "candidate-sentiment-v1";
};

export type CandidateSentimentBatch = {
  snapshot_id: string | null;
  candidate_snapshot_id: string;
  candidate_input_hash: string;
  as_of: string;
  cutoff: string;
  quality: CandidateSentimentQuality;
  items: CandidateSentimentSnapshot[];
  generated_at: string;
};

export type CandidateSentimentLoader = (
  candidateSnapshotId: string,
) => Promise<CandidateSentimentBatch>;
