import { AlertTriangle, Database, Layers3 } from "lucide-react";

import type { MarketDataWatermark } from "./types";
import { blockerLabel } from "../../shared/evidence/freshnessCopy";

function percent(value: string | null): string {
  const parsed = value === null ? Number.NaN : Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(1)}%` : "--";
}

export function MarketDataWatermarkCenter({ watermark }: { watermark: MarketDataWatermark }) {
  const qualityLabel = watermark.quality === "ready"
    ? "水位完整"
    : watermark.quality === "partial"
      ? "部分覆盖"
      : watermark.quality === "stale" ? "历史待更新" : "水位不可用";
  return <section className="market-watermark-center" role="region" aria-label="全市场数据水位中心" data-quality={watermark.quality}>
    <header>
      <div><Database size={16} /><span><b>全市场数据水位中心</b><small>所有筛选、复盘和量化结论共用同一主导交易日口径</small></span></div>
      <em>{qualityLabel}</em>
    </header>
    <div className="market-watermark-metrics">
      <article><span>主导交易日</span><strong>{watermark.dominant_trade_date ?? "--"}</strong><small>全市场覆盖最多的历史交易日</small></article>
      <article><span>最新可用记录</span><strong>{watermark.latest_available_trade_date ?? "--"}</strong><small>{watermark.fragmented_latest_count > 0 ? `${watermark.fragmented_latest_count} 只零散记录` : "与主导日期一致"}</small></article>
      <article><span>历史覆盖率</span><strong>{percent(watermark.coverage_percent)}</strong><small>{watermark.history_ready_count.toLocaleString("zh-CN")} / {watermark.universe_count.toLocaleString("zh-CN")} 只</small></article>
      <article><span>零散最新记录</span><strong>{watermark.fragmented_latest_count.toLocaleString("zh-CN")} 只</strong><small>不会替代全市场主导日期</small></article>
      <article><span>缺失完整历史</span><strong>{watermark.missing_history_count.toLocaleString("zh-CN")} 只</strong><small>不进入依赖完整日线的计算</small></article>
    </div>
    {watermark.blockers.length > 0 && <footer><Layers3 size={14} />{watermark.blockers.map((item) => <span key={item}><AlertTriangle size={12} />{blockerLabel(item)}</span>)}</footer>}
  </section>;
}
