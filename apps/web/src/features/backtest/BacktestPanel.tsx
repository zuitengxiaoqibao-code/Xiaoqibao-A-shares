import type { EChartsOption } from "echarts";
import { BarChart3, BookmarkPlus, Play, ShieldAlert } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { isAShareSymbol } from "../instrument-selection/SelectedInstrumentProvider";
import { QuantChart } from "../quant-analysis/QuantChart";
import type { BacktestRequest, BacktestResult, BacktestRunner, BacktestStrategy } from "./types";

type State = { kind: "idle" | "loading" } | { kind: "ready"; result: BacktestResult } | { kind: "error"; message: string };
type StrategyDefinition = { id: BacktestStrategy; name: string; summary: string; defaults: BacktestRequest };

const strategies: StrategyDefinition[] = [
  { id: "sma_cross", name: "双均线趋势", summary: "快线上穿慢线进入，下穿退出；适合趋势阶段。", defaults: { strategy: "sma_cross", fast_window: 5, slow_window: 20, stop_loss_percent: .06, take_profit_percent: .18, initial_cash: 1_000_000, commission_rate: .0003, slippage_rate: .0005 } },
  { id: "momentum_breakout", name: "动量突破", summary: "收盘突破近期高点进入，跌破退出均线离场。", defaults: { strategy: "momentum_breakout", lookback_window: 20, exit_window: 10, fast_window: 5, slow_window: 20, stop_loss_percent: .06, take_profit_percent: .18, initial_cash: 1_000_000, commission_rate: .0003, slippage_rate: .0005 } },
  { id: "low_volume_pullback", name: "趋势缩量回踩", summary: "趋势仍在时等待缩量回踩，不追高。", defaults: { strategy: "low_volume_pullback", fast_window: 5, slow_window: 20, volume_window: 20, volume_ratio: .8, lookback_window: 20, exit_window: 10, stop_loss_percent: .06, take_profit_percent: .18, initial_cash: 1_000_000, commission_rate: .0003, slippage_rate: .0005 } },
];
const strategyById = new Map(strategies.map((item) => [item.id, item]));
const segmentName = { train: "训练段", validation: "验证段", out_of_sample: "样本外" };
const regimeName = { bull: "上行阶段", bear: "下行阶段", sideways: "震荡阶段" };
const warningLabel: Record<string, string> = {
  corporate_actions_not_adjusted: "当前日线未统一复权，分红送转可能影响长期收益口径",
  benchmark_not_available: "未提供同期基准，暂不能判断超额收益",
  survivorship_bias_not_eliminated: "股票样本未消除幸存者偏差，历史结论需谨慎",
};
const percent = (value: string | number) => `${(Number(value) * 100).toFixed(2)}%`;
const ratio = (value: string | null) => value === null ? "--" : Number(value).toFixed(2);

function equityOption(result: BacktestResult): EChartsOption {
  return {
    animationDuration: 280,
    grid: { left: 58, right: 20, top: 28, bottom: 42 },
    tooltip: { trigger: "axis", backgroundColor: "#111a22", borderColor: "#466575", textStyle: { color: "#dce9ed", fontSize: 12 } },
    xAxis: { type: "category", data: result.equity_curve.map((item) => item.trade_date), axisLabel: { color: "#718795", fontSize: 12 }, axisLine: { lineStyle: { color: "#31434f" } } },
    yAxis: { type: "value", scale: true, axisLabel: { color: "#718795", fontSize: 12 }, splitLine: { lineStyle: { color: "rgba(70, 91, 105, .24)" } } },
    series: [{ name: "账户权益", type: "line", showSymbol: false, smooth: .18, data: result.equity_curve.map((item) => Number(item.equity)), lineStyle: { width: 2, color: "#53b8d4" }, areaStyle: { color: "rgba(51, 138, 166, .16)" } }],
  };
}

