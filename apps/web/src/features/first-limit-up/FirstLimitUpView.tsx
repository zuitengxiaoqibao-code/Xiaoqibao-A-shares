import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle, CheckCircle2, CircleDot, Database, Info, LoaderCircle,
  RefreshCw, ShieldAlert, Target,
} from "lucide-react";

import type { FirstLimitUpBoard, FirstLimitUpCandidate } from "./types";


type Props = {
  load: () => Promise<FirstLimitUpBoard>;
  refresh: () => Promise<FirstLimitUpBoard>;
};

type Tab = "today" | "pool";
type CandidateFilter = "all" | "qualified" | "pullback" | "no_buy";

const filterNames: Record<CandidateFilter, string> = {
  all: "全部股票",
  qualified: "规则合格",
  pullback: "回撤窗口",
  no_buy: "涨停日禁买",
};

const sourceNames: Record<string, string> = {
  "local-daily-bars": "本地日线",
  "tencent-quote": "腾讯行情",
  "pe-unavailable": "市盈率暂不可用",
};

const missingDataNames: Record<string, string> = {
  full_market_scan_required: "当前尚未完成全市场筛选，请刷新或等待盘后任务",
};

const reasonNames: Record<string, string> = {
  outside_shenzhen_shanghai_scope: "不在沪深 A 股筛选范围内",
  st_or_delisting_name: "ST 或退市风险标的已排除",
  recent_limit_up_within_20_bars: "近 20 个交易日内已有涨停，不属于阶段首次涨停",
  pe_missing: "市盈率数据缺失",
  pe_not_positive: "市盈率为零或负数",
  pe_above_50: "市盈率超过 50 倍",
  weekly_not_at_bottom: "周线位置不在底部区域",
  monthly_not_at_bottom: "月线位置不在底部区域",
  weekly_history_insufficient: "周线历史数据不足",
  monthly_history_insufficient: "月线历史数据不足",
};

const riskNames: Record<string, string> = {
  limit_up_day_no_buy: "涨停当日只记录，不买入",
  history_insufficient: "历史行情不足，暂不能完整判断",
  pullback_above_20_percent: "较涨停收盘价回撤超过 20%",
};

const stageNames: Record<FirstLimitUpCandidate["stage"], string> = {
  limit_up_day: "涨停当日",
  waiting_pullback: "等待回撤",
  pullback_window: "回撤窗口",
  risk_expanded: "风险扩大",
  data_insufficient: "待验证",
};

const actionNames: Record<FirstLimitUpCandidate["action"], string> = {
  no_buy: "禁止买入",
  observe: "仅观察",
  staged_entry_reference: "分批参考",
  avoid: "回避",
  data_insufficient: "数据不足",
};

function pct(value: string | null, digits = 1): string {
  if (value === null || value === "") return "待验证";
  const number = Number(value);
  return Number.isFinite(number) ? `${(number * 100).toFixed(digits)}%` : "待验证";
}

