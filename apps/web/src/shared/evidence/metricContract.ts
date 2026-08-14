export type MetricStatus = "ready" | "partial" | "stale" | "unavailable" | "error";
export type MetricDrilldownKind = "members" | "aggregate_only";

export type MetricMember = {
  symbol: string;
  name: string;
  reason: string;
  value?: string | number | null;
};

export type MetricContractInput = {
  metricId: string;
  label: string;
  value?: string | number | null;
  unit?: string | null;
  scope: string;
  status: MetricStatus;
  tradeDate?: string | null;
  observedAt?: string | null;
  source: string;
  formulaVersion?: string | null;
  sampleCount?: number | null;
  totalCount?: number | null;
  loadedMemberCount?: number;
  drilldownKind?: MetricDrilldownKind;
  members?: Array<Partial<MetricMember> & Pick<MetricMember, "symbol" | "reason">>;
  unavailableReason?: string | null;
};

export type MetricContract = Omit<MetricContractInput, "members" | "loadedMemberCount"> & {
  loadedMemberCount: number;
  members: MetricMember[];
};

export function createMetricContract(input: MetricContractInput): MetricContract {
  const members: MetricMember[] = (input.members ?? []).map((member) => ({
    symbol: member.symbol,
    name: member.name?.trim() || "名称待补齐",
    reason: member.reason,
    value: member.value ?? null,
  }));
  const loadedMemberCount = input.loadedMemberCount ?? members.length;
  if (loadedMemberCount !== members.length) throw new Error("loadedMemberCount must match members");
  if (input.totalCount != null && input.totalCount < loadedMemberCount) {
    throw new Error("totalCount cannot be smaller than loadedMemberCount");
  }
  const drilldownKind = input.drilldownKind ?? (members.length ? "members" : "aggregate_only");
  if (drilldownKind === "aggregate_only" && !input.unavailableReason) {
    throw new Error("aggregate_only requires unavailableReason");
  }
  if ((input.status === "unavailable" || input.status === "error") && !input.unavailableReason) {
    throw new Error("unavailable metric requires unavailableReason");
  }
  if (["ready", "partial", "stale"].includes(input.status) && !input.observedAt) {
    throw new Error("observed metric requires observedAt");
  }
  return { ...input, drilldownKind, members, loadedMemberCount };
}
