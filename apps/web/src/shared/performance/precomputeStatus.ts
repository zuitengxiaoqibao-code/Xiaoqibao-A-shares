import { recordPerfEvent } from "./perfLedger";

export type PrecomputeInventoryItem = {
  domain: "overview" | "quant" | "research";
  latest_attempt_status: "complete" | "partial" | "failed" | "unavailable";
  latest_attempt_data_version: string | null;
  served_data_version: string | null;
  served_trade_date: string | null;
  served_generated_at: string | null;
  served_content_hash: string | null;
  attempt_count: number;
  limitations: string[];
};

export type PrecomputeStatus = {
  state: "ready" | "stale" | "refreshing" | "unavailable" | "error";
  message: string;
  dataVersion: string | null;
  tradeDate: string | null;
};

export function selectPrecomputeStatus(
  inventory: PrecomputeInventoryItem[],
  domain: PrecomputeInventoryItem["domain"],
): PrecomputeStatus {
  const item = inventory.find((candidate) => candidate.domain === domain);
  if (!item) return { state: "unavailable", message: "尚无预计算记录", dataVersion: null, tradeDate: null };
  if (!item.served_data_version) {
    return {
      state: item.latest_attempt_status === "failed" ? "error" : "unavailable",
      message: item.latest_attempt_status === "failed" ? "最新计算失败，暂无完整快照" : "完整快照尚未生成",
      dataVersion: null,
      tradeDate: null,
    };
  }
  if (item.latest_attempt_status === "failed" || item.latest_attempt_status === "partial") {
    return {
      state: "stale",
      message: "最新刷新未通过完整性校验，仍展示上一份完整快照",
      dataVersion: item.served_data_version,
      tradeDate: item.served_trade_date,
    };
  }
  const exact = item.latest_attempt_data_version === item.served_data_version;
  return {
    state: exact ? "ready" : "refreshing",
    message: exact ? "完整预计算快照已就绪" : "正在后台生成最新完整快照",
    dataVersion: item.served_data_version,
    tradeDate: item.served_trade_date,
  };
}

export function recordPageMilestone(
  domain: string,
  phase: "first-screen" | "interactive",
  navigationStartedMs: number,
  milestoneAtMs: number,
  cacheHit: boolean,
): void {
  recordPerfEvent({
    domain,
    phase,
    durationMs: Math.max(0, milestoneAtMs - navigationStartedMs),
    cacheHit,
    status: "ready",
    observedAt: new Date().toISOString(),
  });
}
