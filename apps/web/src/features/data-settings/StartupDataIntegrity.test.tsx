import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { StartupDataIntegrity } from "./StartupDataIntegrity";
import type { HistoryCoverageSummary, HistorySupplementJob } from "./types";

const ready: HistoryCoverageSummary = {
  target_date: "2026-11-18", universe_count: 5200, backfill_complete_count: 5180,
  eligible_count: 5180, target_date_count: 5180, dominant_trade_date: "2026-11-18",
  dominant_date_count: 5180, dominant_date_coverage_percent: 99.6, coverage_percent: 99.6,
  fragmented_latest_count: 0, missing_history_count: 20, quality: "ready", blockers: [],
};
const missing: HistoryCoverageSummary = { ...ready, quality: "partial", coverage_percent: 40, blockers: ["history_coverage_below_98_percent"] };
const pending: HistorySupplementJob = {
  job_id: "repair-1", state: "pending", stage: "queued", percent: 0, source_url: "",
  downloaded_bytes: 0, day_file_count: 0, supported_file_count: 0, imported_rows: 0,
  replaced_rows: 0, skipped_rows: 0, failed_files: 0, validated_bytes: 0, total_validation_bytes: 0,
  extracted_files: 0, total_extract_files: 0, processed_files: 0, total_import_files: 0,
  online_total: 0, online_ready: 0, online_failed: 0, online_pending: 0, remaining_gap_count: 0,
  final_blockers: [], source_attempts: [], created_at: "2026-11-19T02:00:00Z", updated_at: "2026-11-19T02:00:00Z",
};
async function startCheck() { await act(async () => { await vi.advanceTimersByTimeAsync(650); }); }

