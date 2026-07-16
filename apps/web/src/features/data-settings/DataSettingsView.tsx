import { CheckCircle2, Database, KeyRound, RefreshCw, ShieldAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { friendlyError } from "../../shared/friendlyError";
import { safeStorageGet, safeStorageSet } from "../../shared/safeLocalStorage";
import type { StockPreparation } from "../stock-cockpit/types";
import type {
  AISettingsDeleter, AISettingsLoader, AISettingsSaver, AISettingsView,
  ComplianceAction, ComplianceLoader, ComplianceStatus, DataAsset, PreparationLoader,
} from "./types";

const AUTO_SYNC_KEY = "qibao.autoSync";
export function isAutoSyncEnabled(): boolean { return safeStorageGet(AUTO_SYNC_KEY, "true") !== "false"; }

type Props = {
  loadAI: AISettingsLoader;
  saveAI: AISettingsSaver;
  deleteAI: AISettingsDeleter;
  symbol?: string | null;
  prepare?: PreparationLoader;
  preparation?: StockPreparation | null;
  onAIChanged?: () => void;
  loadCompliance?: ComplianceLoader;
  complianceAction?: ComplianceAction;
};
const sourceNames = { quote: "实时行情", history: "历史走势", finance: "基本面", news: "新闻事件", classification: "行业与板块", fund_flow: "资金流" } as const;
const complianceSourceNames: Record<string, string> = {
  baidu: "百度",
  eastmoney: "东方财富",
  mootdx: "通达信",
  tencent: "腾讯",
};
const complianceAssetNames: Record<DataAsset, string> = {
  a_share: "A 股",
  convertible_bond: "可转债",
};
const complianceFeatureNames: Record<string, string> = {
  a_share_finance: "A 股基本面",
  bond_clauses: "转债条款",
  bond_quotes: "转债行情",
  bond_valuations: "转债估值",
  "history_sync.baidu": "百度历史走势",
  "history_sync.mootdx": "通达信历史走势",
  market_news: "新闻事件",
  realtime_quotes: "实时行情",
  stock_classification: "行业与板块",
  stock_fund_flow: "资金流",
};

export function friendlySourceReason(reason: string | null): string | null {
  if (!reason) return null;
  const value = reason.toLowerCase();
  if (value.includes("lock") && value.includes("timeout")) return "同步任务繁忙，请稍后重试";
  if (value === "news_no_verified_symbol_events") return "暂未找到与这只股票直接相关且已核实的新闻";
  if (value.includes("fund_flow_connection_cooldown")) return "资金流连接刚被上游关闭，已暂缓重试，稍后自动再试";
  if (value.includes("server disconnected") || value.includes("remote end closed")) return "东方财富连接被远端关闭，可能是来源限流；已保留其他可用数据";
  if (value.includes("classification")) return "行业与板块来源暂不可用，请稍后重试";
  if (value.includes("fund_flow") || value.includes("fund-flow") || value.includes("fund flow")) return "资金流来源暂不可用，请稍后重试";
  if (value.includes("not fresh") || value.includes("stale")) return "数据时间较早，正在等待来源更新";
  if (value.includes("history")) return "历史走势暂未补齐";
  if (value.includes("news")) return "新闻来源暂未返回内容";
  if (value.includes("quote")) return "实时行情暂不可用";
  if (value.includes("finance")) return "基本面数据暂未补齐";
  if (value.includes("unavailable")) return "公开来源当前不可用";
  return "来源暂未提供详细原因";
}

export function DataSettingsView({ loadAI, saveAI, deleteAI, symbol, prepare, preparation: initialPreparation, onAIChanged, loadCompliance, complianceAction }: Props) {
  const [settings, setSettings] = useState<AISettingsView | null>(null);
  const [baseUrl, setBaseUrl] = useState(""); const [model, setModel] = useState(""); const [apiKey, setApiKey] = useState("");
  const [autoSync, setAutoSync] = useState(isAutoSyncEnabled); const [preparation, setPreparation] = useState<StockPreparation | null>(null);
  const [prepBusy, setPrepBusy] = useState(false); const [aiBusy, setAiBusy] = useState(false); const [message, setMessage] = useState("");
  const [complianceAsset, setComplianceAsset] = useState<DataAsset>("a_share");
  const [compliance, setCompliance] = useState<ComplianceStatus | null>(null);
  const [complianceBusy, setComplianceBusy] = useState<string | null>(null);
  const [permissionReferences, setPermissionReferences] = useState<Record<string, string>>({});
  const mounted = useRef(true); const aiGeneration = useRef(0); const prepGeneration = useRef(0); const complianceGeneration = useRef(0);
  const aiController = useRef<AbortController | null>(null); const prepController = useRef<AbortController | null>(null);
  const applySettings = (value: AISettingsView) => { setSettings(value); setBaseUrl(value.base_url ?? ""); setModel(value.model ?? ""); setApiKey(""); };

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; aiGeneration.current += 1; prepGeneration.current += 1; aiController.current?.abort(); prepController.current?.abort(); }; }, []);
  useEffect(() => { const request = ++aiGeneration.current; aiController.current?.abort(); setAiBusy(false); const controller = new AbortController(); aiController.current = controller; loadAI(controller.signal).then((value) => { if (mounted.current && request === aiGeneration.current && !controller.signal.aborted) applySettings(value); }).catch((error) => { if (mounted.current && request === aiGeneration.current && !controller.signal.aborted) setMessage(friendlyError(error, "AI 设置")); }); return () => controller.abort(); }, [loadAI, symbol]);
  useEffect(() => { prepGeneration.current += 1; prepController.current?.abort(); setPrepBusy(false); setPreparation(initialPreparation?.symbol === symbol ? (initialPreparation ?? null) : null); setMessage(""); }, [initialPreparation, symbol]);
  useEffect(() => {
    if (!loadCompliance) { setCompliance(null); return; }
    const request = ++complianceGeneration.current;
    setCompliance(null);
    loadCompliance(complianceAsset).then((value) => {
      if (mounted.current && request === complianceGeneration.current) setCompliance(value);
    }).catch((error) => {
      if (mounted.current && request === complianceGeneration.current) setMessage(friendlyError(error, "来源授权"));
    });
  }, [loadCompliance, complianceAsset]);

  const retry = async () => { if (!symbol || !prepare) return; const request = ++prepGeneration.current; prepController.current?.abort(); const controller = new AbortController(); prepController.current = controller; setPrepBusy(true); setMessage(""); try { const value = await prepare(symbol, controller.signal); if (mounted.current && request === prepGeneration.current && !controller.signal.aborted && value.symbol === symbol) setPreparation(value); } catch (error) { if (mounted.current && request === prepGeneration.current && !controller.signal.aborted) setMessage(friendlyError(error, "数据同步")); } finally { if (mounted.current && request === prepGeneration.current) setPrepBusy(false); } };
  const save = async () => { const request = ++aiGeneration.current; aiController.current?.abort(); const controller = new AbortController(); aiController.current = controller; setAiBusy(true); setMessage(""); try { const value = await saveAI({ base_url: baseUrl, model, api_key: apiKey }, controller.signal); if (mounted.current && request === aiGeneration.current && !controller.signal.aborted) { applySettings(value); onAIChanged?.(); } } catch (error) { if (mounted.current && request === aiGeneration.current && !controller.signal.aborted) setMessage(friendlyError(error, "AI 设置")); } finally { if (mounted.current && request === aiGeneration.current) setAiBusy(false); } };
  const clear = async () => { const request = ++aiGeneration.current; aiController.current?.abort(); const controller = new AbortController(); aiController.current = controller; setAiBusy(true); setMessage(""); try { const value = await deleteAI(controller.signal); if (mounted.current && request === aiGeneration.current && !controller.signal.aborted) { applySettings(value); onAIChanged?.(); } } catch (error) { if (mounted.current && request === aiGeneration.current && !controller.signal.aborted) setMessage(friendlyError(error, "AI 设置")); } finally { if (mounted.current && request === aiGeneration.current) setAiBusy(false); } };
  const runComplianceAction = async (source: string, action: "authorize" | "revoke" | "acknowledge") => {
    if (!loadCompliance || !complianceAction) return;
    const key = `${complianceAsset}:${source}:${action}`;
    setComplianceBusy(key); setMessage("");
    try {
      await complianceAction(source, action, permissionReferences[source], complianceAsset);
      const value = await loadCompliance(complianceAsset);
      if (mounted.current) setCompliance(value);
    } catch (error) {
      if (mounted.current) setMessage(friendlyError(error, "来源授权"));
    } finally {
      if (mounted.current) setComplianceBusy(null);
    }
  };

  return <main className="beginner-page data-settings-view"><header><p className="eyebrow">数据设置</p><h1>数据源与 AI</h1><p>自动补齐公开数据，并在本机保存 AI 连接信息。研判规则不由 AI 改写。</p></header>
    {message && <div className="cockpit-error" role="alert"><ShieldAlert size={16} />{message}</div>}
    <section className="settings-section"><div className="settings-heading"><div><Database size={20} /><span><h2>公开数据同步</h2><p>选择股票后检查行情、走势、基本面、行业、资金流和新闻。</p></span></div><label className="toggle-control"><input type="checkbox" checked={autoSync} onChange={(event) => { setAutoSync(event.target.checked); safeStorageSet(AUTO_SYNC_KEY, String(event.target.checked)); }} /><span>自动同步</span></label></div>
      {preparation ? <div className="source-status-list">{preparation.sources.map((source) => <article key={source.name}><div>{source.status === "ready" ? <CheckCircle2 size={17} /> : <ShieldAlert size={17} />}<b>{sourceNames[source.name]}</b><span>{source.status === "ready" ? "可用" : "待补齐"}</span></div><small>最后成功：{source.observed_at ? new Date(source.observed_at).toLocaleString("zh-CN", { hour12: false }) : "暂无成功记录"}</small>{friendlySourceReason(source.reason) && <p>{friendlySourceReason(source.reason)}</p>}</article>)}</div> : <p className="settings-empty">选择一只 A 股后，这里会显示各类数据的最新状态。</p>}
      <button type="button" className="settings-action secondary" disabled={!symbol || !prepare || prepBusy} onClick={() => void retry()}><RefreshCw size={16} />重试当前股票数据</button>
    </section>
    {loadCompliance && complianceAction && <section className="settings-section compliance-settings"><div className="settings-heading"><div><ShieldAlert size={20} /><span><h2>来源授权</h2><p>只在你明确授权并确认声明后，启用对应公开数据源。</p></span></div></div>
      <div className="settings-segmented" role="group" aria-label="资产数据域"><button type="button" aria-pressed={complianceAsset === "a_share"} onClick={() => setComplianceAsset("a_share")}>A 股</button><button type="button" aria-pressed={complianceAsset === "convertible_bond"} onClick={() => setComplianceAsset("convertible_bond")}>可转债</button></div>
      {!compliance && <p className="settings-empty">正在读取{complianceAssetNames[complianceAsset]}来源状态...</p>}
      {compliance && <>
        <p className="compliance-policy-state">{complianceAssetNames[complianceAsset]}：{compliance.policy_state === "current" ? "授权状态正常" : compliance.policy_state === "stale" ? "授权记录需要复核" : "有来源尚未确认"}</p>
        <div className="permission-list">{compliance.sources.map((item) => { const name = String(item.source ?? ""); const displayName = complianceSourceNames[name] ?? "公开数据源"; const state = String(item.permission_state ?? "pending"); const actionKey = (action: "authorize" | "revoke" | "acknowledge") => `${complianceAsset}:${name}:${action}`; return <article className="permission-row beginner-permission-row" key={name}><div><b>{displayName}</b><small>{state === "authorized" ? "已授权" : state === "revoked" ? "已撤销" : "待确认"} · {item.user_acknowledged_at ? "声明已确认" : "声明未确认"}</small><input aria-label={`${displayName} 权限依据`} value={permissionReferences[name] ?? ""} onChange={(event) => setPermissionReferences((current) => ({ ...current, [name]: event.target.value }))} placeholder="例如：个人研究用途" /></div><div className="settings-actions permission-actions"><button type="button" disabled={complianceBusy !== null || !(permissionReferences[name] ?? "").trim()} aria-label={`授权 ${displayName}`} onClick={() => void runComplianceAction(name, "authorize")}>{complianceBusy === actionKey("authorize") ? "处理中..." : "授权"}</button><button type="button" disabled={complianceBusy !== null} aria-label={`确认声明 ${displayName}`} onClick={() => void runComplianceAction(name, "acknowledge")}>{complianceBusy === actionKey("acknowledge") ? "处理中..." : "确认声明"}</button><button type="button" className="settings-action danger" disabled={complianceBusy !== null} aria-label={`撤销授权 ${displayName}`} onClick={() => void runComplianceAction(name, "revoke")}>{complianceBusy === actionKey("revoke") ? "处理中..." : "撤销"}</button></div></article>; })}</div>
        <div className="compliance-feature-list">{compliance.features.map((feature) => <div className={`feature-state ${feature.allowed ? "allowed" : "blocked"}`} key={feature.feature}><b>{complianceFeatureNames[feature.feature] ?? "数据功能"}</b><span>{feature.allowed ? "可用" : "待授权"}</span>{!feature.allowed && feature.blocked_reasons.length > 0 && <small>请先完成来源授权和声明确认</small>}</div>)}</div>
      </>}
    </section>}
    <section className="settings-section"><div className="settings-heading"><div><KeyRound size={20} /><span><h2>AI 补充解释</h2><p>{settings?.configured ? `密钥已保存 · ${settings.api_key_hint ?? "已脱敏"}` : "尚未配置 AI"}</p></span></div></div>
      <div className="settings-form"><label>API 地址<input aria-label="API 地址" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} placeholder="https://api.example.com/v1" /></label><label>模型<input aria-label="模型" value={model} onChange={(event) => setModel(event.target.value)} placeholder="模型名称" /></label><label>新密钥<input aria-label="新密钥" type="password" autoComplete="new-password" value={apiKey} onChange={(event) => setApiKey(event.target.value)} placeholder={settings?.configured ? "留空不会显示旧密钥" : "仅保存在本机"} /></label></div>
      <div className="settings-actions"><button type="button" className="settings-action" disabled={aiBusy || !baseUrl || !model || !apiKey} onClick={() => void save()}>保存 AI 配置</button><button type="button" className="settings-action danger" disabled={aiBusy || !settings?.configured} onClick={() => void clear()}>清除 AI 配置</button></div>
    </section>
  </main>;
}
