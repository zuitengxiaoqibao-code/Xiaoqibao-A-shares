import { fireEvent, render, screen } from "@testing-library/react";
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
    expect(inventoryDetails).not.toHaveAttribute("open");
    fireEvent.click(screen.getByRole("heading", { name: "本地目录与数据库" }));
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

  it("previews rebuildable storage before confirmed cleanup and keeps performance folded", async () => {
    const previewCleanup = vi.fn(() => Promise.resolve({ candidate_count: 3, candidate_bytes: 4096, categories: { cache: 2, logs: 1 } }));
    const cleanupStorage = vi.fn(() => Promise.resolve({ removed_count: 3, removed_bytes: 4096 }));
    render(<OperationsView loadStatus={() => Promise.resolve(status)} setSchedulerPaused={() => Promise.resolve(status.scheduler)} createBackup={() => Promise.resolve(status.backups[0])} verifyBackup={() => Promise.reject(new Error("unused"))} runManualJob={() => Promise.resolve({ report_id: "report-manual" })} previewCleanup={previewCleanup} cleanupStorage={cleanupStorage} loadPerformance={() => Promise.resolve({ generated_at: "2026-08-12T08:00:00Z", metrics: [{ kind: "api", name: "/company-research", sample_count: 5, p50_ms: 800, p95_ms: 1600, failure_rate: 0, cache_hit_rate: 60, recent_ms: [500, 700, 800, 1200, 1600] }], snapshots: [{ kind: "market_cross_section", snapshot_version: 2, trade_date: "2026-08-12", observed_at: "2026-08-12T08:00:00Z", coverage_percent: 99, content_hash: "a".repeat(64), freshness: "live", source: "local-tdx", compute_count: 3, reuse_count: 4, duplicate_compute_count: 1, cache_hit_rate: 57.14, slowest_compute_ms: 320, latest_latency_ms: 8 }] })} />);

    expect(await screen.findByText("页面与接口性能 · 默认折叠")).toBeInTheDocument();
    expect(screen.getByText(/本次会话请求合并/)).toBeInTheDocument();
    expect(screen.getByText("/company-research")).not.toBeVisible();
    fireEvent.click(screen.getByText("页面与接口性能 · 默认折叠"));
    expect(screen.getByText(/市场横截面/)).toBeVisible();
    expect(screen.getByText(/复用 4 · 重复计算 1/)).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "预览可清理空间" }));
    expect(await screen.findByText(/预计清理 3 个可重建文件/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "确认清理" }));
    expect(await screen.findByText(/已安全清理 3 个可重建文件/)).toBeInTheDocument();
    expect(cleanupStorage).toHaveBeenCalledWith(72);
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
    fireEvent.click(screen.getByText("修复审计 · 1 条最近记录"));
    expect(screen.getByText(/覆盖 99.8% → 100%/)).toBeVisible();
    expect(screen.getByText(/写入 10 行/)).toBeVisible();
  });
});
