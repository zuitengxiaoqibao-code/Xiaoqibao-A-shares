import {
  Activity, BarChart3, BellRing, BookOpenText, CandlestickChart, CircleDot, Gauge, History, LayoutDashboard, LibraryBig, Newspaper, ServerCog, Settings2,
  ShieldAlert, Sparkles,
} from "lucide-react";
import { TaskActivityStatus } from "../../shared/TaskActivityStatus";
import type { AISettingsView } from "../data-settings/types";

export type BeginnerView = "market_overview" | "dashboard" | "a_shares" | "company_research" | "first_limit_up" | "late_session_selection" | "quant_analysis" | "data_screen" | "monitor_center" | "news" | "risk" | "history" | "settings" | "operations" | "bonds";

const entries = [
  ["market_overview", "信息总览", LayoutDashboard],
  ["dashboard", "今日研判", Sparkles],
  ["a_shares", "个股观察", CandlestickChart],
  ["company_research", "公司研究", LibraryBig],
  ["first_limit_up", "首次涨停", CircleDot],
  ["late_session_selection", "尾盘选股", Activity],
  ["quant_analysis", "量化分析", BarChart3],
  ["data_screen", "数据大屏", Gauge],
  ["news", "新闻热点", Newspaper],
  ["risk", "风险提醒", ShieldAlert],
  ["history", "历史复盘", History],
  ["monitor_center", "监控中心", BellRing],
  ["settings", "数据设置", Settings2],
  ["operations", "本地运维", ServerCog],
] as const;

export function BeginnerNavigation({ active, onNavigate, ai }: {
  active: BeginnerView;
  onNavigate: (view: BeginnerView) => void;
  ai?: AISettingsView | null;
}) {
  return <aside className="terminal-navigation beginner-sidebar">
    <div className="beginner-brand"><span><BookOpenText size={20} /></span><div><strong>一树-A股观测台</strong><small>个股观察台</small></div></div>
    <nav aria-label="主要功能">
      {entries.map(([view, label, Icon]) => <button className={active === view ? "active" : ""} type="button" key={view} aria-current={active === view ? "page" : undefined} onClick={() => onNavigate(view)}><Icon size={18} /><span>{label}</span></button>)}
    </nav>
    <div className="asset-separator"><span>独立资产</span></div>
    <button className={`bond-navigation ${active === "bonds" ? "active" : ""}`} type="button" aria-label="可转债" onClick={() => onNavigate("bonds")}><BellRing size={18} /><span><b>可转债</b><small>独立观察空间</small></span></button>
    <TaskActivityStatus ai={ai} />
    <p className="beginner-company">上海一树电子商务有限公司</p>
    <p className="beginner-disclaimer">只做观察与风险提示<br />不连接券商，不构成投资建议</p>
  </aside>;
}
