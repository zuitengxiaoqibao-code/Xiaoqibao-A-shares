import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Database,
  FolderSearch,
  Plus,
  RefreshCw,
  Save,
  Trash2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { friendlyError } from "../../shared/friendlyError";
import type {
  LocalSourceSettings,
  LocalSourceSettingsLoader,
  LocalSourceSettingsView,
  LocalSourceSettingsWriter,
} from "./types";

type Props = {
  load: LocalSourceSettingsLoader;
  detect: LocalSourceSettingsWriter;
  save: LocalSourceSettingsWriter;
};

type PathKind = "tdx_install_paths" | "ths_install_paths";

const defaultSettings: LocalSourceSettings = {
  auto_discovery: true,
  tdx_install_paths: [],
  ths_install_paths: [],
  tdx_rpc_enabled: false,
  tdx_rpc_url: null,
};

const vendorLabel = { tdx: "通达信", ths: "同花顺" } as const;
const originLabel = {
  manual: "手动配置",
  process: "运行进程",
  registry: "系统注册",
  common: "常见目录",
} as const;

const rpcStatusLabel = {
  ready: "全部只读能力可用",
  partial: "部分只读能力可用",
  unavailable: "桥接不可用",
  disabled: "桥接未启用",
} as const;
const clientStatusLabel = {
  running: "已运行",
  not_running: "未运行",
  unknown: "未确认",
} as const;

