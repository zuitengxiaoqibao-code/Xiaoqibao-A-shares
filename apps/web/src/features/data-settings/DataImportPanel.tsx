import { Database, FileUp, RefreshCw, ShieldAlert } from "lucide-react";
import { useState } from "react";

import type { DataImportIngestor, DataImportInspector, DataImportPreview, DataImportTask } from "./types";

type Props = { inspect: DataImportInspector; ingest: DataImportIngestor };

const labels: Record<string, string> = { inspect: "读取文件", decode: "解码", normalize: "标准化", validate: "校验", merge: "多源裁决", publish: "发布", completed: "已完成" };

export function DataImportPanel({ inspect, ingest }: Props) {
  const [preview, setPreview] = useState<DataImportPreview | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [task, setTask] = useState<DataImportTask | null>(null);
  const [error, setError] = useState("");
  const choose = (selected: File | null) => {
    setFile(selected); setPreview(null); setTask(null); setError("");
    if (!selected) return;
    void inspect(selected).then((value) => {
      setPreview(value);
      setMapping(Object.fromEntries(value.columns.map((column) => [column, column])));
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "文件预览失败"));
  };
  const publish = () => {
    if (!file) return;
    setError("");
    void ingest(file, mapping).then(setTask).catch((reason) => setError(reason instanceof Error ? reason.message : "数据导入失败"));
  };
  return <section className="settings-section data-import-panel" aria-label="多格式数据导入">
    <div className="settings-heading"><div><Database size={20} /><span><h2>多格式数据导入</h2><p>CSV、JSON、Parquet、SQLite、DuckDB 和 ZIP；原始文件与隔离行保留在本机。</p></span></div></div>
    <label className="data-import-picker">选择本地数据文件<input aria-label="导入数据文件" type="file" accept=".csv,.tsv,.json,.jsonl,.parquet,.sqlite,.sqlite3,.db,.duckdb,.xls,.xlsx,.zip" onChange={(event) => choose(event.target.files?.[0] ?? null)} /></label>
    {error && <p className="cockpit-error" role="alert"><ShieldAlert size={15} />{error}</p>}
    {preview && <div className="data-import-preview" role="status"><strong>{preview.format.toUpperCase()} · {preview.row_count} 行</strong><span>字段：{preview.columns.join("、") || "未识别"}</span>{preview.error && <span className="data-import-error">{preview.error}</span>}<div className="data-import-mapping">{preview.columns.map((column) => <label key={column}>{column}<input aria-label={`映射 ${column}`} value={mapping[column] ?? column} onChange={(event) => setMapping((current) => ({ ...current, [column]: event.target.value }))} /></label>)}</div><button type="button" className="settings-action" disabled={!file} onClick={publish}><FileUp size={15} />发布导入</button></div>}
    {task && <div className={`data-import-task ${task.quality_status}`} role="status"><div><b>{labels[task.stage] ?? task.stage} · {Math.round(task.progress)}%</b><small>{task.processed} / {task.total} 行 · 隔离 {task.quarantined_rows} 行</small></div><progress max={100} value={task.progress} /><strong>数据质量：{task.quality_status === "ready" ? "完整可用" : task.quality_status === "partial" ? "部分可用" : "不可用"}</strong>{task.quarantine_reasons?.map((reason) => <span className="data-import-error" key={reason}><ShieldAlert size={14} />{reason}</span>)}{task.error_message && <span className="data-import-error"><ShieldAlert size={14} />{task.error_message}</span>}</div>}
    {!preview && !task && !error && <small className="data-import-empty"><RefreshCw size={14} />选择文件后将先预览，不会直接覆盖已有数据</small>}
  </section>;
}
