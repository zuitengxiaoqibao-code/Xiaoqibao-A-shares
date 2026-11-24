import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RepairProgressNumbers, repairDuration } from "./RepairProgressNumbers";
import type { HistorySupplementJob } from "./types";

const job: HistorySupplementJob = {
  job_id: "repair", state: "running", stage: "online_repair", percent: 90,
  phase_label: "在线补齐", phase_percent: 25, phase_eta_seconds: 120,
  phase_rate: 4, phase_unit: "只", source_url: "", downloaded_bytes: 0,
  day_file_count: 0, supported_file_count: 0, imported_rows: 10, replaced_rows: 0,
  skipped_rows: 0, failed_files: 0, validated_bytes: 0, total_validation_bytes: 0,
  extracted_files: 0, total_extract_files: 0, processed_files: 0, total_import_files: 0,
  online_total: 40, online_ready: 10, online_failed: 0, online_pending: 30,
  remaining_gap_count: 0, final_blockers: [], source_attempts: [],
  created_at: "2026-11-19T07:00:00Z", updated_at: "2026-11-19T07:01:00Z",
};

describe("RepairProgressNumbers", () => {
  afterEach(() => vi.useRealTimers());

  it("shows actual counts alongside current phase percentage, ETA and speed", () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-11-19T07:01:05Z"));
    render(<RepairProgressNumbers job={job} />);
    expect(screen.getByText("25.0%")).toBeInTheDocument();
    expect(screen.getByRole("progressbar")).toHaveAttribute("value", "25");
    expect(screen.getByText(/预计剩余：约 2 分 0 秒/)).toBeInTheDocument();
    expect(screen.getByText(/当前速度：4.0 只\/秒/)).toBeInTheDocument();
    expect(screen.getByText("10 / 40 只")).toBeInTheDocument();
  });

  it("does not keep promising a stale ETA or claim partial work is complete", () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-11-19T07:02:05Z"));
    const view = render(<RepairProgressNumbers job={job} />);
    expect(screen.getByText(/等待新进度，暂无法估算/)).toBeInTheDocument();
    expect(screen.getByText("当前速度：等待新进度")).toBeInTheDocument();
    view.rerender(<RepairProgressNumbers job={{ ...job, state: "partial", stage: "partial", percent: 100 }} />);
    expect(screen.getByText("未全部补齐")).toBeInTheDocument();
    expect(screen.queryByText("100%")).not.toBeInTheDocument();
  });

  it("formats bounded durations", () => {
    expect(repairDuration(0)).toBe("1 秒");
    expect(repairDuration(61)).toBe("1 分 1 秒");
    expect(repairDuration(3660)).toBe("1 小时 1 分");
  });

  it("keeps metric slots and progress in place across batches, stale readings and stages", () => {
    vi.useFakeTimers(); vi.setSystemTime(new Date("2026-11-19T07:01:05Z"));
    const view = render(<RepairProgressNumbers job={job} />);
    const labels = Array.from(view.container.querySelectorAll("dt"), (node) => node.textContent);
    const bar = screen.getByRole("progressbar");
    const cells = Array.from(view.container.querySelectorAll("dd"));
    expect(labels).toHaveLength(12);
    for (const next of [
      { ...job, stage: "importing", pending_write_rows: 18000, scan_current_file: "D:/行情/sh600000.day" },
      { ...job, stage: "downloading", phase_rate: null, downloaded_bytes: 10485760 },
      { ...job, updated_at: "2026-11-19T07:00:00Z", online_skipped: 8 },
      { ...job, state: "completed", stage: "completed", finished_at: job.updated_at },
    ] as HistorySupplementJob[]) {
      view.rerender(<RepairProgressNumbers job={next} />);
      expect(screen.getByRole("progressbar")).toBe(bar);
      expect(Array.from(view.container.querySelectorAll("dt"), (node) => node.textContent)).toEqual(labels);
      expect(Array.from(view.container.querySelectorAll("dd"))).toEqual(cells);
      expect(view.container.querySelectorAll(".repair-progress-timing p")).toHaveLength(3);
      expect(view.container.querySelectorAll(".repair-progress-status p")).toHaveLength(2);
    }
    expect(bar).toHaveAttribute("value", "100");
  });
});
