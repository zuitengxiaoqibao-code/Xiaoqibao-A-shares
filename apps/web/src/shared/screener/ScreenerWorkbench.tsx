import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { filterMembers } from "./filterEngine";
import type { ScreenerMember, ScreenerSort } from "./types";
import { loadWorkspaceState, updateWorkspaceFilter } from "../workspace/workspaceState";

export function ScreenerWorkbench({ rows, children, storageScope }: { rows: ScreenerMember[]; children: (rows: ScreenerMember[]) => React.ReactNode; storageScope?: string }) {
  const [saved] = useState(() => storageScope ? loadWorkspaceState()?.filters[storageScope] : undefined);
  const [query, setQuery] = useState(typeof saved?.query === "string" ? saved.query : "");
  const [excludeST, setExcludeST] = useState(saved?.excludeST === true);
  const [excludeSuspended, setExcludeSuspended] = useState(saved?.excludeSuspended === true);
  const [sort, setSort] = useState<ScreenerSort>(saved?.sort === "name" || saved?.sort === "value_desc" ? saved.sort : "symbol");
  useEffect(() => {
    if (storageScope) updateWorkspaceFilter(storageScope, { query, excludeST, excludeSuspended, sort });
  }, [excludeST, excludeSuspended, query, sort, storageScope]);
  const filtered = useMemo(() => filterMembers(rows, { query, excludeST, excludeSuspended, sort }), [excludeST, excludeSuspended, query, rows, sort]);
  return <>
    <div className="metric-screener-toolbar" aria-label="明细筛选工具">
      <label><Search size={14} /><input aria-label="搜索明细" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="代码 / 名称 / 原因" /></label>
      <label><input type="checkbox" checked={excludeST} onChange={(event) => setExcludeST(event.target.checked)} />排除 ST</label>
      <label><input type="checkbox" checked={excludeSuspended} onChange={(event) => setExcludeSuspended(event.target.checked)} />排除停牌</label>
      <select aria-label="明细排序" value={sort} onChange={(event) => setSort(event.target.value as ScreenerSort)}><option value="symbol">代码排序</option><option value="name">名称排序</option><option value="value_desc">数值降序</option></select>
      <span>筛选结果 <b>{filtered.length}</b> / {rows.length}</span>
    </div>
    {children(filtered)}
  </>;
}
