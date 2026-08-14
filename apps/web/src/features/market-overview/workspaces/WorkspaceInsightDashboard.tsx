import {
  Activity, AlertTriangle, BarChart3, BookOpenCheck, Database, Gauge,
  Landmark, Newspaper, Radar, ShieldAlert, Tags, TrendingUp,
} from "lucide-react";
import { useState } from "react";

import { DrilldownMetric, MetricDrilldownPanel, type MetricDrilldownSelection, type StockResearchActions } from "./MetricDrilldown";
import type { WorkspaceInsight } from "./workspaceInsights";

const icons = {
  pulse: Gauge,
  news: Newspaper,
  theme: Tags,
  auction: Radar,
  limit: TrendingUp,
  sector: BarChart3,
  history: BookOpenCheck,
  seat: Landmark,
  risk: ShieldAlert,
  data: Database,
  stock: Activity,
};

export function WorkspaceInsightDashboard({ feature, insights, actions }: { feature: string; insights: WorkspaceInsight[]; actions: StockResearchActions }) {
  const [selection, setSelection] = useState<MetricDrilldownSelection | null>(null);
  return <><section className="workspace-insight-dashboard" aria-label={`${feature}关键仪表`}>
    {insights.map((insight) => {
      const Icon = icons[insight.icon];
      const content = <article className={`tone-${insight.tone} quality-${insight.quality}`}>
        <header><Icon size={18} /><span>{insight.label}</span>{insight.quality === "unavailable" ? <AlertTriangle size={15} /> : <i />}</header>
        <b>{insight.value}</b>
        <p>{insight.detail}</p>
        <footer><span>{insight.quality === "ready" ? insight.basis === "raw" ? "原始字段" : insight.basis === "derived" ? "确定性派生" : "观察性合成" : insight.quality === "partial" ? "部分证据" : "禁止代理"}</span><i /></footer>
        {insight.method && <small className="workspace-insight-method" title={insight.method}>口径：{insight.method}</small>}
      </article>;
      return insight.drilldown
        ? <DrilldownMetric key={insight.key} item={insight.drilldown} selected={selection?.label === insight.label} onSelect={setSelection} ariaLabelPrefix="关键仪表">{content}</DrilldownMetric>
        : <div key={insight.key}>{content}</div>;
    })}
  </section>{selection && <MetricDrilldownPanel selection={selection} onClose={() => setSelection(null)} actions={actions} />}</>;
}
