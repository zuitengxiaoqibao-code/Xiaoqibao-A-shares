import {
  BellRing,
  Check,
  CheckCircle2,
  Cloud,
  RefreshCw,
  Save,
  ShieldAlert,
  Volume2,
  Wifi,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "../../shared/apiClient";

type Alert = {
  alert_id: string;
  rule_id: string;
  topic?: string | null;
  symbol?: string | null;
  observed_at: string;
  severity?: "critical" | "warning" | "info" | string;
  state?: "active" | "recovered" | string;
  confirmed?: boolean;
  delivery: Record<string, string>;
  delivery_reason?: Record<string, string>;
  snapshot?: Record<string, unknown>;
};
type MonitorTopicHealth = {
  topic: string;
  status: "critical" | "warning" | "ok" | "no_data" | string;
  alert_count: number;
  active_count: number;
  last_alert_at?: string | null;
};
type MonitorSummary = {
  generated_at: string;
  service: { status: string; last_heartbeat_at?: string | null; latency_ms?: number | null };
  rules: { total: number; enabled: number };
  alerts: { total: number; active: number; critical: number; unconfirmed: number; recovered: number };
  delivery: { pending: number; failed: number };
  topics: MonitorTopicHealth[];
  recent_alerts: Alert[];
};
type Rule = { id: string; name: string; topics: string[]; conditions: Record<string, Record<string, number>>; channels?: { in_app?: boolean; tts?: boolean; feishu?: boolean } };
type RuleDraft = { id: string; name: string; topics: string[]; field: string; operator: string; threshold: number; channels: { in_app: boolean; tts: boolean; feishu: boolean } };
type NotificationSettings = { feishu_configured: boolean; feishu_enabled: boolean; webhook_hint: string | null };

const topicOptions = [
  ["market_overview", "市场总览"],
  ["quant_strategy", "量化策略"],
  ["news_events", "新闻事件"],
  ["late_session_candidates", "尾盘选股"],
  ["stock_observation", "个股观察"],
  ["company_research", "公司研究"],
  ["data_sources", "数据源"],
] as const;
const channelNames: Record<string, string> = { in_app: "站内", tts: "语音", feishu: "飞书" };
const statusNames: Record<string, string> = { sent: "已送达", pending: "等待投递", queued: "排队中", playing: "正在播报", failed: "失败", "未配置": "未配置" };
const severityNames: Record<string, string> = { critical: "严重", warning: "警告", info: "提示" };
const topicLabel = (topic?: string | null) => topicOptions.find(([value]) => value === topic)?.[1] ?? topic ?? "实时快照";

const defaultRule = (): RuleDraft => ({ id: `rule-${Date.now()}`, name: "新监控规则", topics: ["quant_strategy"], field: "risk_score", operator: "gte", threshold: 65, channels: { in_app: true, tts: true, feishu: false } });
function ruleDraft(item: Rule): RuleDraft {
  const [field, operators] = Object.entries(item.conditions)[0] ?? ["risk_score", { gte: 65 }];
  const [operator, threshold] = Object.entries(operators)[0] ?? ["gte", 65];
  return { id: item.id, name: item.name, topics: item.topics ?? ["quant_strategy"], field, operator, threshold: Number(threshold), channels: { in_app: item.channels?.in_app !== false, tts: item.channels?.tts !== false, feishu: item.channels?.feishu === true } };
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(path, { ...init, context: "监控中心" })).data;
}

function emptySummary(alerts: Alert[] = []): MonitorSummary {
  return {
    generated_at: new Date().toISOString(),
    service: { status: "unknown", last_heartbeat_at: null, latency_ms: null },
    rules: { total: 0, enabled: 0 },
    alerts: { total: alerts.length, active: alerts.filter((item) => item.state !== "recovered").length, critical: alerts.filter((item) => item.severity === "critical").length, unconfirmed: alerts.filter((item) => item.confirmed !== true).length, recovered: alerts.filter((item) => item.state === "recovered").length },
    delivery: { pending: alerts.flatMap((item) => Object.values(item.delivery)).filter((status) => ["pending", "queued", "playing"].includes(status)).length, failed: alerts.flatMap((item) => Object.values(item.delivery)).filter((status) => status === "failed").length },
    topics: [],
    recent_alerts: alerts,
  };
}

