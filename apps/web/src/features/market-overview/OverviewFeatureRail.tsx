import { featureCatalog } from "./featureCatalog";
import { isCoreOverviewWorkspace } from "./workspaces/workspaceRegistry";

export function OverviewFeatureRail({ active, onSelect }: {
  active: string;
  onSelect: (feature: string) => void;
}) {
  return <nav className="overview-feature-rail" aria-label="市场功能筛选">
    {featureCatalog.map((feature) => <button
      type="button"
      key={feature.key}
      title={feature.note ? `${feature.label}：${feature.note}` : feature.label}
      data-feature-key={feature.key}
      data-family={feature.family}
      className={active === feature.key ? "active" : ""}
      aria-pressed={active === feature.key}
      data-core-overview={isCoreOverviewWorkspace(feature.key) ? "true" : undefined}
      onClick={() => onSelect(feature.key)}
    >{feature.label}</button>)}
  </nav>;
}
