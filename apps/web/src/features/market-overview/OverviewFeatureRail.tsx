import { featureRows } from "./featureCatalog";

export function OverviewFeatureRail({ active, onSelect }: {
  active: string;
  onSelect: (feature: string) => void;
}) {
  return <nav className="overview-feature-rail" aria-label="市场功能筛选">
    {featureRows.flat().map((label) => <button
      type="button"
      key={label}
      title={label}
      className={active === label ? "active" : ""}
      aria-pressed={active === label}
      onClick={() => onSelect(label)}
    >{label}</button>)}
  </nav>;
}
