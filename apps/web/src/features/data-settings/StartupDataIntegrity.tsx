import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { HistoryCoverageSummary, HistorySupplementJob } from "./types";
import { DATA_INTEGRITY_DIALOG_EVENT } from "../../shared/dataIntegrityDialog";
import "./startupIntegrity.css";
import { RepairProgressNumbers, repairActivityLabel } from "./RepairProgressNumbers";

type Props = {
  loadCoverage: () => Promise<HistoryCoverageSummary>;
  loadJob: () => Promise<HistorySupplementJob | null>;
  startRepair: () => Promise<HistorySupplementJob>;
};

const stages: Record<HistorySupplementJob["stage"], string> = {
  queued: "等待执行", checking_metadata: "检查修复来源", checking_cache: "检查缓存包",
  validating_cache: "校验缓存包", downloading: "下载官方日线包", validating: "校验下载内容",
  extracting: "解压日线包", scanning: "扫描本机日线", waiting_database: "等待数据库并自动重试",
  importing: "导入日线", online_repair: "通过在线及备用来源补齐", final_review: "复核数据覆盖",
  completed: "修复流程结束", partial: "仍有数据缺口", failed: "修复未完成",
};
const sources: Record<string, string> = { a_share_universe: "A 股证券目录", tdx_local: "本机通达信", tdx_official: "官方数据包", mootdx: "通达信在线", eltdx: "通达信 eltdx 连接池", baidu: "百度历史后备", eastmoney: "东方财富日线", tencent: "腾讯收盘日线" };
const reasons: Record<string, string> = {
  a_share_universe_unavailable: "尚未建立 A 股证券目录",
  daily_history_unavailable: "尚无可用的本地日线",
  dominant_date_coverage_below_98_percent: "最新交易日日线覆盖不足 98%",
  history_coverage_below_98_percent: "历史日线覆盖不足 98%",
  dominant_trade_date_behind_target: "日线日期落后于最近已完成的交易日",
};
function active(job: HistorySupplementJob | null): boolean { return job?.state === "pending" || job?.state === "running"; }
function complete(coverage: HistoryCoverageSummary | null): boolean {
  return Boolean(coverage && coverage.universe_count >= 4000 && coverage.quality === "ready"
    && coverage.dominant_trade_date === coverage.target_date
    && (coverage.coverage_percent ?? 0) >= 98 && (coverage.dominant_date_coverage_percent ?? 0) >= 98);
}
function message(error: unknown): string { return error instanceof Error ? error.message : "本地服务暂时不可用，请重试"; }
function percent(value: number | null | undefined): string { return value == null ? "未检测到" : `${value.toFixed(1)}%`; }