function peLabel(value: string | null): string {
  if (value === null || value.trim() === "") return "待验证";
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}x` : "待验证";
}

function tone(candidate: FirstLimitUpCandidate): "positive" | "warning" | "danger" | "muted" {
  if (candidate.action === "avoid" || candidate.stage === "risk_expanded") return "danger";
  if (candidate.action === "no_buy" || candidate.action === "data_insufficient") return "warning";
  if (candidate.action === "staged_entry_reference") return "positive";
  return "muted";
}

function bottomStatus(value: boolean | null): string {
  return value === true ? "通过" : value === false ? "未通过" : "待验证";
}

function sourceLabel(source: string): string {
  return sourceNames[source] ?? source;
}

function missingDataLabel(code: string): string {
  return missingDataNames[code] ?? code;
}

function friendlyCodeLabel(code: string, names: Record<string, string>, fallback: string): string {
  if (names[code]) return names[code];
  return /^[a-z0-9_-]+$/i.test(code) ? fallback : code;
}

function reasonLabel(reason: string): string {
  return friendlyCodeLabel(reason, reasonNames, "其他筛选规则未通过");
}

function riskLabel(risk: string): string {
  return friendlyCodeLabel(risk, riskNames, "存在其他风险项，请核对数据");
}

function ladderUnavailableMessage(candidate: FirstLimitUpCandidate): string {
  if (candidate.selection_status === "excluded") return "当前规则未通过，不适用分批观察阶梯。";
  if (candidate.selection_status === "data_insufficient" || candidate.action === "data_insufficient") return "关键数据尚未完整，不适用分批观察阶梯。";
  if (candidate.action === "no_buy") return "涨停当日禁止买入，暂不启用分批观察阶梯。";
  if (candidate.action === "observe") return "尚未形成 5%–20% 回撤和横盘窗口，暂不启用分批观察阶梯。";
  if (candidate.action === "avoid") return "风险条件已触发，不适用分批观察阶梯。";
  return "仍有风险项，暂不启用分批观察阶梯。";
}

function CandidateRow({ candidate, selected, onSelect }: { candidate: FirstLimitUpCandidate; selected: boolean; onSelect: () => void }) {
  return <button type="button" className={`first-limit-up-row ${selected ? "selected" : ""}`} onClick={onSelect} aria-pressed={selected}>
    <span className="first-limit-up-symbol"><b>{candidate.symbol}</b><small>{candidate.name}</small></span>
    <span className={`first-limit-up-stage ${tone(candidate)}`}>{stageNames[candidate.stage]}</span>
    <span className="first-limit-up-number">{peLabel(candidate.pe_ttm)}<small>PE</small></span>
    <span className="first-limit-up-number"><small>周线底部：</small>{bottomStatus(candidate.weekly_bottom)}</span>
    <span className="first-limit-up-number"><small>月线底部：</small>{bottomStatus(candidate.monthly_bottom)}</span>
    <span className="first-limit-up-number">{pct(candidate.pullback_pct)}<small>回撤</small></span>
    <strong className="first-limit-up-score">{Number(candidate.score).toFixed(1)}</strong>
  </button>;
}

function Detail({ candidate }: { candidate: FirstLimitUpCandidate }) {
  const evidenceIncomplete = candidate.selection_status === "data_insufficient" || candidate.action === "data_insufficient";
  const showLadder = candidate.action === "staged_entry_reference" && candidate.risk_flags.length === 0;
  return <section className={`first-limit-up-detail ${tone(candidate)}`} aria-label="首次涨停标的详情">
    <header>
      <div><p className="eyebrow">EVIDENCE / FIRST LIMIT-UP</p><h2>{candidate.name} <span>{candidate.symbol}</span></h2></div>
      <span className={`first-limit-up-action ${tone(candidate)}`}>{actionNames[candidate.action]}</span>
    </header>
    {candidate.selection_status === "excluded" && <div className="first-limit-up-alert danger"><AlertTriangle size={18} /><div><b>规则未通过，暂不进入观察池</b><p>数据足以完成判断，但该股票不符合当前首次涨停筛选规则，请查看下方未通过原因。</p></div></div>}
    {evidenceIncomplete && <div className="first-limit-up-alert warning"><Info size={18} /><div><b>关键数据待补齐</b><p>现有证据不足以完成判断，补齐历史行情或估值数据后再重新筛选。</p></div></div>}
    {candidate.action === "no_buy" && <div className="first-limit-up-alert danger"><ShieldAlert size={18} /><div><b>涨停当日不能买入</b><p>今日只记录进池，等后续出现 5%–20% 回撤并横盘观察后再评估。</p></div></div>}
    {candidate.action === "staged_entry_reference" && <div className="first-limit-up-alert positive"><CheckCircle2 size={18} /><div><b>进入回撤窗口</b><p>这是规则筛选出的观察窗口，不是自动买入信号；先核对数据新鲜度和风险项。</p></div></div>}
    {candidate.stage === "risk_expanded" && candidate.action === "avoid" && <div className="first-limit-up-alert danger"><AlertTriangle size={18} /><div><b>回撤超过 20%</b><p>不再按原规则补仓，等待新的结构确认。</p></div></div>}
    <dl className="first-limit-up-metrics">
      <div><dt>优先观察分</dt><dd>{Number(candidate.score).toFixed(1)}</dd></div>
      <div><dt>市盈率 TTM</dt><dd>{peLabel(candidate.pe_ttm).replace("x", " 倍")}</dd></div>
      <div><dt>周线底部</dt><dd>{bottomStatus(candidate.weekly_bottom)}</dd></div>
      <div><dt>月线底部</dt><dd>{bottomStatus(candidate.monthly_bottom)}</dd></div>
      <div><dt>涨停收盘价</dt><dd>{candidate.limit_up_close}</dd></div>
      <div><dt>当前收盘价</dt><dd>{candidate.current_close}</dd></div>
      <div><dt>回撤幅度</dt><dd>{pct(candidate.pullback_pct)}</dd></div>
      <div><dt>横盘观察</dt><dd>{candidate.consolidation_days ? `${candidate.consolidation_days} 个交易日` : "待形成"}</dd></div>
    </dl>
    <div className="first-limit-up-evidence-grid">
      <section><header><Target size={15} /><b>规则证据</b></header><ul>
        <li>阶段首板日期：{candidate.limit_up_date}</li>
        <li>周线距低点：{pct(candidate.weekly_distance_to_low)}</li>
        <li>月线距低点：{pct(candidate.monthly_distance_to_low)}</li>
        {candidate.reasons.map((reason) => <li key={reason} className="danger-text">{candidate.selection_status === "data_insufficient" ? "待核对：" : "未通过："}{reasonLabel(reason)}</li>)}
        {candidate.selection_status === "excluded"
          ? <li className="danger-text">规则未通过，暂不进入观察池</li>
          : evidenceIncomplete
            ? <li>数据不足，暂不判定通过</li>
            : <li className="positive-text">估值与周/月线位置通过</li>}
      </ul></section>
      <section><header><CircleDot size={15} /><b>分批观察阶梯</b></header>{showLadder ? <><p>当前处于“分批参考”状态且没有风险标记，可按阶梯继续观察：</p><div className="first-limit-up-steps"><span><b>回撤观察</b>{candidate.entry_reference.buy_steps_pct.map((step) => <i key={step}>{pct(step, 0)}</i>)}</span><span><b>分段止盈</b>{candidate.entry_reference.sell_steps_pct.map((step) => <i key={step}>+{pct(step, 0)}</i>)}</span></div><small>{candidate.entry_reference.note}</small></> : <p className="first-limit-up-ladder-unavailable">{ladderUnavailableMessage(candidate)}</p>}</section>
    </div>
    {candidate.risk_flags.length > 0 && <div className="first-limit-up-risk-list"><Info size={15} /><span>风险标记：{candidate.risk_flags.map(riskLabel).join(" / ")}</span></div>}
  </section>;
}

export function FirstLimitUpView({ load, refresh }: Props) {
  const [board, setBoard] = useState<FirstLimitUpBoard | null>(null);
  const [tab, setTab] = useState<Tab>("today");
  const [filter, setFilter] = useState<CandidateFilter>("all");
  const [selected, setSelected] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setState("loading");
    void load().then((value) => { if (active) { setBoard(value); setSelected(value.today[0]?.symbol ?? value.pool[0]?.symbol ?? null); setState("ready"); setError(""); } }).catch((reason) => { if (active) { setState("error"); setError(reason instanceof Error ? reason.message : "首次涨停数据暂不可用"); } });
    return () => { active = false; };
  }, [load]);

  const sourceEntries = useMemo(() => tab === "today" ? board?.today ?? [] : board?.pool ?? [], [board, tab]);
  const entries = useMemo(() => sourceEntries.filter((candidate) => {
    if (filter === "qualified") return candidate.selection_status === "qualified";
    if (filter === "pullback") return candidate.stage === "pullback_window";
    if (filter === "no_buy") return candidate.action === "no_buy";
    return true;
  }), [filter, sourceEntries]);
  useEffect(() => {
    if (!entries.length) { setSelected(null); return; }
    if (!selected || !entries.some((item) => item.symbol === selected)) setSelected(entries[0].symbol);
  }, [entries, selected]);
  const selectedCandidate = entries.find((item) => item.symbol === selected) ?? null;
  const priorityCandidate = board && [...board.today, ...board.pool].find((item) => item.symbol === board.priority_symbol);
  const listTitle = filter === "all"
    ? tab === "today" ? "本次已识别涨停" : "历史观察分组"
    : filterNames[filter];

  function selectSummaryFilter(nextTab: Tab, nextFilter: CandidateFilter) {
    setTab(nextTab);
    setFilter(nextFilter);
  }

  function selectTab(nextTab: Tab) {
    setTab(nextTab);
    setFilter("all");
  }

  async function refreshBoard() {
    setRefreshing(true); setError("");
    try { const value = await refresh(); setBoard(value); setSelected((current) => current ?? value.today[0]?.symbol ?? value.pool[0]?.symbol ?? null); setState("ready"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "刷新失败"); }
    finally { setRefreshing(false); }
  }

  return <main className="terminal-page first-limit-up-page" aria-label="首次涨停研究域">
    <header className="first-limit-up-header"><div><p className="eyebrow">A SHARE / POSTCLOSE SCREEN</p><h1>首次涨停</h1><p>收盘后筛选阶段首板，等待估值、周/月线位置和回撤结构共同确认。</p></div><div className="first-limit-up-header-meta"><span><Database size={15} />数据截至</span><b>{board?.as_of ?? "待扫描"}</b><button type="button" aria-label="刷新首次涨停" onClick={() => void refreshBoard()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? "spin" : ""} /></button></div></header>
    {error && <div className="first-limit-up-error" role="alert"><ShieldAlert size={17} /><span>{error}</span></div>}
    {board?.missing_data.length ? <div className="first-limit-up-missing" role="status"><AlertTriangle size={16} /><span>部分数据待验证：{board.missing_data.map(missingDataLabel).join(" / ")}</span></div> : null}
    {board && !board.coverage_complete && <div className="first-limit-up-coverage-warning" role="status"><AlertTriangle size={18} /><div><b>当前仅为部分市场结果</b><p>日线仍在补全；这里只展示本次扫描实际识别结果，不使用其他批次候选补位。</p></div><strong>{board.scan_coverage_count.toLocaleString("zh-CN")} / {board.universe_count.toLocaleString("zh-CN")}</strong><small>具备 250 日历史：{board.history_eligible_count.toLocaleString("zh-CN")} 只</small></div>}
    <section className="first-limit-up-summary" aria-label="首次涨停摘要">
      <button type="button" className="first-limit-up-summary-filter" aria-pressed={tab === "today" && filter === "all"} aria-label={`筛选已识别涨停股票，共 ${board?.scanned_count ?? 0} 只`} onClick={() => selectSummaryFilter("today", "all")}><span>已识别涨停</span><strong>{board?.scanned_count ?? "--"} 只</strong><small>点击查看本次全部明细</small></button>
      <button type="button" className="first-limit-up-summary-filter" aria-pressed={tab === "today" && filter === "qualified"} aria-label={`筛选规则合格股票，共 ${board?.qualified_count ?? 0} 只`} onClick={() => selectSummaryFilter("today", "qualified")}><span>规则合格</span><strong>{board?.qualified_count ?? "--"} 只</strong><small>点击查看通过规则的股票</small></button>
      <button type="button" className="first-limit-up-summary-filter" aria-pressed={tab === "pool" && filter === "pullback"} aria-label={`筛选回撤窗口股票，共 ${board?.pullback_window_count ?? 0} 只`} onClick={() => selectSummaryFilter("pool", "pullback")}><span>回撤窗口</span><strong>{board?.pullback_window_count ?? "--"} 只</strong><small>点击查看 5%–20% 回撤明细</small></button>
      <button type="button" className="first-limit-up-summary-filter warning" aria-pressed={tab === "today" && filter === "no_buy"} aria-label={`筛选涨停日禁买股票，共 ${board?.no_buy_count ?? 0} 只`} onClick={() => selectSummaryFilter("today", "no_buy")}><span>涨停日禁买</span><strong>{board?.no_buy_count ?? "--"} 只</strong><small>点击查看禁买原因与证据</small></button>
      <div><span>数据来源</span><strong>{board?.sources.map(sourceLabel).join(" / ") || "暂无"}</strong><small>用于本次盘后筛选</small></div>
      <div><span>优先观察项</span><strong>{priorityCandidate ? `${priorityCandidate.symbol} · ${priorityCandidate.name}` : board?.priority_symbol ?? "暂无"}</strong><small>综合规则排序，非收益概率</small></div>
    </section>
    <div className="first-limit-up-tabs" role="tablist" aria-label="首次涨停分组"><button role="tab" aria-selected={tab === "today"} type="button" onClick={() => selectTab("today")}>识别结果</button><button role="tab" aria-selected={tab === "pool"} type="button" onClick={() => selectTab("pool")}>回撤池</button></div>
    <div className="first-limit-up-layout"><section className="first-limit-up-list" aria-label="首次涨停候选列表"><header><div><p className="eyebrow">POOL / {tab === "today" ? "DETECTED" : "PULLBACK"}</p><h2>{listTitle} · {entries.length} 只</h2></div><div className="first-limit-up-list-actions"><span>{entries.length.toString().padStart(2, "0")}</span>{filter !== "all" && <button type="button" onClick={() => setFilter("all")} aria-label="查看当前分组全部股票">查看全部</button>}</div></header>{state === "loading" && <div className="first-limit-up-empty" role="status" aria-busy="true"><LoaderCircle className="spin" size={22} /><b>正在读取收盘筛选...</b></div>}{state === "error" && <div className="first-limit-up-empty danger"><ShieldAlert size={22} /><b>筛选数据暂不可用</b></div>}{state === "ready" && !entries.length && <div className="first-limit-up-empty"><Database size={25} /><b>{filter === "all" ? tab === "today" ? "本次没有识别到涨停记录" : "回撤池尚未形成" : `当前没有${filterNames[filter]}股票`}</b><p>{filter === "all" ? "先同步覆盖足够的日线历史，盘后扫描会持续把识别结果和规则证据保留下来。" : "该数字为零或当前真实明细为空；可点击“查看全部”返回当前分组。"}</p></div>}{state === "ready" && entries.length > 0 && <div className="first-limit-up-rows">{entries.map((candidate) => <CandidateRow key={`${candidate.symbol}-${candidate.limit_up_date}`} candidate={candidate} selected={candidate.symbol === selected} onSelect={() => setSelected(candidate.symbol)} />)}</div>}<footer>当前筛选：{filter === "all" ? "全部股票" : filterNames[filter]} · 收盘后更新 · 不构成投资建议</footer></section>{selectedCandidate ? <Detail candidate={selectedCandidate} /> : <section className="first-limit-up-detail first-limit-up-detail-empty"><Database size={30} /><b>{filter === "all" ? "选择一只股票查看证据" : `没有可展示的${filterNames[filter]}明细`}</b><p>{filter === "all" ? "列表记录可能包含待验证项，点击后查看证据。" : "当前筛选没有匹配股票，可查看全部或切换其他统计项。"}</p></section>}</div>
    <section className="first-limit-up-rules"><header><Info size={16} /><div><b>新手规则速览</b><span>先看红色提醒，再看绿色窗口</span></div></header><div><p><strong>1</strong>涨停当天坚决不买。</p><p><strong>2</strong>PE 必须为正且 ≤ 50。</p><p><strong>3</strong>周线、月线都要处于底部附近。</p><p><strong>4</strong>涨停后回撤 5%–20%，横盘后才进入分批观察。</p></div></section>
  </main>;
}
