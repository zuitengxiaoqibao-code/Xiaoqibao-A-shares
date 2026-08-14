import { AlertTriangle, ArchiveRestore, BarChart3, CheckCircle2, Clock3, Database, DatabaseBackup, Download, FolderOpen, Pause, Play, RotateCcw, ServerCog, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import type { BackupRecord, BackupVerification, CacheCleanupResult, CleanupPreview, OperationsDiagnostics, OperationsStatus, PerformanceSummary } from "./types";
import type { HistoryRepairAudit, HistoryRepairCenter, HistorySyncController, HistorySyncStarter, TdxImportController, TdxImportJob, TdxImportScanner, TdxImportStarter, TdxImportLoader, TdxImportScan } from "../data-settings/types";
import { readCoalescedFetchStats } from "../../shared/coalescedFetch";
import { blockerLabel } from "../../shared/evidence/freshnessCopy";

type Props = {
  loadStatus: () => Promise<OperationsStatus>;
  setSchedulerPaused: (paused: boolean) => Promise<OperationsStatus["scheduler"]>;
  createBackup: () => Promise<BackupRecord>;
  verifyBackup: (backupId: string) => Promise<BackupVerification>;
  runManualJob: (phase: string, tradingDate: string) => Promise<{ report_id: string }>;
  cleanupCache?: (olderThanHours: number) => Promise<CacheCleanupResult>;
  previewCleanup?: (olderThanHours: number) => Promise<CleanupPreview>;
  cleanupStorage?: (olderThanHours: number) => Promise<CacheCleanupResult>;
  loadPerformance?: () => Promise<PerformanceSummary>;
  loadDiagnostics?: () => Promise<OperationsDiagnostics>;
  loadHistoryRepairCenter?: () => Promise<HistoryRepairCenter>;
  loadHistoryRepairAudits?: () => Promise<HistoryRepairAudit[]>;
  startHistoryBackfill?: HistorySyncStarter;
  pauseHistorySync?: HistorySyncController;
  resumeHistorySync?: HistorySyncController;
  loadTdxImport?: TdxImportLoader;
  scanTdxImport?: TdxImportScanner;
  startTdxImport?: TdxImportStarter;
  pauseTdxImport?: TdxImportController;
  resumeTdxImport?: TdxImportController;
};

const phaseName = { premarket: "盘前", intraday: "盘中", postclose: "盘后" };
const snapshotName: Record<string, string> = {
  market_cross_section: "市场横截面",
  limit_events: "涨跌停事件",
  sector_strength: "板块强度",
  stock_fund_flow: "个股资金",
  news_events: "新闻事件",
  financial_valuation: "财务估值",
  quant_factors: "量化因子",
};
const schedule = [["09:20", "盘前情报"], ["10:30", "盘中一检"], ["13:30", "盘中二检"], ["14:30", "盘中三检"], ["15:30", "盘后复盘"]];
const bytes = (value: number) => value >= 1048576 ? `${(value / 1048576).toFixed(2)} MB` : `${(value / 1024).toFixed(1)} KB`;
const autoImportStateLabel: Record<string, string> = { disabled: "未启用", idle: "等待首次扫描", baseline: "已建立目录基线", unchanged: "等待目录变化", submitted: "已提交增量导入", skipped_active: "已有任务运行", error: "监测失败" };

export function OperationsView(props: Props) {
  const [status, setStatus] = useState<OperationsStatus | null>(null);
  const [error, setError] = useState("");
  const [acting, setActing] = useState("");
  const [tradingDate, setTradingDate] = useState(new Date().toISOString().slice(0, 10));
  const [verification, setVerification] = useState<BackupVerification | null>(null);
  const [notice, setNotice] = useState("");
  const [history, setHistory] = useState<HistoryRepairCenter | null>(null);
  const [historyError, setHistoryError] = useState("");
  const [historyBusy, setHistoryBusy] = useState(false);
  const [historyAudits, setHistoryAudits] = useState<HistoryRepairAudit[] | null>(null);
  const [historyAuditError, setHistoryAuditError] = useState("");
  const [cleanupPreview, setCleanupPreview] = useState<CleanupPreview | null>(null);
  const [performance, setPerformance] = useState<PerformanceSummary | null>(null);
  const [tdxImport, setTdxImport] = useState<TdxImportJob | null>(null);
  const [tdxScan, setTdxScan] = useState<TdxImportScan | null>(null);
  const [tdxBusy, setTdxBusy] = useState(false);
  const [tdxError, setTdxError] = useState("");
  const [diagnostics, setDiagnostics] = useState<OperationsDiagnostics | null>(null);
  const requestStats = readCoalescedFetchStats();

  async function reload() { setError(""); try { setStatus(await props.loadStatus()); } catch (reason) { setError(reason instanceof Error ? reason.message : "运维状态读取失败"); } }
  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const next = await props.loadStatus();
        if (active) {
          setStatus(next);
          setError("");
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "运维状态读取失败");
      }
    };
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => { active = false; window.clearInterval(timer); };
  }, [props.loadStatus]);
  useEffect(() => { if (props.loadPerformance) void props.loadPerformance().then(setPerformance).catch(() => undefined); }, [props.loadPerformance]);
  useEffect(() => { if (props.loadDiagnostics) void props.loadDiagnostics().then(setDiagnostics).catch(() => undefined); }, [props.loadDiagnostics]);
  useEffect(() => {
    if (!props.loadTdxImport) return;
    let active = true;
    const poll = () => props.loadTdxImport!().then((value) => { if (active) setTdxImport(value); }).catch((reason) => { if (active) setTdxError(reason instanceof Error ? reason.message : "本地导入状态读取失败"); });
    void poll();
    const timer = window.setInterval(() => void poll(), 1200);
    return () => { active = false; window.clearInterval(timer); };
  }, [props.loadTdxImport]);
  useEffect(() => {
    if (!props.loadHistoryRepairCenter) return;
    let active = true;
    props.loadHistoryRepairCenter().then((value) => {
      if (active) setHistory(value);
    }).catch((reason) => {
      if (active) setHistoryError(reason instanceof Error ? reason.message : "日线修复中心读取失败");
    });
    return () => { active = false; };
  }, [props.loadHistoryRepairCenter]);
  useEffect(() => {
    if (!props.loadHistoryRepairAudits) return;
    props.loadHistoryRepairAudits().then(setHistoryAudits).catch((reason) => setHistoryAuditError(reason instanceof Error ? reason.message : "日线修复审计读取失败"));
  }, [props.loadHistoryRepairAudits]);
  async function toggleScheduler() { if (!status) return; const paused = !status.scheduler.paused; setActing("scheduler"); setError(""); try { const scheduler = await props.setSchedulerPaused(paused); setStatus({ ...status, scheduler }); setNotice(paused ? "调度已暂停" : "调度已恢复"); } catch (reason) { setError(reason instanceof Error ? reason.message : "调度操作失败"); } finally { setActing(""); } }
  async function backup() { if (!status) return; setActing("backup"); setError(""); try { const created = await props.createBackup(); setStatus({ ...status, backups: [created, ...status.backups] }); setNotice(`备份已创建 ${created.backup_id}`); } catch (reason) { setError(reason instanceof Error ? reason.message : "备份创建失败"); } finally { setActing(""); } }
  async function verify(backupId: string) { setActing(`verify:${backupId}`); setError(""); try { setVerification(await props.verifyBackup(backupId)); } catch (reason) { setError(reason instanceof Error ? reason.message : "备份验证失败"); } finally { setActing(""); } }
  async function manual(phase: "premarket" | "intraday" | "postclose") { setActing(`manual:${phase}`); setError(""); try { const result = await props.runManualJob(phase, tradingDate); setNotice(`补跑已归档 ${result.report_id}`); await reload(); } catch (reason) { setError(reason instanceof Error ? reason.message : "手动补跑失败"); } finally { setActing(""); } }
  async function cleanCache() { if (!props.cleanupCache) return; setActing("cache"); setError(""); try { const result = await props.cleanupCache(72); setNotice(`已清理 ${result.removed_count} 个缓存文件`); setStatus(await props.loadStatus()); } catch (reason) { setError(reason instanceof Error ? reason.message : "缓存清理失败"); } finally { setActing(""); } }
  async function previewClean() { if (!props.previewCleanup) return; setActing("preview-cleanup"); setError(""); try { setCleanupPreview(await props.previewCleanup(72)); } catch (reason) { setError(reason instanceof Error ? reason.message : "清理范围预览失败"); } finally { setActing(""); } }
  async function confirmClean() { if (!props.cleanupStorage) return; setActing("storage-cleanup"); setError(""); try { const result = await props.cleanupStorage(72); setNotice(`已安全清理 ${result.removed_count} 个可重建文件，释放 ${bytes(result.removed_bytes)}`); setCleanupPreview(null); setStatus(await props.loadStatus()); } catch (reason) { setError(reason instanceof Error ? reason.message : "存储清理失败"); } finally { setActing(""); } }
  async function refreshHistory() { if (!props.loadHistoryRepairCenter) return; setHistoryBusy(true); setHistoryError(""); setHistoryAuditError(""); try { setHistory(await props.loadHistoryRepairCenter()); if (props.loadHistoryRepairAudits) setHistoryAudits(await props.loadHistoryRepairAudits()); } catch (reason) { setHistoryError(reason instanceof Error ? reason.message : "日线修复中心读取失败"); } finally { setHistoryBusy(false); } }
  async function controlHistory(action: "start" | "pause" | "resume") {
    setHistoryBusy(true); setHistoryError("");
    try {
      if (action === "start" && props.startHistoryBackfill) await props.startHistoryBackfill();
      if (action === "pause" && props.pauseHistorySync && history?.current_job) await props.pauseHistorySync(history.current_job.job_id);
      if (action === "resume" && props.resumeHistorySync && history?.current_job) await props.resumeHistorySync(history.current_job.job_id);
      await refreshHistory();
    } catch (reason) { setHistoryError(reason instanceof Error ? reason.message : "日线修复任务操作失败"); } finally { setHistoryBusy(false); }
  }
  async function scanTdx() { if (!props.scanTdxImport) return; setTdxBusy(true); setTdxError(""); try { setTdxScan(await props.scanTdxImport()); } catch (reason) { setTdxError(reason instanceof Error ? reason.message : "本地通达信扫描失败"); } finally { setTdxBusy(false); } }
  async function startTdx() { if (!props.startTdxImport) return; setTdxBusy(true); setTdxError(""); try { setTdxImport(await props.startTdxImport()); } catch (reason) { setTdxError(reason instanceof Error ? reason.message : "本地通达信导入失败"); } finally { setTdxBusy(false); } }
  async function controlTdx(action: "pause" | "resume") { if (!tdxImport) return; const handler = action === "pause" ? props.pauseTdxImport : props.resumeTdxImport; if (!handler) return; setTdxBusy(true); setTdxError(""); try { setTdxImport(await handler(tdxImport.job_id)); } catch (reason) { setTdxError(reason instanceof Error ? reason.message : "本地通达信导入任务操作失败"); } finally { setTdxBusy(false); } }
  function exportDiagnostics() {
    if (!diagnostics) return;
    const payload = JSON.stringify({
      exported_at: new Date().toISOString(),
      diagnostics,
      note: "仅包含运行状态汇总，不包含密钥、令牌、密码或原始行情数据。",
    }, null, 2);
    const url = URL.createObjectURL(new Blob([payload], { type: "application/json;charset=utf-8" }));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `yishu-operations-diagnostics-${new Date().toISOString().replace(/[:.]/g, "-")}.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    setNotice("诊断摘要已导出，未包含敏感凭据");
  }

  if (!status && !error) return <main className="terminal-page operations-domain"><div className="operations-loading" role="status" aria-busy="true"><Clock3 size={18}/>正在读取运维状态...</div></main>;
  return <main className="terminal-page operations-domain">
    <header className="operations-header"><div><p className="eyebrow">工部 / DATA OPERATIONS</p><h1>数据与运维中心</h1><p>本地任务调度、故障补跑、一致性备份与恢复验证</p></div><div className={`scheduler-switch ${status?.scheduler.paused ? "paused" : "running"}`}><span>{status?.scheduler.paused ? "PAUSED" : "RUNNING"}</span><button onClick={() => void toggleScheduler()} disabled={acting !== ""}>{status?.scheduler.paused ? <Play size={15}/> : <Pause size={15}/>} {status?.scheduler.paused ? "恢复调度" : "暂停调度"}</button></div></header>
    {error && <div className="operations-error" role="alert"><AlertTriangle size={17}/>{error}<button onClick={() => void reload()}>重试</button></div>}
    {notice && <div className="operations-notice" role="status"><CheckCircle2 size={16}/>{notice}</div>}
    {status?.tdx_auto_import && <section className={`tdx-auto-import-status ${status.tdx_auto_import.state}`} aria-label="通达信自动导入状态">
      <div><Database size={16}/><strong>通达信日线自动监测</strong><span>{autoImportStateLabel[status.tdx_auto_import.state] ?? status.tdx_auto_import.state}</span></div>
      <small>{status.tdx_auto_import.file_count} 个受监测文件{status.tdx_auto_import.last_poll_at ? ` · 最近扫描 ${new Date(status.tdx_auto_import.last_poll_at).toLocaleTimeString("zh-CN")}` : ""}</small>
      {status.tdx_auto_import.state === "skipped_active" && <small>已有导入任务运行中，目录变化将在当前任务结束后再次检查</small>}
      {status.tdx_auto_import.state === "error" && <small>{status.tdx_auto_import.error ?? "未返回具体原因"}</small>}
    </section>}
    {diagnostics && <details className="inventory-console operations-diagnostics"><summary><ServerCog size={16}/>运行诊断摘要 · 默认折叠</summary><div className="directory-inventory"><article><Database size={17}/><div><b>数据源健康</b><small>就绪 {diagnostics.source_health.ready} · 降级 {diagnostics.source_health.degraded} · 不可用 {diagnostics.source_health.unavailable}</small></div></article><article><DatabaseBackup size={17}/><div><b>本地备份</b><small>{diagnostics.backup_count} 份 · 持久数据 {bytes(diagnostics.persistent_bytes)} · 可重建缓存 {bytes(diagnostics.rebuildable_bytes)}</small></div></article><article><ServerCog size={17}/><div><b>自动导入</b><small>{autoImportStateLabel[diagnostics.tdx_auto_import.state] ?? diagnostics.tdx_auto_import.state} · 监测文件 {diagnostics.tdx_auto_import.file_count}</small></div></article><article><AlertTriangle size={17}/><div><b>来源冲突</b><small>{diagnostics.source_conflicts?.state === "ready" ? `${diagnostics.source_conflicts.conflict_count} 个字段冲突，点击展开核验` : "冲突摘要暂不可用"}</small></div></article></div>{diagnostics.source_conflicts?.state === "ready" && diagnostics.source_conflicts.conflict_count > 0 && <div className="source-conflict-list">{diagnostics.source_conflicts.conflicts.slice(0, 12).map((conflict) => <article key={`${conflict.symbol}:${conflict.field}:${conflict.as_of}`}><div><b>{conflict.symbol} · {conflict.field}</b><small>{conflict.as_of} · 采用 {conflict.selected_source} · {conflict.selection_reason}</small></div><div className="source-conflict-candidates">{conflict.candidates.map((candidate) => <span key={`${candidate.source}:${candidate.value}`} title={candidate.evidence_link}>{candidate.source}: {candidate.value}</span>)}</div></article>)}</div>}<button className="diagnostics-export" onClick={exportDiagnostics}><Download size={14}/>导出诊断摘要</button></details>}
    {(props.loadTdxImport || props.scanTdxImport || props.startTdxImport) && <section className="history-repair-console tdx-import-console">
      <header><div><h2><Database size={17}/>本地通达信日线导入</h2><small>读取 vipdoc / 日线压缩包 · 本地数据优先 · 不控制通达信进程</small></div><div><button onClick={() => void scanTdx()} disabled={tdxBusy || !props.scanTdxImport}><RotateCcw size={14}/>扫描本地数据</button><button onClick={() => void startTdx()} disabled={tdxBusy || !props.startTdxImport}>导入本地增量</button>{tdxImport?.state === "running" && <button onClick={() => void controlTdx("pause")} disabled={tdxBusy || !props.pauseTdxImport}><Pause size={14}/>暂停</button>}{tdxImport?.state === "paused" && <button onClick={() => void controlTdx("resume")} disabled={tdxBusy || !props.resumeTdxImport}><Play size={14}/>继续</button>}</div></header>
      {tdxScan && <p className="history-repair-loading" role="status">发现 {tdxScan.day_files} 个日线文件 · 可读取 {tdxScan.readable_files} 个 · 最新 {tdxScan.latest_trade_date ?? "--"}</p>}
      {tdxImport && <div className="history-job-progress" role="status"><div><b>{tdxImport.stage} · {tdxImport.percent.toFixed(2)}%</b><small>{tdxImport.processed_files}/{tdxImport.total_files} 文件 · 新增 {tdxImport.imported_rows} · 替换 {tdxImport.replaced_rows} · 跳过 {tdxImport.skipped_rows} · 失败 {tdxImport.failed_files}</small></div><progress max={100} value={tdxImport.percent}/></div>}
      {tdxError && <p className="history-repair-error"><AlertTriangle size={15}/>{tdxError}</p>}
    </section>}
    {props.loadHistoryRepairCenter && <section className="history-repair-console">
      <header><div><h2><BarChart3 size={17}/>全市场日线修复中心</h2><small>本地去重日线 · 主导交易日覆盖达到 98% 才标记就绪</small></div><div><button onClick={() => void refreshHistory()} disabled={historyBusy}><RotateCcw size={14}/>{historyBusy ? "读取中" : "刷新状态"}</button>{!history?.current_job && props.startHistoryBackfill && <button onClick={() => void controlHistory("start")} disabled={historyBusy}>开始修复</button>}{history?.current_job?.state === "running" && props.pauseHistorySync && <button onClick={() => void controlHistory("pause")} disabled={historyBusy}><Pause size={14}/>暂停</button>}{history?.current_job?.state === "paused" && props.resumeHistorySync && <button onClick={() => void controlHistory("resume")} disabled={historyBusy}><Play size={14}/>继续</button>}</div></header>
      {historyError && <p className="history-repair-error"><AlertTriangle size={15}/>{historyError}</p>}
      {!history && !historyError ? <p className="history-repair-loading" role="status"><Clock3 size={15}/>正在读取本地日线水位...</p> : history && <>
        <div className="history-watermark">
          <article className={history.coverage.quality}><span>数据状态</span><strong>{history.coverage.quality === "ready" ? "就绪" : history.coverage.quality === "partial" ? "待修复" : "不可用"}</strong><small>{history.coverage.blockers.length ? `${history.coverage.blockers.length} 个阻断项` : "无阻断项"}</small></article>
          <article><span>主导交易日</span><strong>{history.coverage.dominant_trade_date ?? "--"}</strong><small>覆盖 {history.coverage.dominant_date_coverage_percent ?? "--"}%</small></article>
          <article><span>策略可用</span><strong>{history.coverage.eligible_count} / {history.coverage.universe_count}</strong><small>覆盖 {history.coverage.coverage_percent ?? "--"}%</small></article>
          <article><span>待修复</span><strong>{history.total_gap_count}</strong><small>无历史 / 不足 / 日期落后</small></article>
        </div>
        {history.current_job && <div className="history-job-progress"><div><b>{history.current_job.mode === "backfill" ? "全量回填" : "增量修复"} · {history.current_job.state}</b><small>{history.current_job.ready_count + history.current_job.skipped_count} / {history.current_job.total_count} 已处理 · 失败 {history.current_job.failed_count}</small></div><progress max={Math.max(1, history.current_job.total_count)} value={history.current_job.ready_count + history.current_job.skipped_count}/></div>}
        {history.coverage.blockers.length > 0 && <div className="history-blocker-list" role="status">{history.coverage.blockers.map((item) => <span key={item}><AlertTriangle size={13}/>{blockerLabel(item)}</span>)}</div>}
        <div className="history-gap-list">{history.gaps.slice(0, 12).map((item) => <article key={item.symbol}><b>{item.symbol}</b><span>{item.gap_kind === "missing_history" ? "无历史" : item.gap_kind === "insufficient_history" ? "历史不足" : "日期落后"}</span><small>{item.bar_count} 根 · {item.latest_trade_date ?? "无日期"}</small></article>)}</div>
        {(props.loadHistoryRepairAudits || historyAudits) && <details className="history-audit-details"><summary>修复审计 · {historyAudits?.length ?? 0} 条最近记录</summary>{historyAuditError && <p className="history-repair-error">{historyAuditError}</p>}{!historyAudits?.length && !historyAuditError ? <p className="history-repair-loading">暂无已完成修复审计</p> : <div className="history-audit-list">{historyAudits?.map((audit) => <article key={audit.audit_id}><div><b>{audit.target_date} · {audit.mode === "backfill" ? "全量回填" : "增量修复"}</b><small>{new Date(audit.completed_at).toLocaleString("zh-CN")} · {audit.source}</small></div><div><span>缺口 {audit.gap_count_before}</span><span>写入 {audit.written_rows} 行</span><span>覆盖 {audit.coverage_before_percent ?? "--"}% → {audit.coverage_after_percent ?? "--"}%</span></div><div><span>成功 {audit.ready_count}</span><span>跳过 {audit.skipped_count}</span><span className={audit.failed_count ? "audit-failed" : ""}>失败 {audit.failed_count}</span></div>{audit.failure_reasons.length > 0 && <small className="audit-failed">原因：{audit.failure_reasons.join("；")}</small>}</article>)}</div>}</details>}
      </>}
    </section>}
    <section className="schedule-console"><header><ServerCog size={17}/><div><h2>尚书省自动调度</h2><small>交易日 · 北京时间 · 失败最多尝试 3 次</small></div></header><div className="schedule-track">{schedule.map(([time, label]) => <div key={time}><time>{time}</time><span>{label}</span></div>)}</div></section>
    <section className="manual-console"><div><h2>故障补跑</h2><small>暂停状态下仍可执行，结果进入追加式任务日志</small></div><label>补跑交易日<input aria-label="补跑交易日" type="date" value={tradingDate} onChange={(event) => setTradingDate(event.target.value)}/></label><div>{(["premarket", "intraday", "postclose"] as const).map((phase) => <button key={phase} disabled={acting !== "" || !tradingDate} onClick={() => void manual(phase)}><RotateCcw size={14}/>补跑{phaseName[phase]}</button>)}</div></section>
    <section className="inventory-console">
      <header><div><h2>本地目录与数据库</h2><small>仅统计便携版持久目录，不扫描或控制通达信</small></div><button onClick={() => props.previewCleanup ? void previewClean() : void cleanCache()} disabled={acting !== "" || (!props.previewCleanup && !props.cleanupCache)}><Trash2 size={15}/>{acting === "preview-cleanup" ? "正在预览" : acting === "cache" ? "正在清理" : props.previewCleanup ? "预览可清理空间" : "清理72小时前缓存"}</button></header>
      {cleanupPreview && <div className="operations-notice" role="status"><Database size={16}/><span>预计清理 {cleanupPreview.candidate_count} 个可重建文件 · {bytes(cleanupPreview.candidate_bytes)} · {Object.entries(cleanupPreview.categories).map(([name, count]) => `${name} ${count}`).join(" / ") || "无候选"}</span>{cleanupPreview.candidate_count > 0 && <button onClick={() => void confirmClean()} disabled={acting !== "storage-cleanup" && acting !== ""}>{acting === "storage-cleanup" ? "正在清理" : "确认清理"}</button>}</div>}
      {!status?.inventory ? <p className="operations-empty">目录清单暂不可用</p> : <>
        {status.inventory.release && <div className="operations-notice"><Database size={16}/><span>程序 {bytes(status.inventory.release.program_bytes)} · 持久数据 {bytes(status.inventory.release.persistent_bytes)}<small>只允许清理 {status.inventory.release.rebuildable_directories.join("、")}；配置、行情、新闻、模型、研究与备份受保护</small></span></div>}
        <div className="directory-inventory">{Object.entries(status.inventory.directories).map(([name, item]) => <article key={name}><FolderOpen size={17}/><div><b>{name}/</b><small>{item.exists ? `${item.file_count} 个文件 · ${bytes(item.bytes)}${item.truncated ? " · 已达扫描上限" : ""}` : "目录尚未建立"}</small></div></article>)}</div>
        <div className="database-inventory">{Object.entries(status.inventory.databases).length === 0 ? <p className="operations-empty">未发现本地数据库文件</p> : Object.entries(status.inventory.databases).map(([name, item]) => <article key={name}><Database size={17}/><div><b>{name}</b><small>{bytes(item.bytes)} · 更新于 {new Date(item.modified_at).toLocaleString("zh-CN")}</small></div></article>)}</div>
      </>}
    </section>
    {performance && <details className="inventory-console performance-console"><summary><BarChart3 size={16}/>页面与接口性能 · 默认折叠</summary><div className="directory-inventory"><article><BarChart3 size={17}/><div><b>本次会话请求合并</b><small>调用 {requestStats.callers} · 实际网络 {requestStats.networkRequests} · 已合并 {requestStats.coalescedCallers} · 活动 {requestStats.activeRequests}</small></div></article>{performance.metrics.slice().sort((a, b) => b.p95_ms - a.p95_ms).slice(0, 11).map((metric) => <article key={`${metric.kind}:${metric.name}`}><BarChart3 size={17}/><div><b>{metric.name}</b><small>P50 {metric.p50_ms}ms · P95 {metric.p95_ms}ms · 失败 {metric.failure_rate}%{metric.cache_hit_rate === null ? "" : ` · 缓存命中 ${metric.cache_hit_rate}%`}</small></div></article>)}</div><div className="directory-inventory">{performance.snapshots.slice().sort((a, b) => b.slowest_compute_ms - a.slowest_compute_ms).map((snapshot) => <article key={snapshot.kind}><Database size={17}/><div><b>{snapshotName[snapshot.kind] ?? snapshot.kind}</b><small>v{snapshot.snapshot_version}{snapshot.trade_date ? ` · ${snapshot.trade_date}` : ""} · 计算 {snapshot.compute_count} · 复用 {snapshot.reuse_count} · 重复计算 {snapshot.duplicate_compute_count}{snapshot.cache_hit_rate === null ? "" : ` · 命中 ${snapshot.cache_hit_rate}%`} · 最慢 {snapshot.slowest_compute_ms}ms</small></div></article>)}</div></details>}
    <section className="job-ledger"><header><h2>任务运行账本</h2><small>{status?.scheduler.jobs.length ?? 0} 个调度槽位</small></header>{status?.scheduler.jobs.length === 0 ? <p className="operations-empty">暂无任务运行记录</p> : status?.scheduler.jobs.slice().reverse().map((job) => <article key={job.job_key}><span className={`job-state ${job.status}`}/><div><b>{phaseName[job.phase]} · {job.trading_date} · {job.slot}</b><small>{job.trigger === "manual" ? "手动补跑" : "自动调度"} · {new Date(job.occurred_at).toLocaleString("zh-CN")}</small></div><div><strong>{job.status === "completed" ? "已完成" : job.error_code}</strong><small>累计尝试 {job.attempts} 次</small></div></article>)}</section>
    <section className="backup-console"><header><div><h2>本地备份与恢复验证</h2><small>SQLite 在线快照 · DuckDB checkpoint · SHA-256 清单</small></div><button onClick={() => void backup()} disabled={acting !== ""}><DatabaseBackup size={15}/>创建一致性备份</button></header>{verification && <div className={`verification-result ${verification.valid && verification.restore_drill_passed ? "passed" : "failed"}`}>{verification.valid && verification.restore_drill_passed ? <CheckCircle2/> : <AlertTriangle/>}<div><b>{verification.restore_drill_passed ? "恢复演练通过" : "恢复演练失败"}</b><small>校验 {verification.checked_files} 个文件{verification.mismatched_files.length ? ` · 异常 ${verification.mismatched_files.join(", ")}` : " · 哈希一致"}</small></div></div>}<div className="backup-ledger">{status?.backups.length === 0 ? <p className="operations-empty">尚未创建本地备份</p> : status?.backups.map((item) => <article key={item.backup_id}><ArchiveRestore size={17}/><div><b>{item.backup_id}</b><small>{new Date(item.created_at).toLocaleString("zh-CN")} · {item.file_count} 文件 · {bytes(item.total_bytes)}</small></div><button aria-label="执行恢复演练" disabled={acting !== ""} onClick={() => void verify(item.backup_id)}>{acting === `verify:${item.backup_id}` ? "演练中" : "执行恢复演练"}</button></article>)}</div></section>
  </main>;
}
