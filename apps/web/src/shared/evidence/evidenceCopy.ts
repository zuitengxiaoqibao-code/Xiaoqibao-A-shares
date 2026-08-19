import { blockerLabel, isKnownBlocker } from "./freshnessCopy";

const FIELD_LABELS: Record<string, string> = {
  "sentiment.score": "市场情绪评分",
  "breadth.rising_count": "上涨家数",
  "liquidity.relative_amount": "成交热度",
  "valuation.pe_ttm": "市盈率（TTM）",
  "market.latest_price": "最新价",
  "assessment.confidence": "研判置信度",
  final_score: "综合评分",
};

const SOURCE_LABELS: Record<string, string> = {
  "market-sentiment-cache": "本地市场情绪快照",
  "tdx-local-daily": "本地通达信日线",
  "tdx-local-day": "本地通达信日线",
  "tdx-local-rpc": "本地通达信全市场行情",
  "tdx-local-rpc-detail": "本地通达信行情明细",
  "tdx-local-realtime": "本地通达信实时行情",
  "tdx-local-professional": "本地通达信专业数据",
  "sina-finance": "新浪财经",
  tencent: "腾讯行情",
  unavailable: "暂无有效数据来源",
  "stock-assessor": "个股研判引擎",
};

const SOURCE_FIELD_LABELS: Record<string, string> = {
  score: "情绪评分",
  rising_count: "上涨家数",
  relative_amount: "相对成交额",
  pe_ttm: "市盈率（TTM）",
  price: "最新价",
};

const FORMULA_LABELS: Record<string, string> = {
  "a-share-sentiment-v1": "A股市场情绪模型 v1",
  "a-share-sentiment-v2": "A股市场情绪模型 v2",
  "a-share-market-review-v1": "A股市场复盘模型 v1",
  "a-share-market-review-v2": "A股市场复盘模型 v2",
  "market-review-v1": "市场复盘模型 v1",
  "a-share-short-strategy-v2.0": "A股短线策略模型 v2.0",
  "a-share-short-regime-v2.0": "A股短线风格模型 v2.0",
  "candidate-sentiment-v1": "候选股情绪模型 v1",
  "workspace-insight-v1": "工作台洞察模型 v1",
  "regime-v2": "市场风格模型 v2",
};

const OPERATION_LABELS: Record<string, string> = {
  market_review: "市场复盘",
  professional_probe: "通达信专业数据探测",
  market_sentiment: "市场情绪计算",
  company_research: "公司研究",
  quant_strategy: "量化策略分析",
  realtime_quote: "实时行情读取",
  daily_history: "日线历史读取",
};

function containsChinese(value: string): boolean {
  return /[\u3400-\u9fff]/u.test(value);
}

function translatedSourcePart(value: string): string {
  const normalized = value.trim();
  if (!normalized) return "未识别数据来源";
  if (containsChinese(normalized)) return normalized;
  return SOURCE_LABELS[normalized] ?? "未识别数据来源";
}

export function evidenceFieldLabel(value: string): string {
  if (containsChinese(value)) return value;
  return FIELD_LABELS[value] ?? "未识别指标";
}

export function evidenceSourceLabel(value: string): string {
  if (containsChinese(value)) return value;
  const parts = value.split(/\s*\/\s*/u);
  if (parts.length > 1) return parts.map(translatedSourcePart).join(" / ");
  return translatedSourcePart(value);
}

export function evidenceSourceFieldLabel(value: string): string {
  if (containsChinese(value)) return value;
  return SOURCE_FIELD_LABELS[value] ?? "未识别原始字段";
}

export function evidenceFormulaLabel(value: string): string {
  if (containsChinese(value)) return value;
  return FORMULA_LABELS[value] ?? "未登记公式版本";
}

export function evidenceOperationLabel(value: string): string {
  if (containsChinese(value)) return value;
  return OPERATION_LABELS[value] ?? "未识别处理流程";
}

export function evidenceLimitationLabel(value: string): string {
  if (containsChinese(value)) return value;
  return isKnownBlocker(value) ? blockerLabel(value) : "数据完整性限制";
}
