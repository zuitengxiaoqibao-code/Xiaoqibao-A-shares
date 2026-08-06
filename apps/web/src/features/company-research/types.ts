export type ResearchStatus = "ready" | "partial" | "unavailable";
export type CounterStatus = "clear" | "triggered" | "unavailable";

export type FinancialPeriod = {
  period: string;
  revenue: string | null;
  revenue_yoy: string | null;
  operating_cost: string | null;
  net_profit: string | null;
  net_profit_yoy: string | null;
  operating_cash_flow: string | null;
  total_assets: string | null;
  total_liabilities: string | null;
  total_equity: string | null;
  gross_margin: string | null;
  cash_to_profit: string | null;
  debt_ratio: string | null;
};

export type FinancialHistory = {
  status: ResearchStatus;
  periods: FinancialPeriod[];
  annual_periods: FinancialPeriod[];
  latest_period: FinancialPeriod | null;
  revenue_cagr_3y: string | null;
  net_profit_cagr_3y: string | null;
  source: string;
  observed_at: string | null;
  reasons: string[];
};

export type ResearchDimension = {
  key: string;
  label: string;
  weight: number;
  status: "ready" | "unavailable";
  score: string | null;
  summary: string;
  metrics: Record<string, string | null>;
  evidence_ids: string[];
  reason: string | null;
};

export type CounterCaseItem = {
  key: string;
  title: string;
  status: CounterStatus;
  detail: string;
  threshold: string | null;
  penalty: string;
  evidence_ids: string[];
};

export type ValuationObservation = {
  status: ResearchStatus;
  pe_ttm: string | null;
  pb: string | null;
  market_cap_yi: string | null;
  peer_pe_median: string | null;
  peer_pb_median: string | null;
  observation_range_status: "available" | "unavailable";
  observation_range_reason: string;
  source: string;
  observed_at: string | null;
};

export type LatestTipCategory = "公告与合同" | "业绩预告" | "资金与融资" | "交易异动" | "风险提醒" | "其他";
export type LatestTipTone = "positive" | "neutral" | "risk" | "unknown";

export type LatestTipItem = {
  id: string;
  category: LatestTipCategory;
  title: string;
  date: string | null;
  tone: LatestTipTone;
  summary: string;
  source: string;
  observed_at: string | null;
  raw_text: string;
};

export type CompanyProfileEvidence = {
  status: ResearchStatus;
  company_overview: string | null;
  industry_analysis: string | null;
  latest_tips: string | null;
  latest_tip_items?: LatestTipItem[];
  source: string;
  observed_at: string | null;
  reasons: string[];
};

export type ResearchSource = {
  source: string;
  label: string;
  status: ResearchStatus;
  observed_at: string | null;
  detail: string;
};

export type CompanyResearchResponse = {
  status: ResearchStatus;
  symbol: string;
  name: string;
  as_of: string;
  generated_at: string;
  dimensions: ResearchDimension[];
  evidence_coverage: string;
  base_score: string | null;
  risk_penalty: string;
  final_score: string | null;
  financial_history: FinancialHistory;
  valuation: ValuationObservation;
  counter_case: CounterCaseItem[];
  profile: CompanyProfileEvidence;
  sources: ResearchSource[];
  reasons: string[];
};
