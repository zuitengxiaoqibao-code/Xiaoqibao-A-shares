import {
  Activity, BarChart3, BellRing, BookOpenText, CandlestickChart, CircleDot, Gauge, History, LayoutDashboard, LibraryBig, Newspaper, ServerCog, Settings2,
  ShieldAlert, Sparkles, ChartNoAxesCombined,
} from "lucide-react";

export type BeginnerView = "market_overview" | "dashboard" | "a_shares" | "company_research" | "first_limit_up" | "late_session_selection" | "quant_analysis" | "data_screen" | "monitor_center" | "news" | "risk" | "history" | "settings" | "operations" | "bonds" | "market_cloud" | "yishu_intelligence";

const groups = [
  { label: "工作台", entries: [["market_overview", "信息总览", LayoutDashboard], ["data_screen", "数据大屏", Gauge], ["dashboard", "今日研判", Sparkles]] },
  { label: "个股研究", entries: [["a_shares", "个股观察", CandlestickChart], ["company_research", "公司研究", LibraryBig]] },
  { label: "策略筛选", entries: [["first_limit_up", "首次涨停", CircleDot], ["late_session_selection", "尾盘选股", Activity], ["quant_analysis", "量化分析", BarChart3]] },
  { label: "资讯风控", entries: [["news", "新闻热点", Newspaper], ["risk", "风险提醒", ShieldAlert], ["history", "历史复盘", History], ["monitor_center", "监控中心", BellRing]] },
] as const;

export function BeginnerNavigation({ active, onNavigate }: {
  active: BeginnerView;
  onNavigate: (view: BeginnerView) => void;
}) {
  return <aside className="terminal-navigation beginner-sidebar">
    <div className="beginner-brand"><span><BookOpenText size={20} /></span><div><strong>易数-A股观测台</strong><small>个股观察台</small></div></div>
    <div className="beginner-sidebar-scroll">
      <nav aria-label="主要功能">
        {groups.map(({ label, entries }) => <section className="navigation-group" key={label}>
          <h2>{label}</h2>
          <div className="navigation-group-items">
            {entries.map(([view, entryLabel, Icon]) => <button className={active === view ? "active" : ""} type="button" key={view} aria-current={active === view ? "page" : undefined} onClick={() => onNavigate(view)}><Icon size={18} /><span>{entryLabel}</span></button>)}
          </div>
        </section>)}
        <section className="navigation-group navigation-group-asset">
          <h2>特色工具</h2>
          <button className={`bond-navigation ${active === "market_cloud" ? "active" : ""}`} type="button" aria-label="大盘云图" aria-current={active === "market_cloud" ? "page" : undefined} onClick={() => onNavigate("market_cloud")}><ChartNoAxesCombined size={18} /><span><b>大盘云图</b><small>全市场行情热力图</small></span></button>
        </section>
      </nav>
    </div>
    <div className="beginner-sidebar-bottom">
      <div className="navigation-bottom-group" aria-label="系统设置">
        <h2>系统</h2>
        <button className={active === "settings" ? "active" : ""} type="button" aria-current={active === "settings" ? "page" : undefined} onClick={() => onNavigate("settings")}><Settings2 size={18} /><span>数据设置</span></button>
        <button className={active === "operations" ? "active" : ""} type="button" aria-current={active === "operations" ? "page" : undefined} onClick={() => onNavigate("operations")}><ServerCog size={18} /><span>本地运维</span></button>
      </div>
      <button className={`yishu-intelligence-entry ${active === "yishu_intelligence" ? "active" : ""}`} type="button" aria-current={active === "yishu_intelligence" ? "page" : undefined} onClick={() => onNavigate("yishu_intelligence")}><Sparkles size={18} /><span><b>易数智算</b><small>发现与智能服务</small></span></button>
      <p className="beginner-disclaimer">只做观察与风险提示<br />不连接券商，不构成投资建议</p>
    </div>
  </aside>;
}