export function StartupDataIntegrity({ loadCoverage, loadJob, startRepair }: Props) {
  const [coverage, setCoverage] = useState<HistoryCoverageSummary | null>(null);
  const [job, setJob] = useState<HistorySupplementJob | null>(null);
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState("");
  const [now, setNow] = useState(Date.now);
  const mounted = useRef(false);
  const checkingRef = useRef(false);
  const startingRef = useRef(false);
  const startSequence = useRef(0);
  const previousJobId = useRef<string | null>(null);
  const panel = useRef<HTMLElement>(null);

  const check = useCallback(async (prompt = true) => {
    if (checkingRef.current) return;
    checkingRef.current = true;
    setChecking(true);
    const [coverageResult, jobResult] = await Promise.allSettled([Promise.resolve().then(loadCoverage), Promise.resolve().then(loadJob)]);
    checkingRef.current = false;
    if (!mounted.current) return;
    setChecking(false);
    setChecked(true);
    const nextCoverage = coverageResult.status === "fulfilled" ? coverageResult.value : null;
    setCoverage(nextCoverage);
    if (jobResult.status === "fulfilled") setJob(jobResult.value);
    setError(coverageResult.status === "rejected" ? `完整性检测未完成：${message(coverageResult.reason)}`
      : jobResult.status === "rejected" ? `修复状态读取失败：${message(jobResult.reason)}` : "");
    if (prompt && (!complete(nextCoverage) || (jobResult.status === "fulfilled"
      && (active(jobResult.value) || (jobResult.value?.remaining_gap_count ?? 0) > 0)))) setOpen(true);
  }, [loadCoverage, loadJob]);

  useEffect(() => {
    mounted.current = true;
    // Paint the workspace first. This local read never gates page rendering.
    const timer = window.setTimeout(() => { void check(); }, 600);
    return () => { mounted.current = false; window.clearTimeout(timer); };
  }, [check]);

  useEffect(() => {
    if (!active(job) && !busy) return;
    let disposed = false;
    let timer: number;
    const poll = async () => {
      try {
        const next = await loadJob();
        if (disposed || !mounted.current) return;
        if (!next) throw new Error("任务记录暂不可读，将自动重试");
        // A POST acknowledgement can be delayed after the worker has started.
        // Ignore the preceding terminal job while waiting for the new task.
        if (!busy || next.job_id !== previousJobId.current) {
          if (busy) {
            startSequence.current += 1;
            startingRef.current = false;
            setBusy(false);
          }
          setJob(next);
          setError("");
          if (!active(next)) { await check(false); return; }
        }
      } catch (reason) {
        if (disposed || !mounted.current) return;
        setError(`进度读取失败，将自动重试：${message(reason)}`);
      }
      if (!disposed) timer = window.setTimeout(() => { void poll(); }, 1500);
    };
    timer = window.setTimeout(() => { void poll(); }, 1200);
    return () => { disposed = true; window.clearTimeout(timer); };
  }, [job?.job_id, job?.state, busy, loadJob, check]);

  useEffect(() => {
    if (!active(job)) return;
    setNow(Date.now());
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [job?.job_id, job?.state]);

  useEffect(() => {
    window.dispatchEvent(new CustomEvent(DATA_INTEGRITY_DIALOG_EVENT, { detail: open }));
    if (!open) return;
    const previous = document.activeElement;
    panel.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => {
      window.dispatchEvent(new CustomEvent(DATA_INTEGRITY_DIALOG_EVENT, { detail: false }));
      if (previous instanceof HTMLElement && previous.isConnected) previous.focus();
    };
  }, [open]);

  async function start() {
    if (startingRef.current || active(job)) return;
    const sequence = ++startSequence.current;
    previousJobId.current = job?.job_id ?? null;
    startingRef.current = true;
    setBusy(true); setError("");
    try {
      const next = await startRepair();
      if (mounted.current && sequence === startSequence.current) {
        setJob(next);
        if (!active(next)) void check(false);
      }
    } catch (reason) {
      if (sequence !== startSequence.current) return;
      // Another page may already have started the shared repair job.
      try {
        const current = await loadJob();
        if (mounted.current && sequence === startSequence.current) {
          if (current && (active(current) || current.job_id !== previousJobId.current)) {
            setJob(current);
            if (!active(current)) void check(false);
          }
          else setError(`修复启动失败：${message(reason)}`);
        }
      } catch { if (mounted.current && sequence === startSequence.current) setError(`修复启动失败：${message(reason)}`); }
    } finally {
      if (sequence === startSequence.current) { startingRef.current = false; if (mounted.current) setBusy(false); }
    }
  }

  if (!checked) return null;
  const running = active(job);
  const ready = complete(coverage) && !(job && !running && job.remaining_gap_count > 0);
  if (!open) return !ready || running || error ? <button type="button" className="startup-integrity-reopen" onClick={() => setOpen(true)}>
    {running ? `数据补齐进行中 · ${repairActivityLabel(job!)}` : error ? "数据检测未完成 · 查看" : "数据存在缺口 · 查看修复"}
  </button> : null;

  const issues = coverage?.blockers.map((reason) => reasons[reason] ?? reason) ?? [];
  if (coverage && coverage.universe_count < 4000) issues.unshift("A 股证券目录数量不足，将先尝试补齐证券目录");
  const title = running ? "正在自动补齐数据" : ready ? "数据完整性复核通过" : coverage ? "检测到本地数据不完整" : "数据完整性检测未完成";
  const noticeError = error || job?.error_detail;
  const notice = noticeError || (!running && job?.result_detail) || "数量在每批写入成功后更新；数据是否补齐以最终覆盖复核为准。";
  return createPortal(<div className="startup-integrity-backdrop">
    <section ref={panel} className="startup-integrity-dialog" role="dialog" aria-modal="true" aria-labelledby="startup-integrity-title"
      onKeyDown={(event) => {
        if (event.key === "Escape") { event.stopPropagation(); setOpen(false); }
        if (event.key !== "Tab") return;
        const buttons = panel.current?.querySelectorAll<HTMLButtonElement>("button:not(:disabled)");
        if (!buttons?.length) return;
        const first = buttons[0]; const last = buttons[buttons.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }}>
      <header><div><small>启动数据检查</small><h2 id="startup-integrity-title">{title}</h2></div>
        <button type="button" onClick={() => setOpen(false)}>{running ? "后台继续" : "稍后处理"}</button></header>
      <div className="startup-integrity-body">
      <div className="startup-integrity-metrics">
        <div><span>应有交易日</span><b>{coverage?.target_date ?? "待检测"}</b></div>
        <div><span>本地主导日期</span><b>{coverage?.dominant_trade_date ?? "尚无日线"}</b></div>
        <div><span>当日日线覆盖</span><b>{percent(coverage?.dominant_date_coverage_percent)}</b></div>
        <div><span>历史日线覆盖</span><b>{percent(coverage?.coverage_percent)}</b></div>
      </div>
      <p className="startup-integrity-snapshot-note">检测快照 · 修复完成后自动复核覆盖率</p>
      {job && <div className="startup-integrity-job">
        <div className="startup-integrity-stage"><b>{stages[job.stage]}</b><span>{running ? "执行中" : "已结束"}</span></div>
        <RepairProgressNumbers job={job} />
      </div>}
      <p className="startup-integrity-notice" role={noticeError ? "alert" : undefined} title={notice} data-error={Boolean(noticeError)}>
        {notice}
      </p>
      <details className="startup-integrity-details">
        <summary>检测说明与修复详情</summary>
        <div className="startup-integrity-detail-scroll" tabIndex={0} aria-label="检测说明与修复日志">
        <p>检查 A 股证券目录、最近已完成交易日日线和历史覆盖。合格标准为日线覆盖均达到 98%；不代表新闻、财务或 AI 服务全部可用。</p>
        {!!coverage?.new_listing_complete_count && <p>已核实 {coverage.new_listing_complete_count} 只新股：上市日期及有效交易日历史已核实；停牌间隔需独立行情的日期和价格一致才能认可。它们计入历史完整覆盖，仍不具备 250 日量化分析资格。</p>}
        {!!coverage?.confirmed_suspended_count && <p>已交叉核实 {coverage.confirmed_suspended_count} 只目标日停牌股票：收盘状态与独立历史行情一致，无需生成当日日线；原始日线覆盖率保留真实数值。</p>}
        {!ready && issues.length > 0 && <ul className="startup-integrity-issues">{Array.from(new Set(issues)).map((reason) => <li key={reason}>{reason}</li>)}</ul>}
        {job && <>
        {job.result_detail && <p>{job.result_detail}</p>}
        <p aria-live="off">任务更新时间：{new Date(job.updated_at).toLocaleTimeString("zh-CN", { hour12: false })}
          {running && now - Date.parse(job.updated_at) >= 15000 ? ` · 已 ${Math.floor((now - Date.parse(job.updated_at)) / 1000)} 秒未收到新进度，正在继续查询；当前批次可能仍在处理。` : ""}</p>
        {job.error_detail && <p className="startup-integrity-error">{stages[job.error_stage as HistorySupplementJob["stage"]] ?? "失败原因"}：{job.error_detail}</p>}
        <ul className="startup-integrity-sources">{job.source_attempts.map((attempt) => <li key={attempt.source} data-state={attempt.state}>
          <b>{sources[attempt.source] ?? attempt.source}</b><span>{attempt.detail}</span>
        </li>)}</ul>
        </>}
        </div>
      </details>
      </div>
      <footer><small>点击后依次尝试本机日线、官方包、在线及后备来源；失败原因和剩余缺口会保留。</small>
        <div><button type="button" disabled={checking || busy || running} onClick={() => { void check(false); }}>{checking ? "检测中…" : "重新检测"}</button>
          {!ready && <button type="button" className="startup-integrity-primary" disabled={busy || running} onClick={() => { void start(); }}>
            {busy ? "正在启动…" : running ? "正在补齐数据" : "一键全面修复数据"}
          </button>}
          {ready && <button type="button" className="startup-integrity-primary" onClick={() => setOpen(false)}>进入工作台</button>}
        </div></footer>
    </section>
  </div>, document.body);
}