function normalizeSummary(value: MonitorSummary | Alert[] | null | undefined): MonitorSummary {
  if (Array.isArray(value)) return emptySummary(value);
  if (!value || typeof value !== "object") return emptySummary();
  return { ...emptySummary(), ...value, service: { ...emptySummary().service, ...value.service }, rules: { ...emptySummary().rules, ...value.rules }, alerts: { ...emptySummary().alerts, ...value.alerts }, delivery: { ...emptySummary().delivery, ...value.delivery }, topics: value.topics ?? [], recent_alerts: value.recent_alerts ?? [] };
}

function deliveryLabel(channel: string, status: string): string { return `${channelNames[channel] ?? channel}${statusNames[status] ?? status}`; }
function statusLabel(status: string): string { return { healthy: "运行正常", degraded: "部分异常", unknown: "等待数据", critical: "严重", warning: "警告", ok: "正常", no_data: "暂无数据" }[status] ?? status; }

export function MonitorCenterView() {
  const [summary, setSummary] = useState<MonitorSummary | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [rule, setRule] = useState<RuleDraft>(defaultRule);
  const [webhook, setWebhook] = useState("");
  const [feishuEnabled, setFeishuEnabled] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefreshError, setLastRefreshError] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [stateFilter, setStateFilter] = useState("all");
  const [topicFilter, setTopicFilter] = useState("all");
  const [symbolFilter, setSymbolFilter] = useState("");
  const [saving, setSaving] = useState(false);
  const mounted = useRef(true);
  const summaryRef = useRef<MonitorSummary | null>(null);
  const requestGeneration = useRef(0);

  const load = useCallback(async () => {
    const generation = ++requestGeneration.current;
    setRefreshing(true);
    setError("");
    try {
      const [summaryPayload, nextAlerts, nextRules, nextSettings] = await Promise.all([
        jsonFetch<MonitorSummary | Alert[]>("/api/v1/monitor-center/summary"),
        jsonFetch<Alert[]>("/api/v1/monitor-center/alerts?limit=30"),
        jsonFetch<Rule[]>("/api/v1/monitor-center/rules"),
        jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings"),
      ]);
      if (!mounted.current || generation !== requestGeneration.current) return;
      const normalized = normalizeSummary(summaryPayload);
      const mergedAlerts = normalized.recent_alerts.length > 0 ? normalized.recent_alerts : nextAlerts;
      const nextSummary = normalized.recent_alerts.length > 0 ? normalized : { ...normalized, recent_alerts: nextAlerts, alerts: emptySummary(nextAlerts).alerts };
      summaryRef.current = nextSummary;
      setSummary(nextSummary);
      setAlerts(mergedAlerts);
      setRules(nextRules);
      setSettings(nextSettings);
      setFeishuEnabled(nextSettings.feishu_enabled);
      setLastRefreshError("");
    } catch (reason) {
      if (!mounted.current || generation !== requestGeneration.current) return;
      const message = reason instanceof Error ? reason.message : "监控中心暂不可用";
      setLastRefreshError(message);
      setError(summaryRef.current ? "最新监控摘要刷新失败，当前保留上次有效数据。" : message);
    } finally {
      if (mounted.current && generation === requestGeneration.current) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    void load();
    const refresh = () => { if (document.visibilityState === "visible") void load(); };
    const timer = window.setInterval(refresh, 15_000);
    document.addEventListener("visibilitychange", refresh);
    return () => { mounted.current = false; window.clearInterval(timer); document.removeEventListener("visibilitychange", refresh); };
  }, [load]);

  const filteredAlerts = useMemo(() => alerts.filter((alert) => {
    if (severityFilter !== "all" && alert.severity !== severityFilter) return false;
    if (stateFilter !== "all" && (alert.state ?? "active") !== stateFilter) return false;
    if (topicFilter !== "all" && alert.topic !== topicFilter) return false;
    if (symbolFilter.trim() && !`${alert.symbol ?? ""} ${alert.rule_id}`.toLowerCase().includes(symbolFilter.trim().toLowerCase())) return false;
    return true;
  }), [alerts, severityFilter, stateFilter, topicFilter, symbolFilter]);

  const confirmAlert = async (alertId: string) => {
    try {
      await jsonFetch<Alert>(`/api/v1/monitor-center/alerts/${encodeURIComponent(alertId)}/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ confirmed_by: "用户" }) });
      setNotice("告警已确认");
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "告警确认失败"); }
  };
  const retryDelivery = async (alertId: string, channel: string) => {
    try {
      await jsonFetch(`/api/v1/monitor-center/alerts/${encodeURIComponent(alertId)}/delivery/retry`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ channel }) });
      setNotice(`${channelNames[channel] ?? channel}投递已重新排队`);
      await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "投递重试失败"); }
  };
  const saveRule = async () => {
    setSaving(true); setError("");
    try {
      await jsonFetch<Rule>("/api/v1/monitor-center/rules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: rule.id, name: rule.name, topics: rule.topics, conditions: { [rule.field]: { [rule.operator]: rule.threshold } }, channels: rule.channels }) });
      setNotice("监控规则已保存，下一次实时快照将按新规则评估"); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "监控规则保存失败"); }
    finally { setSaving(false); }
  };
  const testFeishu = async () => { setNotice(""); try { const result = await jsonFetch<{ status: string; message: string }>("/api/v1/monitor-center/notification-settings/test", { method: "POST" }); setNotice(result.message); } catch (reason) { setError(reason instanceof Error ? reason.message : "飞书测试发送失败"); } };
  const saveFeishu = async () => {
    if (feishuEnabled && !webhook.trim() && !settings?.feishu_configured) { setError("启用飞书前必须填写飞书 Webhook"); return; }
    try {
      if (!webhook.trim() && settings?.feishu_configured && !feishuEnabled) setSettings(await jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings", { method: "DELETE" }));
      else setSettings(await jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ feishu_enabled: feishuEnabled, feishu_webhook: webhook.trim() || null }) }));
      setWebhook(""); setNotice("飞书通知配置已安全保存");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "飞书配置保存失败"); }
  };

  const current = summary ?? emptySummary(alerts);
  const sourceIssueCount = current.topics.filter((item) => item.status === "critical" || item.status === "warning" || item.status === "no_data").length;
  return <main className="terminal-page beginner-page monitor-center-view">
    <header className="monitor-header"><div><p className="eyebrow">REALTIME MONITOR</p><h1>监控中心</h1><p>统一查看规则、数据主题、告警生命周期和投递健康。</p></div><button type="button" className="settings-action" onClick={() => void load()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? "monitor-spin" : ""} />{refreshing ? "刷新中" : "刷新监控状态"}</button></header>
    {error && <p className="cockpit-error" role="alert"><ShieldAlert size={15} />{error}</p>}
    {notice && <p className="monitor-notice" role="status"><CheckCircle2 size={15} />{notice}</p>}
    {lastRefreshError && !error && <p className="monitor-stale-note" role="status">上次有效数据仍在展示，最新刷新：{lastRefreshError}</p>}
    <section className="monitor-status-strip"><span className={`monitor-live-dot ${current.service.status === "healthy" ? "is-live" : ""}`} /><strong>监控服务：{statusLabel(current.service.status)}</strong><span>规则 {current.rules.enabled}/{current.rules.total} 启用</span><span>最近心跳 {current.service.last_heartbeat_at ? new Date(current.service.last_heartbeat_at).toLocaleTimeString("zh-CN", { hour12: false }) : "暂无"}</span><span>总线延迟 {current.service.latency_ms == null ? "暂无" : `${Math.round(current.service.latency_ms)} ms`}</span></section>
    <section className="monitor-kpi-grid" aria-label="监控摘要">
      <article className="monitor-kpi critical"><span>严重告警</span><strong>{current.alerts.critical}</strong><small>当前仍处于严重状态</small></article>
      <article className="monitor-kpi warning"><span>待确认</span><strong>{current.alerts.unconfirmed}</strong><small>需要人工确认的活跃告警</small></article>
      <article className="monitor-kpi delivery"><span>投递失败</span><strong>{current.delivery.failed}</strong><small>可在告警记录中重试</small></article>
      <article className="monitor-kpi source"><span>数据源异常</span><strong>{sourceIssueCount}</strong><small>主题暂无数据或处于风险</small></article>
    </section>
    <section className="settings-section monitor-topic-section"><div className="settings-heading"><div><Wifi size={20} /><span><h2>主题健康</h2><p>按真实告警与规则快照聚合，不生成模拟状态。</p></span></div></div>{current.topics.length === 0 ? <p className="data-import-empty">暂未收到主题快照，等待实时总线数据。</p> : <div className="monitor-topic-grid">{current.topics.map((item) => <article className={`monitor-topic-card ${item.status}`} key={item.topic}><div><strong>{topicLabel(item.topic)}</strong><span className={`status-chip ${item.status === "critical" ? "bad" : item.status === "warning" ? "warn" : item.status === "ok" ? "ok" : "muted"}`}>{statusLabel(item.status)}</span></div><b>{item.active_count}</b><small>活跃告警 · 累计 {item.alert_count} 条</small>{item.last_alert_at && <time>{new Date(item.last_alert_at).toLocaleString("zh-CN", { hour12: false })}</time>}</article>)}</div>}</section>
    <section className="settings-section monitor-alert-section"><div className="settings-heading"><div><BellRing size={20} /><span><h2>告警时间线</h2><p>支持按主题、严重级别、生命周期和标的快速定位。</p></span></div></div><div className="monitor-alert-filters"><label>主题<select aria-label="主题筛选" value={topicFilter} onChange={(event) => setTopicFilter(event.target.value)}><option value="all">全部主题</option>{topicOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>严重级别<select aria-label="严重级别筛选" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}><option value="all">全部级别</option><option value="critical">严重</option><option value="warning">警告</option><option value="info">提示</option></select></label><label>状态<select aria-label="告警状态筛选" value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}><option value="all">全部状态</option><option value="active">活跃</option><option value="recovered">已恢复</option></select></label><label>标的/规则<input aria-label="标的或规则筛选" value={symbolFilter} onChange={(event) => setSymbolFilter(event.target.value)} placeholder="代码或规则名称" /></label></div>{filteredAlerts.length === 0 ? <p className="data-import-empty">当前筛选条件下暂无告警。</p> : <div className="monitor-alert-timeline">{filteredAlerts.map((alert) => <article className={`monitor-alert-card ${alert.severity ?? "warning"} ${alert.state ?? "active"}`} key={alert.alert_id}><div className="monitor-alert-marker" /><div className="monitor-alert-main"><div className="monitor-alert-title"><strong>{alert.symbol || "全市场"}</strong><span className="monitor-alert-rule">{alert.rule_id}</span><span className={`status-chip ${alert.severity === "critical" ? "bad" : alert.severity === "info" ? "muted" : "warn"}`}>{severityNames[alert.severity ?? "warning"] ?? alert.severity ?? "警告"}</span><span className={`status-chip ${alert.state === "recovered" ? "ok" : "muted"}`}>{alert.state === "recovered" ? "已恢复" : "活跃"}</span></div><small>{topicLabel(alert.topic)} · {new Date(alert.observed_at).toLocaleString("zh-CN", { hour12: false })}</small><div className="monitor-delivery-tags">{Object.entries(alert.delivery).map(([key, value]) => <span className="monitor-delivery-item" key={key}><span className={`status-chip ${value === "sent" ? "ok" : value === "failed" ? "bad" : "muted"}`}>{deliveryLabel(key, value)}</span>{value === "failed" && <button type="button" className="monitor-retry-button" onClick={() => void retryDelivery(alert.alert_id, key)}>重试</button>}</span>)}</div>{alert.delivery_reason && Object.keys(alert.delivery_reason).length > 0 && <p className="monitor-alert-reason">{Object.entries(alert.delivery_reason).map(([key, value]) => `${channelNames[key] ?? key}：${value}`).join("；")}</p>}</div>{alert.state !== "recovered" && alert.confirmed !== true && <button type="button" className="monitor-confirm-button" onClick={() => void confirmAlert(alert.alert_id)}><Check size={15} />确认告警</button>}</article>)}</div>}</section>
    <div className="monitor-workbench-grid"><section className="settings-section monitor-rule-panel"><div className="settings-heading"><div><BellRing size={20} /><span><h2>规则配置</h2><p>每条规则绑定主题、指标阈值和独立投递通道。</p></span></div></div><div className="monitor-rule-form"><label>规则名称<input aria-label="规则名称" value={rule.name} onChange={(event) => setRule({ ...rule, name: event.target.value })} /></label><label>数据主题<select aria-label="数据主题" value={rule.topics[0]} onChange={(event) => setRule({ ...rule, topics: [event.target.value] })}>{topicOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>字段路径<input aria-label="字段路径" value={rule.field} onChange={(event) => setRule({ ...rule, field: event.target.value })} placeholder="例如 regime.risk_score" /></label><label>比较符<select aria-label="比较符" value={rule.operator} onChange={(event) => setRule({ ...rule, operator: event.target.value })}><option value="gte">大于等于</option><option value="lte">小于等于</option><option value="gt">大于</option><option value="lt">小于</option></select></label><label>阈值<input aria-label="阈值" type="number" value={rule.threshold} onChange={(event) => setRule({ ...rule, threshold: Number(event.target.value) })} /></label></div><div className="monitor-channel-toggles"><span>投递通道</span>{(["in_app", "tts", "feishu"] as const).map((channel) => <label key={channel}><input type="checkbox" checked={rule.channels[channel]} onChange={(event) => setRule({ ...rule, channels: { ...rule.channels, [channel]: event.target.checked } })} />{channel === "tts" ? <Volume2 size={14} /> : channel === "feishu" ? <Cloud size={14} /> : <BellRing size={14} />}{channelNames[channel]}</label>)}</div><button type="button" className="settings-action" disabled={saving || !rule.name.trim()} onClick={() => void saveRule()}><Save size={15} />保存监控规则</button>{rules.length > 0 && <div className="monitor-rule-list">{rules.map((item) => { const draft = ruleDraft(item); return <button type="button" key={item.id} onClick={() => setRule(draft)}><strong>{item.name}</strong><small>{draft.topics.map((topic) => topicLabel(topic)).join("、")} · {draft.field} {draft.operator} {draft.threshold}</small></button>; })}</div>}</section><section className="settings-section monitor-channel-panel"><div className="settings-heading"><div><Cloud size={20} /><span><h2>通知通道</h2><p>Webhook 使用本机凭据保护保存，页面只回显脱敏状态。</p></span></div></div><div className="monitor-channel-status"><article><BellRing size={17} /><strong>站内告警</strong><span className="status-chip ok">已启用</span></article><article><Volume2 size={17} /><strong>Edge TTS</strong><span className="status-chip ok">已接入</span></article><article><Cloud size={17} /><strong>飞书</strong><span className={`status-chip ${settings?.feishu_configured && settings.feishu_enabled ? "ok" : "muted"}`}>{settings?.feishu_configured && settings.feishu_enabled ? `已配置 · ${settings.webhook_hint}` : "未配置"}</span></article></div><div className="monitor-feishu-form"><label><input type="checkbox" checked={feishuEnabled} onChange={(event) => setFeishuEnabled(event.target.checked)} />启用飞书机器人</label><label>飞书 Webhook<input type="password" value={webhook} onChange={(event) => setWebhook(event.target.value)} placeholder={settings?.feishu_configured ? "已安全保存，重新填写可替换" : "https://open.feishu.cn/open-apis/bot/v2/hook/..."} autoComplete="off" /></label><div><button type="button" className="settings-action" onClick={() => void saveFeishu()}><Save size={15} />保存配置</button><button type="button" className="settings-action secondary" disabled={!settings?.feishu_configured || !settings.feishu_enabled} onClick={() => void testFeishu()}>测试发送</button></div></div></section></div>
  </main>;
}
