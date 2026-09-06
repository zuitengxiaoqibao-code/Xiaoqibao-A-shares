import { CheckCircle2, ExternalLink, KeyRound, Link2Off, Loader2, Save, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { friendlyError } from "../../shared/friendlyError";
import type { ExternalDataSourceClearer, ExternalDataSourceLoader, ExternalDataSourceSaver, ExternalDataSourceTester, ExternalDataSourceView } from "./types";

type Props = {
  load: ExternalDataSourceLoader;
  save: ExternalDataSourceSaver;
  clear: ExternalDataSourceClearer;
  test: ExternalDataSourceTester;
};

const statusLabel: Record<ExternalDataSourceView["status"], string> = {
  unconfigured: "未配置", configured: "已配置", ready: "在线", limited: "权限受限", unavailable: "异常",
};

const capabilityStatusLabel = {
  ready: "可用",
  limited: "无权限",
  unavailable: "不可用",
  unverified: "待检测",
} as const;

export function ExternalDataSourceSection({ load, save, clear, test }: Props) {
  const [sources, setSources] = useState<ExternalDataSourceView[]>([]);
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).then((result) => setSources(result.sources)).catch((error) => setMessage(friendlyError(error, "备用数据源")));
    return () => controller.abort();
  }, [load]);

  const replace = (item: ExternalDataSourceView) => setSources((current) => current.map((source) => source.source_id === item.source_id ? item : source));
  const run = async (source: ExternalDataSourceView, action: "save" | "test" | "clear") => {
    setBusy((current) => ({ ...current, [source.source_id]: action }));
    setMessage("");
    try {
      let result: ExternalDataSourceView;
      if (action === "save") {
        await save(source.source_id, keys[source.source_id] ?? "", true);
        result = await test(source.source_id);
      }
      else if (action === "clear") result = await clear(source.source_id);
      else result = await test(source.source_id);
      replace(result);
      if (action === "save") setKeys((current) => ({ ...current, [source.source_id]: "" }));
      setMessage(`${source.name}：${statusLabel[result.status]}${result.last_error ? `，${result.last_error}` : ""}`);
    } catch (error) {
      setMessage(`${source.name}：${friendlyError(error, "操作失败")}`);
    } finally {
      setBusy((current) => { const next = { ...current }; delete next[source.source_id]; return next; });
    }
  };

  return <section className="settings-section external-data-source-section">
    <div className="settings-section-heading"><div><p className="eyebrow">备用通道</p><h2>第三方行情数据源</h2><p>填写自己的 Key 后作为 TickFlow、扶摇或 Tushare 备用来源。主数据源不变，接口失败会保留真实不可用状态。</p></div><Link2Off size={18} aria-hidden="true" /></div>
    <div className="external-data-source-grid">
      {sources.map((source) => {
        const action = busy[source.source_id];
        return <article className="external-data-source-card" key={source.source_id}>
          <header><div><h3>{source.name}</h3><p>{source.description}</p></div><span className={`settings-status status-${source.status}`}><span className="status-dot" />{statusLabel[source.status]}</span></header>
          <div className="external-capabilities" aria-label={`${source.name}接口权限`}>
            {(source.capability_checks?.length ? source.capability_checks : source.capabilities.map((label) => ({ key: label, label, status: "unverified" as const, detail: "尚未进行接口权限检测" }))).map((capability) => <span
              key={capability.key}
              data-status={capability.status}
              className={`capability-${capability.status}`}
              title={`${capabilityStatusLabel[capability.status]}：${capability.detail}`}
            >{capability.label}{capability.status !== "ready" && <small> · {capabilityStatusLabel[capability.status]}</small>}</span>)}
          </div>
          {source.capability_checks?.length ? <p className="external-capability-summary" role="status">
            已逐项检测：{source.capability_checks.filter((item) => item.status === "ready").length}/{source.capability_checks.length} 项可用；划线项目当前 Key 无法调用。
          </p> : null}
          <label className="external-key-field"><span><KeyRound size={14} />{source.key_label}</span><input type="password" autoComplete="off" placeholder={source.api_key_hint ?? "粘贴 API Key / Token"} value={keys[source.source_id] ?? ""} onChange={(event) => setKeys((current) => ({ ...current, [source.source_id]: event.target.value }))} /></label>
          <div className="external-source-meta"><a href={source.key_url} target="_blank" rel="noreferrer">查看官方文档 <ExternalLink size={12} /></a>{source.last_tested_at && <span>最近测试 {new Date(source.last_tested_at).toLocaleString("zh-CN")}</span>}</div>
          <div className="settings-actions"><button type="button" className="settings-action" disabled={Boolean(action) || !(keys[source.source_id] ?? "").trim()} onClick={() => void run(source, "save")}>{action === "save" ? <Loader2 className="spin" size={15} /> : <Save size={15} />}保存并测试</button><button type="button" className="settings-action secondary" disabled={Boolean(action) || !source.configured} onClick={() => void run(source, "test")}>{action === "test" ? <Loader2 className="spin" size={15} /> : <CheckCircle2 size={15} />}测试连接</button><button type="button" className="settings-action danger" disabled={Boolean(action) || !source.configured} onClick={() => void run(source, "clear")}><Trash2 size={15} />清除</button></div>
        </article>;
      })}
    </div>
    {message && <p className="speech-settings-message" role="status">{message}</p>}
  </section>;
}
