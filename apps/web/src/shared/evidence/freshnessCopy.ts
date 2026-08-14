import type { EvidenceStatus } from "../visualization/types";

const LABELS: Record<EvidenceStatus, string> = {
  ready: "数据已就绪",
  partial: "数据部分可用",
  stale: "使用历史数据",
  unavailable: "数据不可用",
  error: "数据加载失败",
};

const COMPACT_LABELS: Record<EvidenceStatus, string> = {
  ready: "数据就绪",
  partial: "部分可用",
  stale: "历史快照",
  unavailable: "数据不可用",
  error: "读取失败",
};

const DETAILS: Record<EvidenceStatus, string> = {
  ready: "关键字段已取得当前可用证据",
  partial: "部分字段或股票仍待补齐",
  stale: "当前内容来自历史快照，不代表实时",
  unavailable: "暂无足够真实证据生成该指标",
  error: "数据源读取失败，保留已有完整内容",
};

const BLOCKERS: Record<string, string> = {
  history_dates_fragmented: "历史日期存在零散分片",
  history_latest_outlier: "最新日期仅覆盖少量股票",
  history_unavailable: "本地日线历史不可用",
  tdx_daily_history_unavailable: "通达信本地日线历史不可用",
  history_coverage_low: "历史覆盖率低于完整分析门槛",
  dominant_date_coverage_below_98_percent: "主导交易日覆盖率低于 98%",
  history_not_ready_for_all_symbols: "仍有股票未达到完整历史要求",
  history_coverage_below_98_percent: "历史覆盖率低于 98% 就绪门槛",
  no_dominant_trade_date: "无法确认主导交易日",
  incomplete_daily_history: "历史覆盖不完整",
  stale_daily_history: "日线历史落后请求日",
  no_factor_ready_history: "没有可计算因子的完整历史",
  candidate_scan_pending: "候选扫描仍在后台进行",
  trigger_evidence_pending: "盘中触发证据仍在更新",
};

export function freshnessLabel(status: EvidenceStatus): string {
  return LABELS[status];
}

export function compactFreshnessLabel(status: EvidenceStatus): string {
  return COMPACT_LABELS[status];
}

export function freshnessDetail(status: EvidenceStatus): string {
  return DETAILS[status];
}

export function blockerLabel(code: string): string {
  return BLOCKERS[code] ?? "数据完整性待检查";
}
