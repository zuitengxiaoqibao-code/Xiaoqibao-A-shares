import type { HistorySupplementJob } from "./types";
import "./repairProgress.css";

const count = (value: number) => value.toLocaleString("zh-CN");
const files = (done: number, total: number | null | undefined) => total == null ? `${count(done)} 个，待统计总量` : `${count(done)} / ${count(total)} 个`;
const mb = (value: number) => `${(value / 1048576).toFixed(1)} MB`;
export function repairDuration(seconds: number): string {
  const rounded = Math.max(1, Math.ceil(seconds));
  if (rounded < 60) return `${rounded} 秒`;
  if (rounded < 3600) return `${Math.floor(rounded / 60)} 分 ${rounded % 60} 秒`;
  return `${Math.floor(rounded / 3600)} 小时 ${Math.ceil((rounded % 3600) / 60)} 分`;
}

function phasePercent(job: HistorySupplementJob): number | null {
  if (job.phase_percent != null) return job.phase_percent;
  const [done, total] = job.stage === "downloading" ? [job.downloaded_bytes, job.total_bytes]
    : job.stage === "extracting" ? [job.extracted_files, job.total_extract_files]
    : job.stage === "importing" ? [job.processed_files, job.total_import_files]
    : job.stage === "online_repair" ? [job.online_total - job.online_pending, job.online_total]
    : job.stage === "scanning" ? [job.scan_scanned_files ?? 0, job.scan_total_files]
    : [job.validated_bytes, ["validating", "validating_cache"].includes(job.stage) ? job.total_validation_bytes : 0];
  return total ? Math.min(100, Math.max(0, done / total * 100)) : null;
}

export function repairActivityLabel(job: HistorySupplementJob): string {
  if (job.stage === "downloading") return `已下载 ${mb(job.downloaded_bytes)}`;
  if (job.stage === "online_repair") return `在线成功 ${count(job.online_ready)} 只 · 失败 ${count(job.online_failed)} 只`;
  if (job.total_import_files > 0) return `已处理 ${files(job.processed_files, job.total_import_files)}文件 · 已新增 ${count(job.imported_rows)} 行`;
  if (job.scan_scanned_files) return `已发现 ${count(job.scan_scanned_files)} 个文件`;
  return "正在准备修复来源";
}

export function RepairProgressNumbers({ job }: { job: HistorySupplementJob }) {
  const active = job.state === "pending" || job.state === "running";
  const percent = phasePercent(job);
  const stale = Date.now() - Date.parse(job.updated_at) > 15000;
  const elapsed = Math.max(0, ((active ? Date.now() : Date.parse(job.finished_at ?? job.updated_at)) - Date.parse(job.created_at)) / 1000);
  const eta = !active ? "本轮已结束" : stale ? "等待新进度，暂无法估算"
    : job.phase_eta_seconds != null ? `约 ${repairDuration(job.phase_eta_seconds)}` : "正在采样估算";
  const speed = !active ? "本轮已结束" : stale ? "等待新进度" : job.phase_rate == null ? "正在采样"
    : job.phase_unit === "字节" ? `${(job.phase_rate / 1048576).toFixed(1)} MB/秒` : `${job.phase_rate.toFixed(1)} ${job.phase_unit ?? "项"}/秒`;
  const currentFile = job.scan_current_file?.split(/[\\/]/).pop() || "—";
  const progressValue = job.state === "completed" ? 100 : percent;
  return <div className="repair-progress-numbers" aria-label="数据修复实际数量">
    <section className="repair-phase-progress" aria-label="修复阶段进度">
      <div><strong>{active ? (job.phase_label ?? "当前阶段") : job.state === "completed" ? "复核通过" : "本轮已结束，仍需补齐"}</strong><span>{active && percent != null ? `${percent.toFixed(1)}%` : active ? "统计中" : job.state === "completed" ? "100%" : "未全部补齐"}</span></div>
      <progress aria-label="当前阶段完成百分比" max={100} {...(progressValue == null ? (active ? {} : { value: 0 }) : { value: progressValue })} />
      <div className="repair-progress-timing">
        <p title={`已用时 ${repairDuration(elapsed)}`}>已用时 {repairDuration(elapsed)}</p>
        <p title={`当前阶段预计剩余：${eta}`}>当前阶段预计剩余：{eta}</p>
        <p title={`当前速度：${speed}`}>当前速度：{speed}</p>
      </div>
      <p className="repair-progress-caption">百分比及预计剩余时间对应当前阶段，完成后以数据覆盖复核为准。</p>
    </section>
    <dl>
      <div><dt>发现日线文件</dt><dd>{files(job.scan_scanned_files ?? 0, job.scan_total_files)}</dd></div>
      <div><dt>已处理 A 股文件</dt><dd>{job.total_import_files ? files(job.processed_files, job.total_import_files) : "尚未开始"}</dd></div>
      <div><dt>已新增入库</dt><dd>{count(job.imported_rows)} 行</dd></div>
      <div><dt>已升级来源</dt><dd>{count(job.replaced_rows)} 行</dd></div>
      <div><dt>已存在跳过</dt><dd>{count(job.skipped_rows)} 行</dd></div>
      <div><dt>失败文件</dt><dd>{count(job.failed_files)} 个</dd></div>
      <div><dt>已下载</dt><dd>{mb(job.downloaded_bytes)}{job.total_bytes ? ` / ${mb(job.total_bytes)}` : "，总量待确认"}</dd></div>
      <div><dt>已校验</dt><dd>{mb(job.validated_bytes)} / {mb(job.total_validation_bytes)}</dd></div>
      <div><dt>已解压</dt><dd>{files(job.extracted_files, job.total_extract_files)}</dd></div>
        <div><dt>在线成功</dt><dd>{count(job.online_ready)} / {count(job.online_total)} 只</dd></div>
        <div><dt>核实完整 / 无需重复补齐</dt><dd>{count(job.online_skipped ?? 0)} 只</dd></div>
        <div><dt>在线失败 / 待处理</dt><dd>{count(job.online_failed)} / {count(job.online_pending)} 只</dd></div>
    </dl>
    <div className="repair-progress-status">
      <p>{(job.pending_write_rows ?? 0) > 0 ? `正在提交本批 ${count(job.pending_write_rows!)} 行，提交后更新入库数量。` : "本批待提交：0 行"}</p>
      <p title={job.scan_current_file || "尚无当前文件"}>当前文件：{currentFile}</p>
    </div>
  </div>;
}