export function LocalSourceSettingsSection({ load, detect, save }: Props) {
  const [draft, setDraft] = useState<LocalSourceSettings>(defaultSettings);
  const [result, setResult] = useState<LocalSourceSettingsView | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const controller = useRef<AbortController | null>(null);
  const runRef = useRef<((operation: LocalSourceSettingsWriter, saved: boolean) => Promise<void>) | null>(null);
  const busyRef = useRef(false);
  busyRef.current = busy;

  useEffect(() => {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    load(request.signal).then((value) => {
      if (request.signal.aborted) return;
      setResult(value);
      setDraft(value.settings);
    }).catch((error) => {
      if (!request.signal.aborted) setMessage(friendlyError(error, "本地行情设置"));
    });
    return () => request.abort();
  }, [load]);

  const setPaths = (kind: PathKind, values: string[]) => {
    setDraft((current) => ({ ...current, [kind]: values }));
  };

  const updatePath = (kind: PathKind, index: number, value: string) => {
    setPaths(kind, draft[kind].map((item, itemIndex) => itemIndex === index ? value : item));
  };

  const movePath = (kind: PathKind, index: number, offset: -1 | 1) => {
    const nextIndex = index + offset;
    if (nextIndex < 0 || nextIndex >= draft[kind].length) return;
    const values = [...draft[kind]];
    [values[index], values[nextIndex]] = [values[nextIndex], values[index]];
    setPaths(kind, values);
  };

  const normalizedDraft = (): LocalSourceSettings => ({
    ...draft,
    tdx_install_paths: draft.tdx_install_paths.map((path) => path.trim()).filter(Boolean),
    ths_install_paths: draft.ths_install_paths.map((path) => path.trim()).filter(Boolean),
    tdx_rpc_url: draft.tdx_rpc_enabled
      ? (draft.tdx_rpc_url?.trim() || "http://127.0.0.1:17709/")
      : null,
  });

  const rpcStatus = result?.tdx_rpc;

  const run = async (operation: LocalSourceSettingsWriter, saved: boolean) => {
    controller.current?.abort();
    const request = new AbortController();
    controller.current = request;
    setBusy(true);
    setMessage("");
    try {
      const value = await operation(normalizedDraft(), request.signal);
      if (request.signal.aborted) return;
      setResult(value);
      setDraft(value.settings);
      setMessage(saved ? "设置已保存，重新打开软件后生效" : "检测完成，尚未保存修改");
    } catch (error) {
      if (!request.signal.aborted) setMessage(friendlyError(error, "本地行情设置"));
    } finally {
      if (!request.signal.aborted) setBusy(false);
    }
  };
  runRef.current = run;

  const rpcUnavailable = result?.settings.tdx_rpc_enabled === true && result.tdx_rpc.status === "unavailable";
  useEffect(() => {
    if (!rpcUnavailable) return;
    const recheck = () => {
      if (document.visibilityState === "visible" && !busyRef.current) void runRef.current?.(detect, false);
    };
    const timer = window.setInterval(recheck, 60_000);
    document.addEventListener("visibilitychange", recheck);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", recheck);
    };
  }, [detect, rpcUnavailable]);

  return <section className="settings-section local-source-settings-section">
    <div className="settings-heading">
      <div><Database size={20} /><span>
        <h2>本地行情软件</h2>
        <p>本地日线优先；目录按从上到下的顺序使用。</p>
      </span></div>
      <label className="settings-toggle">
        <input
          aria-label="自动发现本机行情软件"
          type="checkbox"
          checked={draft.auto_discovery}
          onChange={(event) => setDraft((current) => ({ ...current, auto_discovery: event.target.checked }))}
        />
        <span>自动发现</span>
      </label>
    </div>

    <div className={`local-source-active ${result?.active_tdx_vipdoc ? "is-ready" : "is-warning"}`}>
      <FolderSearch size={17} />
      <span><small>当前采用的通达信日线目录</small><strong>{result?.active_tdx_vipdoc ?? "未发现有效 vipdoc"}</strong></span>
    </div>

    <PathEditor
      title="通达信及券商通达信目录"
      kind="tdx_install_paths"
      paths={draft.tdx_install_paths}
      update={updatePath}
      move={movePath}
      remove={(kind, index) => setPaths(kind, draft[kind].filter((_item, itemIndex) => itemIndex !== index))}
      add={(kind) => setPaths(kind, [...draft[kind], ""])}
    />
    <PathEditor
      title="同花顺安装目录"
      kind="ths_install_paths"
      paths={draft.ths_install_paths}
      update={updatePath}
      move={movePath}
      remove={(kind, index) => setPaths(kind, draft[kind].filter((_item, itemIndex) => itemIndex !== index))}
      add={(kind) => setPaths(kind, [...draft[kind], ""])}
    />

    {result && result.terminals.length > 0 && <div className="local-terminal-list">
      {result.terminals.map((terminal) => <div className={`local-terminal-row status-${terminal.status}`} key={`${terminal.vendor}-${terminal.install_path}`}>
        <div><strong>{vendorLabel[terminal.vendor]}</strong><small>{originLabel[terminal.origin]}</small></div>
        <span className="local-terminal-path">{terminal.install_path}</span>
        <span className="local-terminal-state">
          {terminal.status === "ready" && <>可用 · 沪市 {terminal.sh_daily_count} · 深市 {terminal.sz_daily_count}
            {terminal.professional_data_status === "detected_only" && <small className="local-terminal-note">专业缓存已发现 {terminal.professional_data_files?.length ?? 0} 项，等待只读桥接读取</small>}
            {terminal.professional_data_status === "ready" && <small className="local-terminal-note">专业只读字段已验证</small>}
          </>}
          {terminal.status === "detected_only" && "已发现，暂未读取本地行情"}
          {terminal.status === "invalid" && "目录无效或缺少数据文件"}
          {terminal.selection_note && <small className="local-terminal-note">{terminal.selection_note}</small>}
        </span>
      </div>)}
    </div>}

    <details className="local-rpc-settings">
      <summary>本地实时桥接（高级）</summary>
      <label className="settings-toggle rpc-toggle">
        <input
          aria-label="启用本地实时桥接"
          type="checkbox"
          checked={draft.tdx_rpc_enabled}
          onChange={(event) => setDraft((current) => ({ ...current, tdx_rpc_enabled: event.target.checked }))}
        />
        <span>启用额外桥接程序</span>
      </label>
      {draft.tdx_rpc_enabled && <label className="local-rpc-address">桥接地址
        <input
          aria-label="本地实时桥接地址"
          value={draft.tdx_rpc_url ?? "http://127.0.0.1:17709/"}
          onChange={(event) => setDraft((current) => ({ ...current, tdx_rpc_url: event.target.value }))}
        />
      </label>}
      <p>这是可选的本机通达信 JSON-RPC 桥接地址，不是 EXE 的界面地址；关闭时不会访问该端口。</p>
      {rpcStatus && <section className={`tdx-rpc-capability-status status-${rpcStatus.status}`} aria-label="通达信只读能力探测">
        <header><span><strong>只读能力探测</strong><small>{rpcStatus.endpoint ?? "未配置桥接地址"}</small></span><b>{rpcStatusLabel[rpcStatus.status]}</b></header>
        <div className="tdx-rpc-runtime-summary" aria-label="通达信运行状态">
          <article data-status={rpcStatus.client.status}>
            {rpcStatus.client.status === "running" ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
            <span><strong>通达信客户端</strong><b>{clientStatusLabel[rpcStatus.client.status]}</b><small>{rpcStatus.client.detail}{rpcStatus.client.executable_path ? ` · ${rpcStatus.client.executable_path}` : ""}</small></span>
          </article>
          <article data-status={rpcStatus.reachable ? "ready" : "unavailable"}>
            {rpcStatus.reachable ? <CheckCircle2 size={15} /> : <AlertCircle size={15} />}
            <span><strong>JSON-RPC 桥</strong><b>{rpcStatus.reachable ? "17709 已监听" : "17709 未监听"}</b><small>{rpcStatus.reachable ? "端口可达，正在探测只读能力" : "端口不可达；客户端运行也不会自动等同于桥接可用"}</small></span>
          </article>
        </div>
        <div className="tdx-rpc-capability-grid">
          <article data-status={rpcStatus.direct_python.status}>
            <AlertCircle size={15} />
            <span><strong>官方 TdxQuant Python 回退</strong><small>{rpcStatus.direct_python.detail}</small></span>
          </article>
          {rpcStatus.capabilities.map((capability) => <article key={capability.key} data-status={capability.status}>
            {capability.status === "ready" ? <CheckCircle2 size={15} /> : capability.status === "disabled" ? <AlertCircle size={15} /> : <AlertCircle size={15} />}
            <span><strong>{capability.label}</strong><small>{capability.status === "disabled" ? "桥接未启用" : capability.detail}</small></span>
          </article>)}
        </div>
        <footer>最近探测：{new Date(rpcStatus.observed_at).toLocaleString("zh-CN", { hour12: false })} · 仅探测只读接口，不连接券商、不下单</footer>
        {rpcUnavailable && <p className="tdx-rpc-auto-retry" role="status">桥接暂不可用；页面保持打开时每 60 秒自动重新检测，恢复后会更新能力状态。</p>}
      </section>}
    </details>

    {message && <p className="local-source-message" role="status">{message}</p>}
    <div className="settings-actions">
      <button type="button" className="settings-action secondary" disabled={busy} onClick={() => void run(detect, false)}><RefreshCw size={15} />重新检测</button>
      <button type="button" className="settings-action" disabled={busy} onClick={() => void run(save, true)}><Save size={15} />验证并保存</button>
    </div>
  </section>;
}

