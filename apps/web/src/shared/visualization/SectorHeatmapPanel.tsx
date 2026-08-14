import type { OverviewSector } from "../../features/market-overview/types";

function numeric(value: string | null): number | null {
  if (value === null || value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function signed(value: number | null): string {
  return value === null ? "--" : `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function direction(value: number | null): "up" | "down" | "flat" | "unavailable" {
  if (value === null) return "unavailable";
  if (value > 0) return "up";
  if (value < 0) return "down";
  return "flat";
}

function intensity(value: number | null): number {
  if (value === null) return 0;
  return Math.min(1, Math.max(0.12, Math.abs(value) / 10));
}

export function SectorHeatmapPanel({ sectors, selectedSectorId, onSelectSector }: {
  sectors: OverviewSector[];
  selectedSectorId: string | null;
  onSelectSector: (sectorId: string) => void;
}) {
  return <section className="sector-heatmap-panel" aria-label="板块涨跌热力矩阵">
    <header><div><span>SECTOR / HEATMAP</span><h3>板块涨跌热力</h3></div><small>红涨 · 绿跌 · 灰色表示缺失</small></header>
    {sectors.length === 0
      ? <div className="sector-heatmap-empty">没有已验证板块行情，暂不生成热力矩阵。</div>
      : <div className="sector-heatmap-grid">{sectors.slice(0, 24).map((sector) => {
        const change = numeric(sector.change_percent);
        const tone = direction(change);
        const alpha = intensity(change);
        const style = tone === "up"
          ? { background: `linear-gradient(135deg, rgba(240,79,95,${0.11 + alpha * 0.34}), rgba(240,79,95,${0.03 + alpha * 0.12}))` }
          : tone === "down"
            ? { background: `linear-gradient(135deg, rgba(47,207,145,${0.11 + alpha * 0.34}), rgba(47,207,145,${0.03 + alpha * 0.12}))` }
            : undefined;
        return <button type="button" key={sector.sector_id} className="sector-heatmap-tile" data-direction={tone} data-selected={selectedSectorId === sector.sector_id ? "true" : "false"} style={style} aria-label={`板块热力 ${sector.name}`} onClick={() => onSelectSector(sector.sector_id)}>
          <strong>{sector.name}</strong><b>{signed(change)}</b><small>涨停 {sector.limit_up_count} · {sector.stock_count} 只</small>
        </button>;
      })}</div>}
  </section>;
}
