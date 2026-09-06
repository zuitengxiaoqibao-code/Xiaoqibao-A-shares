import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { OperationsView } from "./OperationsView";
import type { OperationsStatus } from "./types";


const status: OperationsStatus = {
  scheduler: {
    paused: false,
    jobs: [
      { job_key: "2026-07-14:premarket:0920", phase: "premarket", trading_date: "2026-07-14", slot: "0920", trigger: "scheduled", attempt: 2, attempts: 2, status: "completed", occurred_at: "2026-07-14T01:20:00Z", report_id: "report-1", error_code: null },
      { job_key: "2026-07-14:intraday:1030", phase: "intraday", trading_date: "2026-07-14", slot: "1030", trigger: "scheduled", attempt: 3, attempts: 3, status: "failed", occurred_at: "2026-07-14T02:30:00Z", report_id: null, error_code: "runtime_error" },
    ],
  },
  backups: [
    { backup_id: "backup-20260714", created_at: "2026-07-14T08:00:00Z", file_count: 8, total_bytes: 1048576 },
  ],
  inventory: {
    generated_at: "2026-07-14T08:00:00Z",
    directories: {
      data: { exists: true, file_count: 9, bytes: 3145728, truncated: false },
      cache: { exists: true, file_count: 4, bytes: 1024, truncated: false },
    },
    databases: { "data/market.duckdb": { bytes: 2097152, modified_at: "2026-07-14T07:59:00Z" } },
    scan_limit: 5000,
    release: { generated_at: "2026-07-14T08:00:00Z", total_bytes: 7340032, program_bytes: 3145728, persistent_bytes: 4194304, rebuildable_bytes: 1024, protected_directories: ["backups", "config", "data", "exports", "models", "news"], rebuildable_directories: ["cache", "logs"] },
  },
  tdx_auto_import: { state: "baseline", last_poll_at: "2026-07-14T08:00:00Z", last_change_at: null, last_submitted_at: null, submitted_job_id: null, skip_reason: null, error: null, file_count: 12 },
};


