import type { MarketReviewSnapshot } from "../types";

export function hasDragonTigerEvidence(review: MarketReviewSnapshot | null | undefined): boolean {
  return Boolean(review && !review.warnings?.includes("dragon_tiger_unavailable"));
}
