import { QuantChart } from "../quant-analysis/QuantChart";
import { buildDualAxisOption } from "../../shared/visualization/chartOptions";
import { ChartPanel } from "../../shared/visualization/VisualPrimitives";
import type { EvidenceState } from "../../shared/visualization/types";

export function ValuationComparisonChart({ pe, pb, peerPe, peerPb, source, observedAt }: {
  pe: number | null;
  pb: number | null;
  peerPe: number | null;
  peerPb: number | null;
  source: string;
  observedAt: string | null;
}) {
  const hasCurrent = pe !== null || pb !== null;
  const hasPeer = peerPe !== null || peerPb !== null;
  const state: EvidenceState = {
    status: hasCurrent && hasPeer ? "ready" : hasCurrent ? "partial" : "unavailable",
    source,
    observedAt,
    coverage: hasCurrent && hasPeer ? 100 : hasCurrent ? 50 : null,
    warnings: hasPeer ? [] : ["同行中位数或历史估值序列未接入，不能推导相对估值结论。"],
  };
  const option = buildDualAxisOption({
    categories: ["当前快照", "同行中位"],
    primary: { name: "PE(TTM)", values: [pe, peerPe] },
    secondary: { name: "PB", values: [pb, peerPb] },
    primaryTone: "warning",
    secondaryTone: "live",
  });
  return <ChartPanel title="估值双轴对照" subtitle="PE(TTM) 折线 · PB 柱线 · 仅展示真实快照" state={state} ariaLabel="当前估值与同行中位双轴图">
    <div className="research-valuation-chart"><QuantChart option={option} ariaLabel="当前估值与同行中位双轴图" /></div>
    <p className="research-valuation-disclaimer">历史估值序列尚未接入；当前图只对照已取得的当前值与同行中位数，不代表历史高低位。</p>
  </ChartPanel>;
}