type PathEditorProps = {
  title: string;
  kind: PathKind;
  paths: string[];
  update: (kind: PathKind, index: number, value: string) => void;
  move: (kind: PathKind, index: number, offset: -1 | 1) => void;
  remove: (kind: PathKind, index: number) => void;
  add: (kind: PathKind) => void;
};

function PathEditor({ title, kind, paths, update, move, remove, add }: PathEditorProps) {
  return <div className="local-path-editor">
    <div className="local-path-editor-title"><strong>{title}</strong><button type="button" onClick={() => add(kind)}><Plus size={14} />增加目录</button></div>
    {paths.length === 0 && <p className="settings-empty">未手动配置，使用自动发现结果。</p>}
    {paths.map((path, index) => <div className="local-path-row" key={`${kind}-${index}`}>
      <span className="local-path-priority">{index + 1}</span>
      <input aria-label={`${title} ${index + 1}`} value={path} onChange={(event) => update(kind, index, event.target.value)} placeholder="本机安装目录或 vipdoc 目录" />
      <button type="button" className="icon-action" aria-label={`上移 ${title} ${index + 1}`} title="提高优先级" disabled={index === 0} onClick={() => move(kind, index, -1)}><ArrowUp size={15} /></button>
      <button type="button" className="icon-action" aria-label={`下移 ${title} ${index + 1}`} title="降低优先级" disabled={index === paths.length - 1} onClick={() => move(kind, index, 1)}><ArrowDown size={15} /></button>
      <button type="button" className="icon-action danger" aria-label={`删除 ${title} ${index + 1}`} title="删除目录" onClick={() => remove(kind, index)}><Trash2 size={15} /></button>
    </div>)}
  </div>;
}
