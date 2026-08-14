import { type FormEvent, useState } from "react";
import { Archive, Clock3, NotebookPen, ShieldCheck, TrendingDown } from "lucide-react";

import type { DecisionJournalAction, DecisionJournalCreate, DecisionJournalEntry, QuantCalibrationReport, QuantShadowAnalytics, QuantShadowDecisionRecord } from "./types";

type Props = {
  records: QuantShadowDecisionRecord[];
  loading: boolean;
  error: string;
  analytics?: QuantShadowAnalytics | null;
  analyticsLoading?: boolean;
  analyticsError?: string;
  calibration?: QuantCalibrationReport | null;
  journalRecords?: DecisionJournalEntry[];
  journalSymbol?: string | null;
  journalLoading?: boolean;
  journalError?: string;
  onJournalCreate?: (request: DecisionJournalCreate) => Promise<void>;
};

function percent(value: string | null): string {
  if (value === null || value === "") return "--";
  const number = Number(value);
  return Number.isFinite(number) ? `${number >= 0 ? "+" : ""}${number.toFixed(2)}%` : "--";
}

function statusLabel(status: QuantShadowDecisionRecord["candidate_status"]): string {
  return status === "alert" ? "提醒" : status === "watch" ? "观察" : status === "reject" ? "排除" : "待触发";
}

