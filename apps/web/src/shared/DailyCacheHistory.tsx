import { Clock3, History } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  DAILY_SNAPSHOT_UPDATED_EVENT,
  listDailySnapshots,
  type DailySnapshotListItem,
} from "./dailySnapshotCache";
import "./dailyCacheHistory.css";

type Props<T> = {
  scope: string;
  ariaLabel: string;
  activeSymbol?: string | null;
  getName: (value: T) => string | null | undefined;
  onSelect: (item: DailySnapshotListItem<T>) => void;
};

function cacheTime(value: string): string {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? "时间不可用"
    : parsed.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

export function DailyCacheHistory<T>({ scope, ariaLabel, activeSymbol, getName, onSelect }: Props<T>) {
  const read = useCallback(() => listDailySnapshots<T>(scope), [scope]);
  const [items, setItems] = useState(read);

  useEffect(() => {
    const refresh = (event?: Event) => {
      if (event instanceof CustomEvent && event.detail?.scope && event.detail.scope !== scope) return;
      setItems(read());
    };
    window.addEventListener(DAILY_SNAPSHOT_UPDATED_EVENT, refresh);
    window.addEventListener("focus", refresh);
    return () => {
      window.removeEventListener(DAILY_SNAPSHOT_UPDATED_EVENT, refresh);
      window.removeEventListener("focus", refresh);
    };
  }, [read, scope]);

  if (!items.length) return null;
  return <section className="daily-cache-history" role="region" aria-label={ariaLabel}>
    <header><span><History size={15} />今日已加载</span><small>{items.length} 只 · 点击再次进入</small></header>
    <div className="daily-cache-history-list">
      {items.map((item) => {
        const name = getName(item.value)?.trim() || "名称数据不可用";
        return <button
          className={activeSymbol === item.symbol ? "active" : undefined}
          type="button"
          key={item.symbol}
          aria-label={`${name} ${item.symbol} 缓存于 ${cacheTime(item.cachedAt)}`}
          onClick={() => onSelect(item)}
        >
          <span><b>{name}</b><code>{item.symbol}</code></span>
          <small><Clock3 size={12} />{cacheTime(item.cachedAt)}</small>
        </button>;
      })}
    </div>
  </section>;
}
