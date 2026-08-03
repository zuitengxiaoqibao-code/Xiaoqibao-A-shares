export type BondDiagnosis = {
  is_cached?: boolean;
  cache_recorded_at?: string;
  status: "ready" | "stale_quote" | "source_conflict";
  bond: { code: string; name: string; price: string | null; suspended: boolean };
  linked_stock: { code: string; name: string; price: string; source: string; observed_at: string };
  quote: { source: string; observed_at: string; quality: string; turnover_amount: string | null };
  clause_snapshot: { source: string; fetched_at: string; conversion_price: string; maturity: string; remaining_size: string };
  metrics: { conversion_value: string | null; conversion_premium: string | null; pure_bond_premium: string | null; remaining_term: { days: number } };
  risk: { outcome: string; unknowns: string[]; explanations: string[] };
  strong_redemption: { state: string; clause_text: string | null; source: string; observed_at: string; evidence_fields?: Record<string, string> };
};

export type BondDashboard = {
  status: "ready" | "empty";
  bond_count: number;
  bond_codes: string[];
  discovered_count?: number;
  diagnosed_count?: number;
  unavailable_count?: number;
  undiagnosed_count?: number;
  undignosed_count?: number;
  data_unavailable_count?: number;
  risk_excluded_count?: number;
  observable_count?: number;
  diagnosed_outside_universe_count?: number;
  universe_observed_at?: string | null;
};
export type BondCandidates = {
  status: "ready" | "empty";
  items: Array<{ bond_code: string; conversion_premium: string | null; risk: { outcome: string } }>;
  coverage?: {
    discovered_count: number;
    diagnosed_count: number;
    candidate_count: number;
    unavailable_count: number;
    undiagnosed_count?: number;
    undignosed_count?: number;
    data_unavailable_count?: number;
    risk_excluded_count?: number;
    observable_count?: number;
    observed_at: string | null;
  };
  discovered?: Array<{
    bond_code: string;
    name: string;
    linked_stock_code: string | null;
    state: "discovered" | "diagnosed" | "unavailable" | "risk_excluded";
    reason: string | null;
  }>;
};

export type BondDiagnosisBatch = {
  status: "ready" | "empty";
  requested: number;
  processed: number;
  diagnosed_count: number;
  unavailable_count: number;
  observable_count?: number;
  risk_excluded_count?: number;
  data_unavailable_count?: number;
  items: Array<
    | { bond_code: string; state: "diagnosed"; status: string | null; risk_outcome: string | null }
    | { bond_code: string; state: "unavailable"; reason_code: string }
  >;
};
