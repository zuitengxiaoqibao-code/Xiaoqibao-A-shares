import {
  BarChart3, BellRing, BookOpenText, CandlestickChart, CircleDot, History, LayoutDashboard, LibraryBig, Newspaper, Settings2,
  ShieldAlert, Sparkles,
} from "lucide-react";
import { useState } from "react";

import { safeStorageGet, safeStorageSet } from "../../shared/safeLocalStorage";

export type BeginnerView = "market_overview" | "dashboard" | "a_shares" | "company_research" | "first_limit_up" | "quant_analysis" | "news" | "risk" | "history" | "settings" | "bonds";

const entries = [
  ["market_overview", "信息总览", LayoutDashboard],
  ["dashboard", "今日研判", Sparkles],
  ["a_shares", "个股观察", CandlestickChart],
  ["company_research", "公司研究", LibraryBig],
  ["first_limit_up", "首次涨停", CircleDot],
  ["quant_analysis", "量化分析", BarChart3],
  ["news", "新闻热点", Newspaper],
  ["risk", "风险提醒", ShieldAlert],
  ["history", "历史复盘", History],
  ["settings", "数据设置", Settings2],
] as const;

type NavigationMode = "beginner" | "expert";
const navigationModeKey = "qibao-navigation-mode";
const beginnerEntries = new Set<BeginnerView>([
  "market_overview", "dashboard", "a_shares", "company_research", "first_limit_up",
  "news", "risk", "history",
]);

export function BeginnerNavigation({ active, onNavigate }: {
  active: BeginnerView;
  onNavigate: (view: BeginnerView) => void;
}) {
  const [mode, setMode] = useState<NavigationMode>(() => (
    safeStorageGet(navigationModeKey, "beginner") === "expert" ? "expert" : "beginner"
  ));
  const visibleEntries = mode === "expert"
    ? entries
    : entries.filter(([view]) => beginnerEntries.has(view));

  function selectMode(next: NavigationMode) {
    setMode(next);
    safeStorageSet(navigationModeKey, next);
  }

  return <aside className="terminal-navigation beginner-sidebar">
    <div className="beginner-brand"><span><BookOpenText size={20} /></span><div><strong>小七宝</strong><small>个股观察台</small></div></div>
    <div className="navigation-mode-switch" role="group" aria-label="导航模式">
      <button className="navigation-mode-beginner" type="button" aria-pressed={mode === "beginner"} onClick={() => selectMode("beginner")}>新手模式</button>
      <button className="navigation-mode-expert" type="button" aria-pressed={mode === "expert"} onClick={() => selectMode("expert")}>专家模式</button>
    </div>
    <nav aria-label="主要功能">
      {visibleEntries.map(([view, label, Icon]) => <button className={active === view ? "active" : ""} type="button" key={view} aria-current={active === view ? "page" : undefined} onClick={() => onNavigate(view)}><Icon size={18} /><span>{label}</span></button>)}
    </nav>
    <div className="asset-separator"><span>独立资产</span></div>
    <button className={`bond-navigation ${active === "bonds" ? "active" : ""}`} type="button" aria-label="可转债" onClick={() => onNavigate("bonds")}><BellRing size={18} /><span><b>可转债</b><small>独立观察空间</small></span></button>
    <p className="beginner-disclaimer">只做观察与风险提示<br />不连接券商，不构成投资建议</p>
  </aside>;
}
