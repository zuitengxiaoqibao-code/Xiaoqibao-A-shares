import { bondTaskPreview, type BondTaskCard } from "./taskCards";

export function BondTaskFlow({ cards, selectedCode, onSelect }: {
  cards: BondTaskCard[];
  selectedCode: string | null;
  onSelect: (code: string) => void;
}) {
  const preview = bondTaskPreview(cards);
  return <section className="bond-task-flow" aria-label="转债任务流">
    <header><div><span>VERIFICATION FLOW</span><h2>转债核验任务</h2></div><small>展示 {preview.visible.length} / 共 {cards.length} 项真实记录</small></header>
    {preview.visible.length ? <>
      <div className="bond-task-stack">
      {preview.visible.map((card, index) => <button
        type="button"
        className={`bond-task-card ${card.tone} ${selectedCode === card.code ? "selected" : ""}`}
        style={{ "--task-index": index, "--task-offset": index - (preview.visible.length - 1) / 2 } as React.CSSProperties}
        aria-label={`${card.code} ${card.name} ${card.stateLabel}`}
        aria-pressed={selectedCode === card.code}
        onClick={() => onSelect(card.code)}
        key={card.code}
      >
        <span><small>{card.code}</small><b>{card.name}</b></span>
        <strong>{card.stateLabel}</strong>
        <span>{card.linkedStockCode ? `关联正股 ${card.linkedStockCode}` : "关联正股待核验"}</span>
        {card.reason && <p>{card.reason}</p>}
      </button>)}
      </div>
      {preview.hiddenCount > 0 && <p className="bond-task-overflow">其余 {preview.hiddenCount} 项保留在发现池</p>}
    </> : <div className="bond-task-empty"><b>等待真实发现池</b><p>同步转债列表后，这里会按未诊断、可观察和风险状态建立任务流。</p></div>}
  </section>;
}