describe("OperationsView", () => {
  it("uses the shared terminal page shell", async () => {
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} />);

    expect(await screen.findByRole("heading", { name: "数据与运维中心" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveClass("terminal-page", "operations-domain");
    expect(screen.getByRole("region", { name: "通达信自动导入状态" })).toHaveTextContent("已建立目录基线");
  });

  it("places the three daily-bar operations above the TDX daily monitor", async () => {
    render(<OperationsView
      loadStatus={() => Promise.resolve(status)}
      setSchedulerPaused={() => Promise.resolve(status.scheduler)}
      createBackup={() => Promise.resolve(status.backups[0])}
      verifyBackup={() => Promise.reject(new Error("unused"))}
      runManualJob={() => Promise.resolve({ report_id: "report-manual" })}
      scanTdxImport={() => Promise.resolve({ scanned_paths: [], day_files: 0, archive_files: 0, readable_files: 0, latest_trade_date: null, errors: [] })}
      loadHistoryRepairCenter={() => Promise.resolve({
        coverage: {
          target_date: "2026-08-26", universe_count: 0, backfill_complete_count: 0,
          eligible_count: 0, target_date_count: 0, target_date_coverage_percent: 0,
          dominant_trade_date: null, dominant_date_count: 0, dominant_date_coverage_percent: 0,
          coverage_percent: 0, fragmented_latest_count: 0, missing_history_count: 0,
          quality: "unavailable", blockers: [],
        },
        current_job: null, total_gap_count: 0, offset: 0, limit: 100, gaps: [],
      })}
    />);

    const localImport = await screen.findByRole("heading", { name: "本地通达信日线导入" });
    const repairCenter = screen.getByRole("heading", { name: "全市场日线修复中心" });
    const manualRecovery = screen.getByRole("heading", { name: "故障补跑" });
    const dailyMonitor = screen.getByText("通达信日线自动监测");

    expect(localImport.compareDocumentPosition(repairCenter) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(repairCenter.compareDocumentPosition(manualRecovery) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(manualRecovery.compareDocumentPosition(dailyMonitor) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("shows scheduler failures and verifies a backup with restore drill", async () => {
    const verifyBackup = vi.fn(() => Promise.resolve({ backup_id: "backup-20260714", valid: true, restore_drill_passed: true, checked_files: 8, mismatched_files: [] }));
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={verifyBackup} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} />);

    expect(await screen.findByRole("heading", { name: "数据与运维中心" })).toBeInTheDocument();
    const taskDetails = screen.getByText("任务运行脚本").closest("details");
    expect(taskDetails).not.toHaveAttribute("open");
    fireEvent.click(screen.getByText("任务运行脚本"));
    expect(screen.getByText("运行错误")).toBeVisible();
    expect(screen.getByText("累计尝试 3 次")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "执行恢复演练" }));
    expect(await screen.findByText("恢复演练通过")).toBeInTheDocument();
    expect(verifyBackup).toHaveBeenCalledWith("backup-20260714");
  });

  it("pauses scheduler and supports manual postclose recovery", async () => {
    const setSchedulerPaused = vi.fn(() => Promise.resolve({ ...status.scheduler, paused: true }));
    const runManualJob = vi.fn(() => Promise.resolve({ report_id: "report-manual" }));
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={setSchedulerPaused} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={runManualJob} />);
    await screen.findByRole("heading", { name: "数据与运维中心" });

    fireEvent.click(screen.getByRole("button", { name: "暂停调度" }));
    expect(await screen.findByText("调度已暂停")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("补跑交易日"), { target: { value: "2026-07-14" } });
    fireEvent.click(screen.getByRole("button", { name: "补跑盘后" }));
    expect(await screen.findByText("补跑已归档 report-manual")).toBeInTheDocument();
    expect(runManualJob).toHaveBeenCalledWith("postclose", "2026-07-14");
  });

  it("shows local inventory and cleans cache without touching persistent data", async () => {
    const cleanupCache = vi.fn(() => Promise.resolve({ removed_count: 4, removed_bytes: 1024 }));
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} cleanupCache={cleanupCache} />);

    expect(await screen.findByRole("heading", { name: "本地目录与数据库" })).toBeInTheDocument();
    const inventoryDetails = screen.getByRole("heading", { name: "本地目录与数据库" }).closest("details");
    expect(inventoryDetails).toHaveAttribute("open");
    expect(inventoryDetails).toHaveClass("operations-collapsible");
    expect(screen.getByText("data/market.duckdb")).toBeVisible();
    expect(screen.getByText("程序 3.00 MB · 持久数据 4.00 MB")).toBeVisible();
    expect(screen.getByText(/只允许清理 cache、logs/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "清理72小时前缓存" }));
    expect(await screen.findByText("已清理 4 个缓存文件")).toBeInTheDocument();
    expect(cleanupCache).toHaveBeenCalledWith(72);
  });

  it("refreshes the automatic import status without clearing the existing view", async () => {
    vi.useFakeTimers();
    const nextStatus = { ...status, tdx_auto_import: { ...status.tdx_auto_import!, state: "submitted" as const, submitted_job_id: "auto-job" } };
    const loadStatus = vi.fn()
      .mockResolvedValueOnce(status)
      .mockResolvedValueOnce(nextStatus);
    try {
      render(<OperationsView loadStatus={loadStatus} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} />);
      await vi.waitFor(() => expect(loadStatus).toHaveBeenCalledTimes(1));
      await vi.advanceTimersByTimeAsync(5000);
      await vi.waitFor(() => expect(screen.getByRole("region", { name: "通达信自动导入状态" })).toHaveTextContent("已提交增量导入"));
      expect(screen.getByText("数据与运维中心")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });

  it("previews rebuildable storage and keeps performance expanded by default", async () => {
    const previewCleanup = vi.fn(() => Promise.resolve({ candidate_count: 3, candidate_bytes: 4096, categories: { cache: 2, logs: 1 } }));
    const cleanupStorage = vi.fn(() => Promise.resolve({ removed_count: 3, removed_bytes: 4096 }));
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} previewCleanup={previewCleanup} cleanupStorage={cleanupStorage} loadPerformance={() => Promise.resolve({ generated_at: "2026-08-12T08:00:00Z", metrics: [{ kind: "api", name: "/company-research", sample_count: 5, p50_ms: 800, p95_ms: 1600, failure_rate: 0, cache_hit_rate: 60, recent_ms: [500, 700, 800, 1200, 1600] }], snapshots: [{ kind: "market_cross_section", snapshot_version: 2, trade_date: "2026-08-12", observed_at: "2026-08-12T08:00:00Z", coverage_percent: 99, content_hash: "a".repeat(64), freshness: "live", source: "local-tdx", compute_count: 3, reuse_count: 4, duplicate_compute_count: 1, cache_hit_rate: 57.14, slowest_compute_ms: 320, latest_latency_ms: 8 }] })} />);

    const performanceHeading = await screen.findByRole("heading", { name: "页面与接口性能" });
    const performanceDetails = performanceHeading.closest("details");
    expect(performanceDetails).toHaveAttribute("open");
    expect(performanceDetails).toHaveClass("operations-collapsible");
    expect(performanceDetails).toHaveTextContent("默认展开");
    expect(screen.getByText(/本次会话请求合并/)).toBeInTheDocument();
    expect(screen.getByText("/company-research")).toBeVisible();
    expect(screen.getByText(/市场横截面/)).toBeVisible();
    expect(screen.getByText(/复用 4 · 重复计算 1/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "预览可清理空间" }));
    expect(await screen.findByText(/预计清理 3 个可重建文件/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认清理" }));
    expect(await screen.findByText(/已安全清理 3 个可重建文件/)).toBeInTheDocument();
    expect(cleanupStorage).toHaveBeenCalledWith(72);
  });

  it("expands every primary operations disclosure except task scripts by default", async () => {
    render(<OperationsView
      loadStatus={() => Promise.resolve(status)}
      setSchedulerPaused={() => Promise.resolve(status.scheduler)}
      createBackup={() => Promise.resolve(status.backups[0])}
      verifyBackup={() => Promise.reject(new Error("unused"))}
      runManualJob={() => Promise.resolve({ report_id: "report-manual" })}
      loadDiagnostics={() => Promise.resolve({
        generated_at: "2026-08-19T08:00:00Z", scheduler_paused: false, backup_count: 1,
        persistent_bytes: 1024, rebuildable_bytes: 512,
        source_health: { ready: 2, degraded: 0, unavailable: 1 },
        tdx_auto_import: status.tdx_auto_import!,
        source_conflicts: { state: "ready", conflict_count: 0, conflicts: [] },
      })}
      loadObservability={() => Promise.resolve({
        generated_at: "2026-08-19T08:00:00Z", window_size: 20, events: [], alerts: [],
      })}
      loadPerformance={() => Promise.resolve({ generated_at: "2026-08-19T08:00:00Z", metrics: [], snapshots: [] })}
    />);

    const expandedHeadings = ["运行诊断摘要", "可观测性事件与告警", "本地目录与数据库", "页面与接口性能"];
    for (const name of expandedHeadings) {
      const details = (await screen.findByRole("heading", { name })).closest("details");
      expect(details).toHaveAttribute("open");
      expect(details).toHaveClass("operations-collapsible");
    }
    expect(screen.getByRole("heading", { name: "任务运行脚本" }).closest("details")).not.toHaveAttribute("open");
  });

  it("preserves a user's collapsed section during the five-second status refresh", async () => {
    vi.useFakeTimers();
    try {
      render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} />);
      await vi.waitFor(() => expect(screen.getByRole("heading", { name: "本地目录与数据库" })).toBeInTheDocument());
      const inventoryDetails = screen.getByRole("heading", { name: "本地目录与数据库" }).closest("details")!;
      expect(inventoryDetails).toHaveAttribute("open");
      fireEvent.click(screen.getByRole("heading", { name: "本地目录与数据库" }));
      expect(inventoryDetails).not.toHaveAttribute("open");

      await vi.advanceTimersByTimeAsync(5000);
      expect(inventoryDetails).not.toHaveAttribute("open");
    } finally {
      vi.useRealTimers();
    }
  });

  it("shows the truthful daily-bar repair watermark and gaps", async () => {
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} loadHistoryRepairCenter={() => Promise.resolve({ coverage: { target_date: "2026-08-11", universe_count: 5000, backfill_complete_count: 4200, eligible_count: 4250, target_date_count: 0, dominant_trade_date: "2026-08-10", dominant_date_count: 4250, dominant_date_coverage_percent: 85, coverage_percent: 85, fragmented_latest_count: 750, missing_history_count: 750, quality: "partial", blockers: ["history_coverage_below_98_percent"] }, current_job: null, total_gap_count: 750, offset: 0, limit: 100, gaps: [{ symbol: "600001", bar_count: 120, latest_trade_date: "2026-08-10", gap_kind: "insufficient_history" }] })} />);

    expect(await screen.findByRole("heading", { name: /全市场日线修复中心/ })).toBeInTheDocument();
    expect(screen.getAllByText((_, element) => element?.textContent?.includes("85%") ?? false).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("历史不足")).toBeInTheDocument();
    expect(screen.getByText("600001")).toBeInTheDocument();
  });

  it("translates repair task states and English load failures into Chinese", async () => {
    const pausedJob = {
      job_id: "job-paused",
      mode: "backfill" as const,
      target_date: "2026-08-14",
      state: "paused" as const,
      pause_requested: false,
      total_count: 100,
      ready_count: 40,
      failed_count: 2,
      skipped_count: 3,
      pending_count: 55,
      tdx_ready_count: 40,
      baidu_ready_count: 0,
      created_at: "2026-08-14T08:00:00Z",
      updated_at: "2026-08-14T08:05:00Z",
    };
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} loadHistoryRepairCenter={() => Promise.resolve({ coverage: { target_date: "2026-08-14", universe_count: 100, backfill_complete_count: 40, eligible_count: 40, target_date_count: 40, dominant_trade_date: "2026-08-14", dominant_date_count: 40, dominant_date_coverage_percent: 40, coverage_percent: 40, fragmented_latest_count: 60, missing_history_count: 60, quality: "partial", blockers: ["history_coverage_below_98_percent"] }, current_job: pausedJob, total_gap_count: 60, offset: 0, limit: 100, gaps: [] })} loadDiagnostics={() => Promise.reject(new Error("backend service unavailable"))} />);

    expect(await screen.findByText("全量回填 · 已暂停")).toBeInTheDocument();
    expect(screen.queryByText(/paused/i)).not.toBeInTheDocument();
  });

  it("shows repair-before-and-after audit details when available", async () => {
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} loadHistoryRepairCenter={() => Promise.resolve({ coverage: { target_date: "2026-08-11", universe_count: 5000, backfill_complete_count: 5000, eligible_count: 5000, target_date_count: 5000, dominant_trade_date: "2026-08-11", dominant_date_count: 5000, dominant_date_coverage_percent: 100, coverage_percent: 100, fragmented_latest_count: 0, missing_history_count: 0, quality: "ready", blockers: [] }, current_job: null, total_gap_count: 0, offset: 0, limit: 100, gaps: [] })} loadHistoryRepairAudits={() => Promise.resolve([{ audit_id: "audit-1", job_id: "job-1", mode: "backfill", target_date: "2026-08-11", started_at: "2026-08-11T08:00:00Z", completed_at: "2026-08-11T08:05:00Z", source: "tdx-local-day", gap_count_before: 10, coverage_before_percent: 99.8, written_rows: 10, ready_count: 10, failed_count: 0, skipped_count: 0, coverage_after_percent: 100, final_state: "completed", failure_reasons: [] }])} />);

    expect(await screen.findByText("修复审计 · 1 条最近记录")).toBeInTheDocument();
    expect(screen.getByText("修复审计 · 1 条最近记录").closest("details")).toHaveAttribute("open");
    expect(screen.getByText(/覆盖 99.8% → 100%/)).toBeVisible();
    expect(screen.getByText(/写入 10 行/)).toBeVisible();
  });

  it("puts the full data repair workflow at the top with a truthful stale-data gate", async () => {
    const startRepair = vi.fn().mockResolvedValue({
      job_id: "full-repair", state: "pending", stage: "queued", percent: 0,
      source_url: "https://data.tdx.com.cn/vipdoc/hsjday.zip", downloaded_bytes: 0,
      day_file_count: 0, supported_file_count: 0, imported_rows: 0, replaced_rows: 0,
      skipped_rows: 0, failed_files: 0, validated_bytes: 0, total_validation_bytes: 0,
      extracted_files: 0, total_extract_files: 0, processed_files: 0,
      total_import_files: 0, online_total: 0, online_ready: 0, online_failed: 0,
      online_pending: 0, remaining_gap_count: 0, source_attempts: [],
      created_at: "2026-08-19T02:00:00Z", updated_at: "2026-08-19T02:00:00Z",
    });
    render(<OperationsView
      loadStatus={() => Promise.resolve(status)}
      setSchedulerPaused={() => Promise.resolve(status.scheduler)}
      createBackup={() => Promise.resolve(status.backups[0])}
      verifyBackup={() => Promise.reject(new Error("unused"))}
      runManualJob={() => Promise.resolve({ report_id: "report-manual" })}
      loadHistoryRepairCenter={() => Promise.resolve({
        coverage: {
          target_date: "2026-08-18", universe_count: 5970, backfill_complete_count: 5816,
          eligible_count: 5816, target_date_count: 5540, target_date_coverage_percent: 92.8,
          dominant_trade_date: "2026-08-15", dominant_date_count: 5540,
          dominant_date_coverage_percent: 92.8, coverage_percent: 97.42,
          fragmented_latest_count: 430, missing_history_count: 154, quality: "stale",
          blockers: ["dominant_trade_date_behind_target"], lag_trading_days: 1, is_fresh: false,
        }, current_job: null, total_gap_count: 430, offset: 0, limit: 100,
        gaps: [{ symbol: "600001", bar_count: 250, latest_trade_date: "2026-08-15", gap_kind: "behind_dominant_date" }],
      })}
      loadOfficialTdxInfo={() => Promise.resolve({ size_label: "520.67MB", modified_at: "2026-08-18T15:58:48+08:00" })}
      loadHistorySupplement={() => Promise.resolve({
        job_id: "full-repair-old", state: "partial", stage: "partial", percent: 100,
        source_url: "https://data.tdx.com.cn/vipdoc/hsjday.zip", downloaded_bytes: 545971146,
        total_bytes: 545971146, validated_bytes: 545971146, total_validation_bytes: 545971146,
        day_file_count: 6000, supported_file_count: 5970, extracted_files: 6000,
        total_extract_files: 6000, processed_files: 5970, total_import_files: 5970,
        imported_rows: 931444, replaced_rows: 84, skipped_rows: 100,
        failed_files: 0, online_total: 154, online_ready: 140, online_failed: 14,
        online_pending: 0, final_target_date: "2026-08-18",
        final_dominant_trade_date: "2026-08-15", final_dominant_coverage_percent: 92.8,
        final_history_coverage_percent: 97.42, remaining_gap_count: 154,
        final_quality: "stale", final_blockers: ["dominant_trade_date_behind_target"],
        result_detail: "主导交易日仍落后，剩余缺口已保留，可继续重试。",
        error_stage: "checking_metadata",
        error_detail: "'utf-8' codec can't decode byte 0xc1 in position 87: invalid start byte",
        source_attempts: [
          { source: "tdx_local", state: "completed", detail: "本机增量导入完成", observed_at: "2026-08-19T02:00:00Z" },
          { source: "tdx_official", state: "completed", detail: "官方包导入完成", observed_at: "2026-08-19T02:00:00Z" },
          { source: "mootdx", state: "completed", detail: "通达信在线成功 100 只", observed_at: "2026-08-19T02:00:00Z" },
          { source: "baidu", state: "completed", detail: "百度后备成功 40 只", observed_at: "2026-08-19T02:00:00Z" },
        ],
        created_at: "2026-08-19T01:00:00Z", updated_at: "2026-08-19T02:00:00Z",
        finished_at: "2026-08-19T02:00:00Z",
      })}
      startOfficialTdxSupplement={startRepair}
    />);

    const heading = await screen.findByRole("heading", { name: "数据完整性与补齐中心" });
    expect(heading.compareDocumentPosition(screen.getByRole("heading", { name: "全市场日线修复中心" })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText(/数据不完整，相关分析已降级/)).toBeInTheDocument();
    expect(screen.getByText(/落后 1 个交易日/)).toBeInTheDocument();
    expect(screen.getByText(/下载与校验/)).toBeInTheDocument();
    expect(screen.getByText(/解压文件/)).toBeInTheDocument();
    expect(screen.getByText("在线补缺")).toBeInTheDocument();
    expect(screen.getByText(/通达信在线成功 100 只/)).toBeInTheDocument();
    expect(screen.getByText(/百度后备成功 40 只/)).toBeInTheDocument();
    expect(screen.getByText(/本地行情数据库暂时不可读取，可能正在被其他任务占用，请等待当前任务完成后重试/)).toBeInTheDocument();
    expect(screen.queryByText(/invalid start byte/)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "一键全面修复" }));
    await waitFor(() => expect(startRepair).toHaveBeenCalledTimes(1));
  });

  it("highlights the active local scan and shows truthful scan counters", async () => {
    render(<OperationsView
      loadStatus={() => Promise.resolve(status)}
      setSchedulerPaused={() => Promise.resolve(status.scheduler)}
      createBackup={() => Promise.resolve(status.backups[0])}
      verifyBackup={() => Promise.reject(new Error("unused"))}
      runManualJob={() => Promise.resolve({ report_id: "report-manual" })}
      loadHistorySupplement={() => Promise.resolve({
        job_id: "scan-job", state: "running", stage: "scanning", percent: 4,
        source_url: "https://data.tdx.com.cn/vipdoc/hsjday.zip", downloaded_bytes: 0,
        day_file_count: 0, supported_file_count: 0, imported_rows: 0,
        replaced_rows: 0, skipped_rows: 0, failed_files: 0,
        validated_bytes: 0, total_validation_bytes: 0, extracted_files: 0,
        total_extract_files: 0, processed_files: 0, total_import_files: 0,
        online_total: 0, online_ready: 0, online_failed: 0, online_pending: 0,
        scan_scanned_files: 18, scan_total_files: null, scan_day_files: 18,
        scan_readable_files: 16, scan_current_file: "C:/tdx/vipdoc/sh/lday/sh600001.day",
        scan_speed: 6.4, scan_eta_seconds: null,
        remaining_gap_count: 0, final_blockers: [], source_attempts: [], created_at: "2026-08-25T01:00:00Z",
        updated_at: "2026-08-25T01:00:04Z",
      })}
    />);

    expect(await screen.findByText("扫描本机日线")).toBeInTheDocument();
    expect(screen.getByText(/已扫描 18 个文件 · 正在统计总量/)).toBeInTheDocument();
    expect(screen.getByText(/当前 sh600001\.day/)).toBeInTheDocument();
    expect(screen.getByText(/可读取 16 个/)).toBeInTheDocument();
    expect(screen.getByTestId("repair-stage-scanning")).toHaveAttribute("data-state", "active");
    expect(screen.queryByText(/4\.00%/)).not.toBeInTheDocument();
  });

  it("shows a completed scan while waiting for the local database", async () => {
    vi.useRealTimers();
    render(<OperationsView
      loadStatus={() => Promise.resolve(status)}
      setSchedulerPaused={() => Promise.resolve(status.scheduler)}
      createBackup={() => Promise.resolve(status.backups[0])}
      verifyBackup={() => Promise.reject(new Error("unused"))}
      runManualJob={() => Promise.resolve({ report_id: "report-manual" })}
      loadHistorySupplement={vi.fn().mockResolvedValue({
        job_id: "waiting-job", state: "running", stage: "waiting_database", percent: 6,
        source_url: "https://data.tdx.com.cn/vipdoc/hsjday.zip", downloaded_bytes: 0,
        day_file_count: 0, supported_file_count: 0, imported_rows: 0,
        replaced_rows: 0, skipped_rows: 0, failed_files: 0,
        validated_bytes: 0, total_validation_bytes: 0, extracted_files: 0,
        total_extract_files: 0, processed_files: 0, total_import_files: 0,
        online_total: 0, online_ready: 0, online_failed: 0, online_pending: 0,
        scan_scanned_files: 9497, scan_total_files: 9497, scan_day_files: 9497,
        scan_readable_files: 9497, scan_current_file: null, scan_speed: 256,
        scan_eta_seconds: 0, result_detail: "本机日线扫描已完成，正在等待本地行情数据库释放并自动重试",
        remaining_gap_count: 0, final_blockers: [], source_attempts: [], created_at: "2026-08-25T01:00:00Z",
        updated_at: "2026-08-25T01:00:04Z",
      })}
    />);

    await waitFor(() => expect(screen.getByRole("heading", { name: "数据与运维中心" })).toBeInTheDocument(), { timeout: 1000 });
    expect(await waitFor(() => screen.getByText(/等待本地数据库释放/), { timeout: 1000 })).toBeInTheDocument();
    expect(screen.getByText(/本机日线扫描已完成/)).toBeInTheDocument();
    expect(screen.getByText(/9497 \/ 9497/)).toBeInTheDocument();
    expect(screen.getByTestId("repair-stage-waiting_database")).toHaveAttribute("data-state", "active");
  });
});