describe("StartupDataIntegrity", () => {
  beforeEach(() => vi.useFakeTimers({ shouldAdvanceTime: true }));
  afterEach(() => vi.useRealTimers());

  it("reads new progress while the start acknowledgement is pending and ignores a late queued response", async () => {
    let acknowledge!: (job: HistorySupplementJob) => void;
    const old = { ...pending, state: "partial", stage: "partial" } as HistorySupplementJob;
    const running = { ...pending, job_id: "repair-2", state: "running", stage: "online_repair", imported_rows: 5537 } as HistorySupplementJob;
    const loadJob = vi.fn().mockResolvedValueOnce(old).mockResolvedValueOnce(old).mockResolvedValue(running);
    const startRepair = vi.fn(() => new Promise<HistorySupplementJob>((resolve) => { acknowledge = resolve; }));
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue(missing)} loadJob={loadJob} startRepair={startRepair} />);
    await startCheck();
    fireEvent.click(screen.getByRole("button", { name: "一键全面修复数据" }));
    await act(async () => { await vi.advanceTimersByTimeAsync(1300); });
    expect(screen.getByRole("button", { name: "正在启动…" })).toBeDisabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(1600); });
    expect(screen.getByRole("button", { name: "正在补齐数据" })).toBeDisabled();
    expect(screen.getByText("5,537 行")).toBeInTheDocument();
    await act(async () => { acknowledge({ ...pending, job_id: "repair-2" }); });
    expect(screen.getByText("5,537 行")).toBeInTheDocument();
    expect(startRepair).toHaveBeenCalledTimes(1);
  });

  it("unlocks retry and shows the reason when submission fails with only an old task present", async () => {
    const old = { ...pending, state: "partial", stage: "partial" } as HistorySupplementJob;
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue(missing)} loadJob={vi.fn().mockResolvedValue(old)} startRepair={vi.fn().mockRejectedValue(new Error("服务正在关闭"))} />);
    await startCheck();
    fireEvent.click(screen.getByRole("button", { name: "一键全面修复数据" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("服务正在关闭"));
    expect(screen.getByRole("button", { name: "一键全面修复数据" })).toBeEnabled();
  });

  it("paints first and checks local data without starting repair for healthy data", async () => {
    const loadCoverage = vi.fn().mockResolvedValue(ready);
    const startRepair = vi.fn();
    render(<StartupDataIntegrity loadCoverage={loadCoverage} loadJob={vi.fn().mockResolvedValue(null)} startRepair={startRepair} />);
    expect(loadCoverage).not.toHaveBeenCalled();
    await startCheck();
    expect(loadCoverage).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(startRepair).not.toHaveBeenCalled();
  });

  it("requires a user click, shows the actual progress, continues after minimizing and rechecks coverage", async () => {
    const loadCoverage = vi.fn().mockResolvedValueOnce(missing).mockResolvedValue(ready);
    const done = { ...pending, state: "completed", stage: "completed", percent: 100, imported_rows: 34000 };
    const loadJob = vi.fn().mockResolvedValueOnce(null).mockResolvedValueOnce({ ...pending, state: "running", stage: "downloading", percent: 28, downloaded_bytes: 10485760, total_bytes: 104857600 }).mockResolvedValue(done);
    const startRepair = vi.fn().mockResolvedValue(pending);
    render(<StartupDataIntegrity loadCoverage={loadCoverage} loadJob={loadJob} startRepair={startRepair} />);
    await startCheck();
    expect(screen.getByRole("dialog")).toHaveTextContent("历史日线覆盖不足 98%");
    expect(startRepair).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "一键全面修复数据" }));
    await waitFor(() => expect(screen.getByText("已新增入库")).toBeInTheDocument());
    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(1300); });
    expect(screen.getByText("10.0 MB / 100.0 MB")).toBeInTheDocument();
    expect(screen.getByText("10.0%")).toBeInTheDocument();
    expect(screen.queryByText("28%")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "后台继续" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /数据补齐进行中/ })).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(1800); });
    expect(loadCoverage).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("button", { name: /数据补齐进行中/ })).not.toBeInTheDocument();
    expect(startRepair).toHaveBeenCalledTimes(1);
  });

  it("does not mistake a tiny stock directory for full market coverage", async () => {
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue({ ...ready, universe_count: 1 })} loadJob={vi.fn().mockResolvedValue(null)} startRepair={vi.fn()} />);
    await startCheck();
    expect(screen.getByRole("dialog")).toHaveTextContent("证券目录数量不足");
  });

  it("shows failed sources and remaining gaps even if workflow progress reaches 100", async () => {
    const partial = { ...pending, state: "partial", stage: "partial", percent: 100, result_detail: "覆盖仍不足，保留缺口", source_attempts: [{ source: "tdx_official", state: "failed", detail: "下载超时，已切换在线来源", observed_at: pending.updated_at }] };
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue(missing)} loadJob={vi.fn().mockResolvedValue(partial)} startRepair={vi.fn()} />);
    await startCheck();
    expect(screen.getByRole("dialog")).toHaveTextContent("下载超时，已切换在线来源");
    expect(screen.getByRole("dialog")).toHaveTextContent("仍有数据缺口");
    expect(screen.getByRole("button", { name: "一键全面修复数据" })).toBeEnabled();
    expect(screen.queryByText("数据完整性复核通过")).not.toBeInTheDocument();
  });

  it("reports a check failure accurately and allows a read-only retry", async () => {
    const loadCoverage = vi.fn().mockRejectedValueOnce(new Error("数据库暂被占用")).mockResolvedValue(ready);
    const startRepair = vi.fn();
    render(<StartupDataIntegrity loadCoverage={loadCoverage} loadJob={vi.fn().mockResolvedValue(null)} startRepair={startRepair} />);
    await startCheck();
    expect(screen.getByRole("alert")).toHaveTextContent("数据库暂被占用");
    expect(screen.getByRole("dialog")).toHaveTextContent("检测未完成");
    fireEvent.click(screen.getByRole("button", { name: "重新检测" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "数据完整性复核通过" })).toBeInTheDocument());
    expect(startRepair).not.toHaveBeenCalled();
  });

  it("keeps verified remaining gaps visible even when the usable coverage threshold passes", async () => {
    const partial = { ...pending, state: "partial", stage: "partial", remaining_gap_count: 8,
      result_detail: "达到可用标准，仍有 8 只待核实" } as HistorySupplementJob;
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue(ready)} loadJob={vi.fn().mockResolvedValue(partial)} startRepair={vi.fn()} />);
    await startCheck();
    expect(screen.getByRole("dialog")).toHaveTextContent("仍有 8 只待核实");
    expect(screen.queryByText("数据完整性复核通过")).not.toBeInTheDocument();
    expect(screen.getByText("未全部补齐")).toBeInTheDocument();
  });

  it("recovers an already running job after reopening the app without launching it again", async () => {
    const startRepair = vi.fn();
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue(missing)} loadJob={vi.fn().mockResolvedValue({ ...pending, state: "running", stage: "online_repair", percent: 83 })} startRepair={startRepair} />);
    await startCheck();
    expect(screen.getByRole("dialog")).toHaveTextContent("正在自动补齐数据");
    expect(screen.getByRole("button", { name: "正在补齐数据" })).toBeDisabled();
    expect(startRepair).not.toHaveBeenCalled();
  });

  it("stops its pending check when unmounted and does not post a repair", async () => {
    const loadCoverage = vi.fn(); const startRepair = vi.fn();
    const view = render(<StartupDataIntegrity loadCoverage={loadCoverage} loadJob={vi.fn()} startRepair={startRepair} />);
    view.unmount();
    await startCheck();
    expect(loadCoverage).not.toHaveBeenCalled();
    expect(startRepair).not.toHaveBeenCalled();
  });

  it("updates actual counts and true phase percentages, suppressing stale estimates", async () => {
    const running = { ...pending, state: "running", stage: "importing", percent: 6,
      scan_scanned_files: 9625, scan_total_files: 9625, processed_files: 48, total_import_files: 5200,
      imported_rows: 12000, replaced_rows: 500, failed_files: 2, pending_write_rows: 18000,
      updated_at: new Date(Date.now() - 30000).toISOString(),
    };
    const loadJob = vi.fn().mockResolvedValueOnce(running).mockResolvedValue({ ...running, processed_files: 64, imported_rows: 30000, pending_write_rows: 0 });
    render(<StartupDataIntegrity loadCoverage={vi.fn().mockResolvedValue(missing)} loadJob={loadJob} startRepair={vi.fn()} />);
    await startCheck();
    expect(screen.getByText("48 / 5,200 个")).toBeInTheDocument();
    expect(screen.getByText("12,000 行")).toBeInTheDocument();
    expect(screen.getByText(/正在提交本批 18,000 行/)).toBeInTheDocument();
    expect(screen.getByText(/未收到新进度/)).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("value", String(48 / 5200 * 100));
    expect(screen.getByText(/等待新进度，暂无法估算/)).toBeInTheDocument();
    expect(screen.queryByText("6%")).not.toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(1300); });
    expect(screen.getByText("64 / 5,200 个")).toBeInTheDocument();
    expect(screen.getByText("30,000 行")).toBeInTheDocument();
    expect(screen.queryByText(/正在提交本批/)).not.toBeInTheDocument();
  });
});
