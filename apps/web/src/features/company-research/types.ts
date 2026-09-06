import type { FieldEvidence } from "../../shared/evidence/FieldEvidenceDetails";

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
  forward_eps_median?: string | null;
  forward_eps_sample_count?: number;
  forecast_latest_report_date?: string | null;
  forecast_age_days?: number | null;
  forecast_freshness?: "fresh" | "stale" | "unavailable";
  forward_pe?: string | null;
  forward_pe_status?: "available" | "low_confidence" | "unavailable";
  forward_pe_reason?: string;
  scenario_range?: {
    status: "available" | "unavailable";
    conservative: string | null;
    neutral: string | null;
    optimistic: string | null;
    eps_basis: string | null;
    peer_pe_basis: string | null;
    institution_sample_count: number;
    latest_report_date: string | null;
    reason: string;
  };
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

export type ResearchReportEvidence = {
  report_id: string; title: string; publish_date: string; organization: string;
  rating: string | null; industry: string | null; eps_this_year: string | null;
  eps_next_year: string | null; eps_next_two_year: string | null; pdf_url: string | null;
};

export type ResearchEnrichmentEvidence = {
  status: ResearchStatus;
  observed_at: string | null;
  stock_reports: ResearchReportEvidence[];
  industry_reports: ResearchReportEvidence[];
  industry_name?: string | null;
  industry_code?: string | null;
  industry_board_code?: string | null;
  shenwan_industry?: { code: string; name: string; level: "一级" | "二级" | "三级"; version: string } | null;
  shenwan_mapping_status?: "verified" | "unmapped";
  peer_candidates?: Array<{
    symbol: string; name: string; industry: string | null; price: string | null;
    change_percent: string | null; pe_ttm: string | null; pb: string | null;
    market_cap_yi: string | null;
  }>;
  unlocks: Array<{ free_date: string; stock_type: string | null; shares: string | null; ratio_percent: string | null }>;
  margin: Array<{ trade_date: string; financing_balance: string | null; financing_buy: string | null; securities_lending_balance: string | null; total_balance: string | null }>;
  holders: Array<{ period: string; holder_count: string | null; change_ratio_percent: string | null; average_free_shares: string | null }>;
  sources: string[];
  reasons: string[];
};

export type ResearchDecisionLedgerRow = {
  key: "peer_context" | "valuation" | "catalysts" | "contrary" | "invalidation";
  label: string;
  status: "ready" | "partial" | "unavailable" | "clear" | "triggered";
  summary: string;
  facts: string[];
  evidence_ids: string[];
  limitation: string | null;
};

export type CompanyResearchSection = {
  key: "business_model" | "industry_space" | "financial_trend" | "profit_quality" |
    "competitive_position" | "valuation_percentile" | "future_catalysts" |
    "contrary_risks" | "invalidation_conditions" | "verification_checklist";
  label: string;
  status: "ready" | "partial" | "unavailable" | "clear" | "triggered";
  summary: string;
  facts: string[];
  evidence_ids: string[];
  limitation: string | null;
};

export type ResearchConclusion = {
  key: CompanyResearchSection["key"];
  label: string;
  kind: "fact" | "inference" | "judgement" | "unavailable";
  claim: string;
  evidence_ids: string[];
  source_count: number;
  observed_at: string | null;
  limitations: string[];
};

export type EvidenceGraphNode = {
  node_id: string;
  kind: "evidence" | "fact" | "inference" | "judgement" | "unavailable";
  label: string;
  claim: string;
  evidence_ids: string[];
  observed_at: string | null;
  limitations: string[];
};

export type EvidenceGraphEdge = {
  source_node_id: string;
  target_node_id: string;
  relation: "supports" | "derives_from";
};

export type EvidenceGraph = {
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
};

export type CompanyResearchVersion = {
  snapshot_id: string;
  version_number: number;
  previous_snapshot_id: string | null;
  content_hash: string;
  generated_at: string;
  changes: Array<{
    category: "conclusion" | "data" | "source";
    label: string;
    before: string | null;
    after: string | null;
  }>;
};

export type CompanyResearchAIResult = {
  status: "ready" | "unconfigured" | "timeout" | "http_error" | "invalid";
  ai_state?: "unconfigured" | "configured_unverified" | "connected" | "connection_failed" | "output_invalid" | "timeout" | "rate_limited" | "model_not_found";
  ai_message?: string | null;
  snapshot_id: string;
  analysis: null | {
    executive_summary: string;
    contrary_risks: Array<{ title: string; detail: string; evidence_ids: string[] }>;
    verification_questions: string[];
  };
  provider: string;
  model: string;
  prompt_version: string;
  generated_at: string;
};

export type CompanyResearchAITaskSnapshot = {
  progress: CompanyResearchTaskProgress;
  result: CompanyResearchAIResult | null;
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
  enrichment?: ResearchEnrichmentEvidence;
  decision_ledger?: ResearchDecisionLedgerRow[];
  research_sections?: CompanyResearchSection[];
  conclusions?: ResearchConclusion[];
  evidence_graph?: EvidenceGraph;
  research_version?: CompanyResearchVersion | null;
  evidence_ledger?: EvidenceLedgerEntry[];
  field_evidence?: FieldEvidence[];
  sources: ResearchSource[];
  reasons: string[];
};

export type CompanyResearchTaskProgress = {
  task_id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  stage: string;
  processed: number | null;
  total: number | null;
  percent: number | null;
  detail: string | null;
  error: string | null;
};

export type CompanyResearchTaskSnapshot = {
  progress: CompanyResearchTaskProgress;
  result: CompanyResearchResponse | null;
};
import type { EvidenceLedgerEntry } from "../../shared/evidence/EvidenceLedger";
