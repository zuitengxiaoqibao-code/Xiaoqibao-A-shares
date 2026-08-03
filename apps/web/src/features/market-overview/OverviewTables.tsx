import type { OverviewSector, OverviewSectorStock } from "./types";
import { interactiveTargetProps } from "./interactiveTarget";

function signed(value: string | null, suffix = "%"): string {
  if (value === null) return "--";
  const number = Number(value);
  if (!Number.isFinite(number)) return "--";
  return `${number > 0 ? "+" : ""}${number.toFixed(2)}${suffix}`;
}

function direction(value: string | null): string {
  const number = Number(value);
  if (!Number.isFinite(number) || number === 0) return "flat";
  return number > 0 ? "up" : "down";
}

export function OverviewTables({ sectors, sectorStocks, selectedSectorId, onSelectSector, onOpenAShare }: {
  sectors: OverviewSector[];
  sectorStocks: Record<string, OverviewSectorStock[]>;
  selectedSectorId: string | null;
  onSelectSector: (sectorId: string) => void;
  onOpenAShare?: (symbol: string) => void;
}) {
  const selected = sectors.find((sector) => sector.sector_id === selectedSectorId) ?? sectors[0] ?? null;
  const stocks = selected ? sectorStocks[selected.sector_id] ?? [] : [];
  return <section className="overview-table-deck" aria-label="热门板块与成分股">
    <div className="overview-table-card">
      <header><b>热门板块</b><span>按公开异动与题材覆盖排序</span></header>
      <div className="overview-table-scroll">
        <table aria-label="热门板块">
          <thead><tr><th>排名</th><th>板块名称</th><th>涨幅</th><th>成交额</th><th>涨停</th><th>上涨</th><th>下跌</th></tr></thead>
          <tbody>{sectors.length === 0 ? <tr><td colSpan={7}>板块数据暂不可用</td></tr> : sectors.map((sector, index) => <tr key={sector.sector_id} className={selected?.sector_id === sector.sector_id ? "selected" : ""} {...interactiveTargetProps(() => onSelectSector(sector.sector_id), `查看${sector.name}板块`)}>
            <td>{index + 1}</td>
            <td><button type="button" aria-label={`${sector.name} ${signed(sector.change_percent)}`} onClick={(event) => { event.stopPropagation(); onSelectSector(sector.sector_id); }}>{sector.name}</button></td>
            <td className={direction(sector.change_percent)}>{signed(sector.change_percent)}</td>
            <td>{sector.amount_yi === null ? "--" : `${sector.amount_yi}亿`}</td>
            <td className="up">{sector.limit_up_count}</td><td>{sector.rising_count}</td><td className="down">{sector.falling_count}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </div>
    <div className="overview-table-card">
      <header><b>{selected?.name ?? "板块成分股"}</b><span>{selected ? `${selected.stock_count} 只 / 当前联动` : "等待板块数据"}</span></header>
      <div className="overview-table-scroll">
        <table aria-label={`${selected?.name ?? "板块"}成分股`}>
          <thead><tr><th>序号</th><th>股票代码</th><th>股票名称</th><th>涨幅</th><th>成交额</th><th>市值</th><th>首次涨停</th><th>地位</th></tr></thead>
          <tbody>{stocks.length === 0 ? <tr><td colSpan={8}>该板块暂无已验证成分股</td></tr> : stocks.map((stock, index) => <tr key={stock.symbol} {...interactiveTargetProps(onOpenAShare ? () => onOpenAShare(stock.symbol) : undefined, `查看 ${stock.symbol} ${stock.name}`)}>
            <td>{index + 1}</td><td>{stock.symbol}</td>
            <td><button type="button" aria-label={`查看 ${stock.symbol} ${stock.name}`} onClick={(event) => { event.stopPropagation(); onOpenAShare?.(stock.symbol); }}>{stock.name}</button></td>
            <td className={direction(stock.change_percent)}>{signed(stock.change_percent)}</td>
            <td>{stock.amount_yi === null ? "--" : `${stock.amount_yi}亿`}</td><td>{stock.market_cap_yi === null ? "--" : `${stock.market_cap_yi}亿`}</td>
            <td>{stock.first_limit_time ?? "--"}</td><td className="position">{stock.position}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </div>
  </section>;
}
