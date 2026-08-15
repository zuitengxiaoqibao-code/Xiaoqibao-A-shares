import { describe, expect, it } from "vitest";

import { recordPageMilestone, selectPrecomputeStatus } from "./precomputeStatus";
import { readPerfSummary, resetPerfLedgerForTests } from "./perfLedger";

describe("precompute status", () => {
  it("keeps a complete snapshot visible while the latest refresh has failed", () => {
    const status = selectPrecomputeStatus([{
      domain: "overview", latest_attempt_status: "failed",
      latest_attempt_data_version: "market-v2", served_data_version: "market-v1",
      served_trade_date: "2026-08-14", served_generated_at: "2026-08-15T08:00:00Z",
      served_content_hash: "a".repeat(64), attempt_count: 2,
      limitations: ["refresh_failed"],
    }], "overview");

    expect(status.state).toBe("stale");
    expect(status.message).toContain("仍展示上一份完整快照");
    expect(status.dataVersion).toBe("market-v1");
  });

  it("records first-screen and interactive milestones in the shared performance ledger", () => {
    resetPerfLedgerForTests();
    recordPageMilestone("market-overview", "first-screen", 100, 260, true);
    recordPageMilestone("market-overview", "interactive", 100, 540, true);

    const summary = readPerfSummary("market-overview")[0];
    expect(summary.count).toBe(2);
    expect(summary.p50Ms).toBe(160);
    expect(summary.p95Ms).toBe(440);
    expect(summary.cacheHitRate).toBe(100);
  });
});