function valueOrDash(value: string | null, suffix = ""): string {
  if (value === null || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? `${parsed.toFixed(2)}${suffix}` : "--";
}

function driftLabel(status: QuantShadowAnalytics["drift"]["status"]): string {
  if (status === "stable") return "暂未漂移";
  if (status === "warning") return "漂移预警";
  if (status === "drift") return "已检测漂移";
  return "样本不足";
}

function regimeKey(regime: NonNullable<QuantShadowAnalytics["regime_performance"]>[number]["regime"]): string {
  if (regime === "情绪主升") return "emotion-rise";
  if (regime === "指数权重进攻") return "index-attack";
  if (regime === "轮动震荡") return "rotation";
  if (regime === "冰点修复") return "ice-repair";
  if (regime === "高位退潮") return "high-retreat";
  return "low-volume";
}

const journalActionLabels: Record<DecisionJournalAction, string> = {
  observe: "继续观察",
  no_trade: "不交易",
  buy: "人工买入记录",
  sell: "人工卖出记录",
};

export function QuantShadowLedgerPanel({ records, loading, error, analytics = null, analyticsLoading = false, analyticsError = "", calibration = null, journalRecords = [], journalSymbol = null, journalLoading = false, journalError = "", onJournalCreate }: Props) {
  const [journalAction, setJournalAction] = useState<DecisionJournalAction>("observe");
  const [journalNote, setJournalNote] = useState("");
  const [journalPrice, setJournalPrice] = useState("");
  const [journalQuantity, setJournalQuantity] = useState("");
  const [journalSaving, setJournalSaving] = useState(false);
  const [journalSaveError, setJournalSaveError] = useState("");
  const submitJournal = async (event: FormEvent) => {
    event.preventDefault();
    if (!onJournalCreate || !journalSymbol || !journalNote.trim()) return;
    setJournalSaving(true);
    setJournalSaveError("");
    try {
      await onJournalCreate({
        decision_id: null,
        symbol: journalSymbol,
        action: journalAction,
        recorded_at: new Date().toISOString(),
        actual_price: journalPrice.trim() || null,
        quantity: journalQuantity.trim() || null,
        note: journalNote.trim(),
        market_regime: null,
        screener_session_id: null,
        snapshot_hash: null,
        observation_reason: journalNote.trim(),
        risks: [],
        invalidation_conditions: [],
      });
      setJournalNote("");
      setJournalPrice("");
      setJournalQuantity("");
    } catch {
      setJournalSaveError("复盘日志写入失败，原有记录未受影响");
    } finally {
      setJournalSaving(false);
    }
  };
  return <section className="quant-shadow-panel" aria-label="策略影子跟踪">
    <header className="quant-shadow-header">
      <div><span><Archive size={15} /> Q5 / SHADOW LEDGER</span><h2>策略影子跟踪</h2></div>
      <small>只记录历史决策，不回填未来结果</small>
    </header>
    {(analytics || analyticsLoading || analyticsError) && <section className="quant-shadow-analytics" aria-label="评分校准与漂移">
      <header><div><TrendingDown size={16} /><h3>评分校准与漂移</h3></div><small>{analytics ? `${analytics.horizon} 个交易日真实结果` : "正在读取统计"}</small></header>
      {analyticsLoading && !analytics && <div className="quant-shadow-analytics-state" role="status">正在计算成熟样本统计…</div>}
      {analyticsError && !analytics && <div className="quant-shadow-analytics-state error" role="alert">{analyticsError}</div>}
      {analytics && <>
        <div className="quant-shadow-kpis">
          <div><span>成熟样本</span><strong>{analytics.mature_sample_count} 条</strong><small>待评估 {analytics.pending_sample_count} 条</small></div>
          <div><span>实际命中率</span><strong>{valueOrDash(analytics.hit_rate_percent, "%")}</strong><small>收益为正定义为命中</small></div>
          <div><span>平均收益</span><strong className={Number(analytics.average_return_percent) >= 0 ? "up" : "down"}>{valueOrDash(analytics.average_return_percent, "%")}</strong><small>MFE {valueOrDash(analytics.average_mfe_percent, "%")} · MAE {valueOrDash(analytics.average_mae_percent, "%")}</small></div>
          <div><span>Brier 误差</span><strong>{valueOrDash(analytics.brier_score)}</strong><small>越接近 0 越好</small></div>
          <div data-drift={analytics.drift.status}><span>漂移状态</span><strong>{driftLabel(analytics.drift.status)}</strong><small>近期 {analytics.drift.recent_sample_count} · 基线 {analytics.drift.baseline_sample_count}</small></div>
        </div>
        <div className="quant-shadow-buckets">
          {analytics.buckets.map((bucket) => <article key={bucket.label} data-status={bucket.status}>
            <header><b>{bucket.label} 分</b><span>{bucket.sample_count} 条</span></header>
            <strong>{bucket.status === "ready" ? valueOrDash(bucket.hit_rate_percent, "%") : "样本不足"}</strong>
            <small>{bucket.status === "ready" ? `均分 ${valueOrDash(bucket.average_score)} · 校准差 ${valueOrDash(bucket.calibration_gap_percent, "pp")}` : "至少需要 5 条成熟结果"}</small>
          </article>)}
        </div>
        {analytics.regime_performance?.some((item) => item.sample_count > 0) && <section className="quant-shadow-regimes" aria-label="分市场风格真实绩效">
          <header>
            <div><span>REGIME PERFORMANCE</span><h4>分市场风格真实绩效</h4></div>
            <small>仅统计冻结时已记录市场风格的成熟真实结果</small>
          </header>
          <div>
            {analytics.regime_performance.filter((item) => item.sample_count > 0).map((item) => {
              const expectedValue = Number(item.expected_value_percent);
              const returnTone = Number.isFinite(expectedValue) && expectedValue >= 0 ? "up" : "down";
              return <article key={item.regime} data-regime={regimeKey(item.regime)}>
                <header><b>{item.regime}</b><span>{item.sample_count} 个成熟样本</span></header>
                <div className="quant-shadow-regime-primary">
                  <div><span>真实命中率</span><strong>{valueOrDash(item.hit_rate_percent, "%")}</strong></div>
                  <div><span>单笔 EV</span><strong className={returnTone}>EV {percent(item.expected_value_percent)}</strong></div>
                </div>
                <dl>
                  <div><dt>盈亏比</dt><dd>{valueOrDash(item.profit_loss_ratio)}</dd></div>
                  <div><dt>最大回撤</dt><dd>{valueOrDash(item.max_drawdown_percent, "%")}</dd></div>
                  <div><dt>Sharpe</dt><dd>{valueOrDash(item.sharpe_ratio)}</dd></div>
                  <div><dt>风险序列</dt><dd>连续亏损 {item.max_consecutive_losses}</dd></div>
                </dl>
              </article>;
            })}
          </div>
        </section>}
        {(analytics.drift.reasons.length > 0 || analytics.limitations.length > 0) && <div className="quant-shadow-findings">
          {[...analytics.drift.reasons, ...analytics.limitations].map((item) => <span key={item}>{item}</span>)}
        </div>}
      </>}
    </section>}
    {calibration && <section className="quant-shadow-analytics" aria-label="量化走样校准报告">
      <header><div><TrendingDown size={16} /><h3>量化走样校准报告</h3></div><small>{calibration.horizon} 日 · {calibration.status === "ready" ? "证据完整" : calibration.status === "partial" ? "部分证据" : "不可用"}</small></header>
      <div className="quant-shadow-kpis">
        <div><span>总样本</span><strong>{calibration.total_sample_count} 条</strong><small>成熟 {calibration.mature_sample_count} 条</small></div>
        <div><span>未来函数检查</span><strong>{calibration.integrity.future_function_check === "passed" ? "通过" : calibration.integrity.future_function_check === "failed" ? "失败" : "不可用"}</strong></div>
        <div><span>生存者偏差检查</span><strong>{calibration.integrity.survivorship_check === "passed" ? "通过" : calibration.integrity.survivorship_check === "failed" ? "失败" : "不可用"}</strong></div>
        <div><span>重复决策检查</span><strong>{calibration.integrity.duplicate_decision_check === "passed" ? "通过" : "失败"}</strong></div>
      </div>
      {(calibration.limitations.length > 0 || calibration.integrity.limitations.length > 0) && <div className="quant-shadow-findings">{[...calibration.limitations, ...calibration.integrity.limitations].map((item, index) => <span key={`${item}-${index}`}>{item}</span>)}</div>}
    </section>}
    {loading && !records.length && <div className="quant-shadow-empty" role="status"><Clock3 size={18} /><b>正在读取冻结决策</b></div>}
    {error && <div className="quant-shadow-empty error" role="alert"><b>{error}</b><p>保留上一次真实账本，不用空响应覆盖。</p></div>}
    {!loading && !error && !records.length && <div className="quant-shadow-empty"><ShieldCheck size={18} /><b>暂无已冻结的策略决策</b><p>候选扫描完成并形成策略快照后才会写入账本。</p></div>}
    {records.length > 0 && <div className="quant-shadow-records">
      {records.slice(0, 12).map((record) => <article key={record.decision_id} className="quant-shadow-record">
        <header><div><strong>{record.symbol}</strong><span>{statusLabel(record.candidate_status)}</span></div><b>{Number(record.strategy_score).toFixed(1)} 分</b></header>
        <small>冻结 {record.as_of} · 参考价 {record.reference_price ?? "--"} · 公式 {record.formula_version} · 生命周期 {(record.lifecycle ?? []).join(" → ") || "观察"}</small>
        <div className="quant-shadow-outcomes">
          {record.outcomes.map((outcome) => <div key={`${record.decision_id}-${outcome.horizon}`} data-status={outcome.status}>
            <span>{outcome.horizon}日</span>
            <strong>{outcome.status === "ready" ? percent(outcome.return_percent) : outcome.status === "pending" ? "待评估" : "不可用"}</strong>
            <small>{outcome.status === "ready" ? `MFE ${percent(outcome.mfe_percent)} · MAE ${percent(outcome.mae_percent)}` : outcome.limitation ?? "缺少未来真实日线"}</small>
          </div>)}
        </div>
      </article>)}
    </div>}
    {onJournalCreate && <section className="quant-decision-journal" aria-label="个人复盘日志">
      <header><div><NotebookPen size={16} /><h3>个人复盘日志</h3></div><small>只记录人工决策，不连接交易下单</small></header>
      <div className="quant-decision-journal-grid">
        <form onSubmit={(event) => { void submitJournal(event); }}>
          <label>当前股票<input value={journalSymbol ?? ""} readOnly aria-label="复盘股票" /></label>
          <label>复盘动作<select aria-label="复盘动作" value={journalAction} onChange={(event) => setJournalAction(event.target.value as DecisionJournalAction)}>{Object.entries(journalActionLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
          <div><label>实际价格<input inputMode="decimal" value={journalPrice} onChange={(event) => setJournalPrice(event.target.value)} placeholder="可选" /></label><label>数量<input inputMode="decimal" value={journalQuantity} onChange={(event) => setJournalQuantity(event.target.value)} placeholder="可选" /></label></div>
          <label>复盘备注<textarea aria-label="复盘备注" value={journalNote} onChange={(event) => setJournalNote(event.target.value)} placeholder="记录为什么观察、不交易、买入或卖出" /></label>
          <button type="submit" disabled={!journalSymbol || !journalNote.trim() || journalSaving}>{journalSaving ? "正在写入…" : "写入复盘日志"}</button>
          {(journalSaveError || journalError) && <p className="error" role="alert">{journalSaveError || journalError}</p>}
        </form>
        <div className="quant-decision-journal-records">
          {journalLoading && journalRecords.length === 0 && <p>正在读取当日复盘记录…</p>}
          {!journalLoading && journalRecords.length === 0 && <p>暂无人工复盘记录。</p>}
          {journalRecords.slice(0, 8).map((entry) => <article key={entry.entry_id}><header><b>{entry.symbol}</b><span>{journalActionLabels[entry.action]}</span></header><p>{entry.note}</p><small>{new Date(entry.recorded_at).toLocaleString("zh-CN", { hour12: false })}{entry.actual_price ? ` · 价格 ${entry.actual_price}` : ""}{entry.quantity ? ` · 数量 ${entry.quantity}` : ""}</small></article>)}
        </div>
      </div>
    </section>}
  </section>;
}