export function BacktestPanel({ symbol, runBacktest }: { symbol: string; runBacktest: BacktestRunner }) {
  const [state, setState] = useState<State>({ kind: "idle" });
  const [requestedSymbol, setRequestedSymbol] = useState(symbol);
  const [request, setRequest] = useState<BacktestRequest>(strategies[0].defaults);
  const [profileName, setProfileName] = useState("");
  const [savedProfiles, setSavedProfiles] = useState<Array<{ name: string; request: BacktestRequest }>>([]);
  const explicitlyEdited = useRef(false);
  const requestVersion = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const selectedStrategy = strategyById.get(request.strategy) ?? strategies[0];
  const option = useMemo(() => state.kind === "ready" && state.result.equity_curve.length ? equityOption(state.result) : null, [state]);

  function invalidateResult() { requestVersion.current += 1; controller.current?.abort(); controller.current = null; setState({ kind: "idle" }); }
  useEffect(() => { if (!explicitlyEdited.current) { setRequestedSymbol(symbol); invalidateResult(); } }, [symbol]);
  useEffect(() => {
    try { setSavedProfiles(JSON.parse(localStorage.getItem("qibao.backtest.profiles") ?? "[]")); } catch { setSavedProfiles([]); }
    return () => { requestVersion.current += 1; controller.current?.abort(); };
  }, []);

  function updateNumber(key: keyof BacktestRequest, value: string) { setRequest((current) => ({ ...current, [key]: Number(value) })); invalidateResult(); }
  function selectStrategy(value: BacktestStrategy) { setRequest(strategyById.get(value)?.defaults ?? strategies[0].defaults); invalidateResult(); }
  function saveProfile() {
    const name = profileName.trim(); if (!name) return;
    const next = [...savedProfiles.filter((item) => item.name !== name), { name, request }].slice(-8);
    setSavedProfiles(next); setProfileName("");
    try { localStorage.setItem("qibao.backtest.profiles", JSON.stringify(next)); } catch { /* Storage can be disabled in hardened desktop environments. */ }
  }
  async function run() {
    if (!isAShareSymbol(requestedSymbol)) return;
    const version = ++requestVersion.current; controller.current?.abort();
    const currentController = new AbortController(); controller.current = currentController; setState({ kind: "loading" });
    try { const result = await runBacktest(requestedSymbol, request, currentController.signal); if (version === requestVersion.current) setState({ kind: "ready", result }); }
    catch (error) { if (version === requestVersion.current && !currentController.signal.aborted) setState({ kind: "error", message: error instanceof Error ? error.message : "未知错误" }); }
    finally { if (version === requestVersion.current) controller.current = null; }
  }

  return <section className="backtest-panel backtest-workbench">
    <div className="backtest-heading"><div><p className="eyebrow">STRATEGY LAB / 本地日线</p><h2>策略历史回测工作台</h2><p>100 万元固定测算基准 · 不连接账户 · 次日开盘执行 · 计入费用与滑点</p></div><button type="button" onClick={() => void run()} disabled={state.kind === "loading" || !isAShareSymbol(requestedSymbol)}><Play size={15}/>{state.kind === "loading" ? "计算中" : "运行回测"}</button></div>
    <div className="backtest-config-grid">
      <section className="backtest-strategy-picker"><h3>策略模型</h3>{strategies.map((item) => <button type="button" key={item.id} aria-pressed={request.strategy === item.id} onClick={() => selectStrategy(item.id)}><b>{item.name}</b><span>{item.summary}</span></button>)}</section>
      <section className="backtest-parameters"><header><div><h3>{selectedStrategy.name}</h3><p>{selectedStrategy.summary}</p></div><label>回测 A 股代码<input aria-label="回测 A 股代码" inputMode="numeric" maxLength={6} pattern="\d{6}" value={requestedSymbol} onChange={(event) => { explicitlyEdited.current = true; setRequestedSymbol(event.target.value.replace(/\D/g, "")); invalidateResult(); }}/></label></header>
        <div className="backtest-parameter-grid">
          {request.strategy !== "momentum_breakout" && <><NumberField label="快线周期" value={request.fast_window} min={2} onChange={(value) => updateNumber("fast_window", value)}/><NumberField label="慢线周期" value={request.slow_window} min={3} onChange={(value) => updateNumber("slow_window", value)}/></>}
          {request.strategy === "momentum_breakout" && <><NumberField label="突破周期" value={request.lookback_window} min={5} onChange={(value) => updateNumber("lookback_window", value)}/><NumberField label="退出周期" value={request.exit_window} min={2} onChange={(value) => updateNumber("exit_window", value)}/></>}
          {request.strategy === "low_volume_pullback" && <><NumberField label="成交量周期" value={request.volume_window} min={5} onChange={(value) => updateNumber("volume_window", value)}/><NumberField label="缩量比例" value={request.volume_ratio} min={.1} step={.05} onChange={(value) => updateNumber("volume_ratio", value)}/></>}
          <NumberField label="止损比例" value={request.stop_loss_percent} min={.01} step={.01} onChange={(value) => updateNumber("stop_loss_percent", value)}/><NumberField label="止盈比例" value={request.take_profit_percent} min={.01} step={.01} onChange={(value) => updateNumber("take_profit_percent", value)}/><NumberField label="初始测算资金" value={request.initial_cash} min={10000} step={10000} onChange={(value) => updateNumber("initial_cash", value)}/><NumberField label="手续费率" value={request.commission_rate} min={0} step={.0001} onChange={(value) => updateNumber("commission_rate", value)}/><NumberField label="滑点率" value={request.slippage_rate} min={0} step={.0001} onChange={(value) => updateNumber("slippage_rate", value)}/>
        </div>
        <div className="backtest-profile-row"><input aria-label="参数方案名称" placeholder="参数方案名称" value={profileName} onChange={(event) => setProfileName(event.target.value)}/><button type="button" disabled={!profileName.trim()} onClick={saveProfile}><BookmarkPlus size={14}/>保存参数方案</button>{savedProfiles.map((profile) => <button className="saved-profile" type="button" key={profile.name} onClick={() => { setRequest(profile.request); invalidateResult(); }}>{profile.name}</button>)}</div>
      </section>
    </div>
    {state.kind === "idle" && <div className="backtest-empty">选择模型并检查参数后运行。结果只用于研究，不构成收益承诺。</div>}
    {state.kind === "loading" && <div className="backtest-empty" aria-busy="true">正在读取本地日线并逐笔复算...</div>}
    {state.kind === "error" && <div className="backtest-error" role="alert"><ShieldAlert size={17}/>{state.message}</div>}
    {state.kind === "ready" && <div className="backtest-result"><p className="backtest-result-symbol"><span>回测标的 {state.result.symbol}</span><b> · {selectedStrategy.name}</b></p>
      <div className="metric-grid"><Metric label="总收益" value={percent(state.result.total_return)} tone={Number(state.result.total_return) < 0 ? "negative" : "positive"}/><Metric label="年化收益" value={percent(state.result.metrics.annualized_return)} tone={Number(state.result.metrics.annualized_return) < 0 ? "negative" : "positive"}/><Metric label="最大回撤" value={percent(state.result.max_drawdown)}/><Metric label="年化波动率" value={percent(state.result.metrics.annualized_volatility)}/><Metric label="Sharpe" value={ratio(state.result.metrics.sharpe_ratio)} tone={Number(state.result.metrics.sharpe_ratio) < 0 ? "negative" : undefined}/><Metric label="Calmar" value={ratio(state.result.metrics.calmar_ratio)} tone={Number(state.result.metrics.calmar_ratio) < 0 ? "negative" : undefined}/><Metric label="闭合交易胜率" value={percent(state.result.metrics.win_rate)}/><Metric label="盈亏比" value={ratio(state.result.metrics.profit_loss_ratio)}/><Metric label="换手率" value={percent(state.result.metrics.turnover_rate)}/><Metric label="交易成本" value={state.result.total_cost}/><Metric label="成交次数" value={`${state.result.trades.length} 笔`}/></div>
      {option && <section className="backtest-equity"><header><BarChart3 size={16}/><div><h3>账户权益曲线</h3><small>按交易日收盘权益绘制</small></div></header><QuantChart option={option} ariaLabel="回测账户权益曲线"/></section>}
      {state.result.warnings.length > 0 && <section className="backtest-warnings"><h3>执行警告</h3>{state.result.warnings.map((item) => <p key={item}><ShieldAlert size={14}/>{warningLabel[item] ?? item}</p>)}</section>}
      {state.result.segments.length > 0 && <section className="segment-analysis"><header><div><p className="eyebrow">STABILITY CHECK</p><h3>样本稳定性</h3></div><small>训练、验证与样本外连续切片；反复调参会削弱样本外结论</small></header><div className="segment-table" role="table" aria-label="回测样本分段">{state.result.segments.map((segment) => <div role="row" key={segment.name} className={segment.name === "out_of_sample" ? "emphasis" : ""}><span>{segmentName[segment.name]}</span><time>{segment.start_date} 至 {segment.end_date}</time><b className={Number(segment.total_return) < 0 ? "negative-metric" : "positive-metric"}>{percent(segment.total_return)}</b><small>回撤 {percent(segment.max_drawdown)} · {segment.bar_count} 日</small></div>)}</div></section>}
      <section className="regime-analysis"><header><BarChart3 size={16}/><div><h3>市场阶段归因</h3><small>分类只使用当日及过去行情，不参与信号生成</small></div></header><div>{state.result.market_regimes.map((regime) => <div key={regime.name}><span>{regimeName[regime.name]}</span><b className={Number(regime.total_return) < 0 ? "negative-metric" : "positive-metric"}>{percent(regime.total_return)}</b><small>{regime.bar_count} 个交易日</small></div>)}</div></section>
      {state.result.trades.length > 0 && <section className="backtest-trades"><header><h3>交易明细</h3><small>信号日与实际成交日分开显示</small></header><div><table><thead><tr><th>方向</th><th>信号日</th><th>成交日</th><th>成交价</th><th>数量</th><th>费用</th></tr></thead><tbody>{state.result.trades.slice(-50).map((trade, index) => <tr key={`${trade.trade_date}-${index}`}><td className={trade.side === "buy" ? "positive-metric" : "negative-metric"}>{trade.side === "buy" ? "买入" : "卖出"}</td><td>{trade.signal_date ?? "--"}</td><td>{trade.trade_date ?? "--"}</td><td>{trade.price ?? "--"}</td><td>{trade.shares ?? "--"}</td><td>{trade.fees ?? "--"}</td></tr>)}</tbody></table></div></section>}
    </div>}
  </section>;
}

function NumberField({ label, value, min, step = 1, onChange }: { label: string; value?: number; min: number; step?: number; onChange: (value: string) => void }) { return <label>{label}<input aria-label={label} type="number" value={value ?? ""} min={min} step={step} onChange={(event) => onChange(event.target.value)}/></label>; }
function Metric({ label, value, tone }: { label: string; value: string; tone?: "positive" | "negative" }) { return <div><span>{label}</span><b className={tone ? `${tone}-metric` : undefined}>{value}</b></div>; }
