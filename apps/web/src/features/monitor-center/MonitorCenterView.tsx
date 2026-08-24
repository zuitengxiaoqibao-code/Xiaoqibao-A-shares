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
type RuleCondition = { field: string; op: string; value: number | string };
type RuleDraft = { id: string; name: string; topics: string[]; logic: "all" | "any" | "n_of"; n: number; conditions: RuleCondition[]; confirm_count: number; confirm_window_seconds: number; cooldown_seconds: number; freshness_seconds: number; require_freshness: boolean; severity: "critical" | "warning" | "info"; recovery_enabled: boolean; recovery: RuleCondition[]; channels: { in_app: boolean; tts: boolean; feishu: boolean }; field: string; operator: string; threshold: number };
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
const metricOptions: Array<readonly [string, string]> = [
  ["risk_score", "风险分"],
  ["emotion_score", "情绪分"],
  ["heat_score", "热度分"],
  ["rotation_score", "轮动分"],
  ["strategy_score", "策略评分"],
  ["buy_score", "买入评分"],
  ["change_pct", "涨跌幅"],
  ["latest_price", "最新价"],
  ["close_pos", "收盘位置"],
  ["volume_ratio", "量比"],
  ["turnover_rate", "换手率"],
  ["amount", "成交额"],
  ["up_ratio", "上涨率"],
  ["limit_up_ratio", "涨停率"],
  ["limit_down_ratio", "跌停率"],
  ["strong_close_ratio", "强势收盘比例"],
  ["weak_close_ratio", "弱势收盘比例"],
  ["panic_ratio", "恐慌率"],
  ["amp_ratio", "振幅比例"],
  ["net_positive_ratio", "资金净流入比例"],
  ["rr_ratio", "盈亏比"],
];
const channelNames: Record<string, string> = { in_app: "站内", tts: "语音", feishu: "飞书" };
const statusNames: Record<string, string> = { sent: "已送达", pending: "等待投递", queued: "排队中", playing: "正在播报", failed: "失败", "未配置": "未配置" };
const severityNames: Record<string, string> = { critical: "严重", warning: "警告", info: "提示" };
const topicLabel = (topic?: string | null) => topicOptions.find(([value]) => value === topic)?.[1] ?? topic ?? "实时快照";
const metricLabel = (field?: string | null) => metricOptions.find(([value]) => value === field)?.[1] ?? "自定义指标";
const metricOptionsFor = (field: string) => metricOptions.some(([value]) => value === field)
  ? metricOptions
  : [[field, "自定义指标（已保存）"] as const, ...metricOptions];
const operatorLabel = (operator?: string | null) => ({ eq: "等于", gt: "大于", gte: "大于等于", lt: "小于", lte: "小于等于" }[operator ?? ""] ?? "比较");

const defaultRule = (): RuleDraft => ({ id: `rule-${Date.now()}`, name: "新监控规则", topics: ["quant_strategy"], logic: "all", n: 1, conditions: [{ field: "risk_score", op: "gte", value: 65 }], confirm_count: 1, confirm_window_seconds: 10, cooldown_seconds: 60, freshness_seconds: 120, require_freshness: false, severity: "warning", recovery_enabled: false, recovery: [{ field: "risk_score", op: "lte", value: 50 }], channels: { in_app: true, tts: true, feishu: false }, field: "risk_score", operator: "gte", threshold: 65 });
function ruleDraft(item: Rule): RuleDraft {
  const entries = Array.isArray((item as Rule & { conditions?: unknown }).conditions)
    ? (item as Rule & { conditions: RuleCondition[] }).conditions
    : Object.entries(item.conditions ?? {}).map(([field, operators]) => { const [op, value] = Object.entries(operators)[0] ?? ["gte", 65]; return { field, op, value }; });
  const source = item as Rule & Partial<RuleDraft>;
  const first = entries[0] ?? { field: "risk_score", op: "gte", value: 65 };
  const recoverySource = source.recovery as unknown;
  const recoveryConditions = Array.isArray(recoverySource)
    ? recoverySource as RuleCondition[]
    : recoverySource && typeof recoverySource === "object" && "conditions" in recoverySource
      ? (Array.isArray((recoverySource as { conditions?: unknown }).conditions) ? (recoverySource as { conditions: RuleCondition[] }).conditions : Object.entries((recoverySource as { conditions: Record<string, Record<string, number>> }).conditions ?? {}).map(([field, operators]) => { const [op, value] = Object.entries(operators)[0] ?? ["lte", 50]; return { field, op, value }; }))
      : defaultRule().recovery;
  return { ...defaultRule(), id: item.id, name: item.name, topics: item.topics ?? ["quant_strategy"], logic: source.logic ?? "all", n: Number(source.n ?? 1), conditions: entries.length > 0 ? entries : defaultRule().conditions, confirm_count: Number(source.confirm_count ?? 1), confirm_window_seconds: Number(source.confirm_window_seconds ?? 10), cooldown_seconds: Number(source.cooldown_seconds ?? 60), freshness_seconds: Number(source.freshness_seconds ?? 120), require_freshness: source.require_freshness === true, severity: source.severity ?? "warning", recovery_enabled: Boolean(source.recovery), recovery: recoveryConditions.length > 0 ? recoveryConditions : defaultRule().recovery, field: first.field, operator: first.op, threshold: Number(first.value), channels: { in_app: item.channels?.in_app !== false, tts: item.channels?.tts !== false, feishu: item.channels?.feishu === true } };
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
  const updateCondition = (index: number, patch: Partial<RuleCondition>) => setRule((current) => ({ ...current, conditions: current.conditions.map((condition, conditionIndex) => conditionIndex === index ? { ...condition, ...patch } : condition) }));
  const addCondition = () => setRule((current) => ({ ...current, conditions: [...current.conditions, { field: "change_pct", op: "gte", value: 2 }] }));
  const removeCondition = (index: number) => setRule((current) => current.conditions.length <= 1 ? current : ({ ...current, conditions: current.conditions.filter((_, conditionIndex) => conditionIndex !== index) }));
  const rulePayload = () => {
    const conditions = rule.conditions.map((condition, index) => index === 0 ? { field: rule.field, op: rule.operator, value: rule.threshold } : condition);
    const conditionPayload = conditions.length === 1 && rule.logic === "all"
      ? { [conditions[0].field]: { [conditions[0].op]: conditions[0].value } }
      : conditions;
    return { id: rule.id, name: rule.name, topics: rule.topics, logic: rule.logic, n: rule.logic === "n_of" ? rule.n : undefined, conditions: conditionPayload, confirm_count: rule.confirm_count, confirm_window_seconds: rule.confirm_window_seconds, cooldown_seconds: rule.cooldown_seconds, freshness_seconds: rule.freshness_seconds, require_freshness: rule.require_freshness, severity: rule.severity, recovery: rule.recovery_enabled ? { enabled: true, logic: "all", conditions: rule.recovery } : undefined, channels: rule.channels };
  };
  const saveRule = async () => {
    setSaving(true); setError("");
    try {
      await jsonFetch<Rule>("/api/v1/monitor-center/rules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(rulePayload()) });
      setNotice("监控规则已保存，下一次实时快照将按新规则评估"); await load();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "监控规则保存失败"); }
    finally { setSaving(false); }
  };
  const testFeishu = async () => { setNotice(""); try { const result = await jsonFetch<{ status: string; message: string }>("/api/v1/monitor-center/notification-settings/test", { method: "POST" }); setNotice(result.message); } catch (reason) { setError(reason instanceof Error ? reason.message : "飞书测试发送失败"); } };
  const saveFeishu = async () => {
    if (feishuEnabled && !webhook.trim() && !settings?.feishu_configured) { setError("启用飞书前必须填写飞书机器人地址"); return; }
    try {
      if (!webhook.trim() && settings?.feishu_configured && !feishuEnabled) setSettings(await jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings", { method: "DELETE" }));
      else setSettings(await jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ feishu_enabled: feishuEnabled, feishu_webhook: webhook.trim() || null }) }));
      setWebhook(""); setNotice("飞书通知配置已安全保存");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "飞书配置保存失败"); }
  };

  const current = summary ?? emptySummary(alerts);
  const sourceIssueCount = current.topics.filter((item) => item.status === "critical" || item.status === "warning" || item.status === "no_data").length;
  const advancedRuleBuilder = <section className="settings-section monitor-rule-builder"><div className="settings-heading"><div><BellRing size={20} /><span><h2>高级规则构建器</h2><p>组合条件、连续确认、数据新鲜度和恢复条件均由后端实时校验。</p></span></div><span className="status-chip ok">高级规则</span></div><div className="monitor-rule-builder-grid"><label>逻辑模式<select aria-label="条件逻辑" value={rule.logic} onChange={(event) => setRule({ ...rule, logic: event.target.value as RuleDraft["logic"] })}><option value="all">全部条件满足</option><option value="any">任意条件满足</option><option value="n_of">满足指定数量</option></select></label>{rule.logic === "n_of" && <label>满足数量<input aria-label="满足条件数量" type="number" min="1" value={rule.n} onChange={(event) => setRule({ ...rule, n: Math.max(1, Number(event.target.value)) })} /></label>}<label>告警级别<select aria-label="规则告警级别" value={rule.severity} onChange={(event) => setRule({ ...rule, severity: event.target.value as RuleDraft["severity"] })}><option value="info">提示</option><option value="warning">警告</option><option value="critical">严重</option></select></label><label>连续确认次数<input aria-label="连续确认次数" type="number" min="1" value={rule.confirm_count} onChange={(event) => setRule({ ...rule, confirm_count: Math.max(1, Number(event.target.value)) })} /></label><label>确认窗口（秒）<input aria-label="确认窗口秒数" type="number" min="1" value={rule.confirm_window_seconds} onChange={(event) => setRule({ ...rule, confirm_window_seconds: Math.max(1, Number(event.target.value)) })} /></label><label>冷却时间（秒）<input aria-label="冷却时间秒数" type="number" min="0" value={rule.cooldown_seconds} onChange={(event) => setRule({ ...rule, cooldown_seconds: Math.max(0, Number(event.target.value)) })} /></label><label>数据新鲜度（秒）<input aria-label="数据新鲜度秒数" type="number" min="1" value={rule.freshness_seconds} onChange={(event) => setRule({ ...rule, freshness_seconds: Math.max(1, Number(event.target.value)) })} /></label><label className="monitor-rule-checkbox"><input type="checkbox" checked={rule.require_freshness} onChange={(event) => setRule({ ...rule, require_freshness: event.target.checked })} />数据过期时禁止触发</label></div><div className="monitor-condition-list"><div className="monitor-condition-list-header"><strong>触发条件</strong><button type="button" className="settings-action secondary" onClick={addCondition}>增加条件</button></div>{rule.conditions.map((condition, index) => { const field = index === 0 ? rule.field : condition.field; return <div className="monitor-condition-row" key={`${index}-${condition.field}`}><label>监控指标<select aria-label={index === 0 ? "监控指标" : `监控指标 ${index + 1}`} value={field} onChange={(event) => index === 0 ? setRule({ ...rule, field: event.target.value, conditions: rule.conditions.map((item, itemIndex) => itemIndex === 0 ? { ...item, field: event.target.value } : item) }) : updateCondition(index, { field: event.target.value })}>{metricOptionsFor(field).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>比较方式<select aria-label={index === 0 ? "高级比较方式" : `高级比较方式 ${index + 1}`} value={index === 0 ? rule.operator : condition.op} onChange={(event) => index === 0 ? setRule({ ...rule, operator: event.target.value, conditions: rule.conditions.map((item, itemIndex) => itemIndex === 0 ? { ...item, op: event.target.value } : item) }) : updateCondition(index, { op: event.target.value })}><option value="gte">大于等于</option><option value="lte">小于等于</option><option value="gt">大于</option><option value="lt">小于</option><option value="eq">等于</option></select></label><label>阈值<input aria-label={index === 0 ? "高级阈值" : `高级阈值 ${index + 1}`} type="number" value={index === 0 ? rule.threshold : Number(condition.value)} onChange={(event) => index === 0 ? setRule({ ...rule, threshold: Number(event.target.value), conditions: rule.conditions.map((item, itemIndex) => itemIndex === 0 ? { ...item, value: Number(event.target.value) } : item) }) : updateCondition(index, { value: Number(event.target.value) })} /></label>{rule.conditions.length > 1 && <button type="button" className="monitor-condition-remove" aria-label={`删除条件 ${index + 1}`} onClick={() => removeCondition(index)}>删除</button>}</div>; })}</div><label className="monitor-rule-checkbox"><input type="checkbox" checked={rule.recovery_enabled} onChange={(event) => setRule({ ...rule, recovery_enabled: event.target.checked })} />启用自定义恢复条件</label>{rule.recovery_enabled && <div className="monitor-recovery-row"><label>恢复指标<select aria-label="恢复指标" value={rule.recovery[0].field} onChange={(event) => setRule({ ...rule, recovery: [{ ...rule.recovery[0], field: event.target.value }] })}>{metricOptionsFor(rule.recovery[0].field).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>恢复比较方式<select aria-label="恢复比较方式" value={rule.recovery[0].op} onChange={(event) => setRule({ ...rule, recovery: [{ ...rule.recovery[0], op: event.target.value }] })}><option value="lte">小于等于</option><option value="lt">小于</option><option value="eq">等于</option></select></label><label>恢复阈值<input aria-label="恢复阈值" type="number" value={Number(rule.recovery[0].value)} onChange={(event) => setRule({ ...rule, recovery: [{ ...rule.recovery[0], value: Number(event.target.value) }] })} /></label></div>}<details className="monitor-rule-preview"><summary>查看高级数据预览</summary><pre aria-label="高级数据预览">{JSON.stringify(rulePayload(), null, 2)}</pre></details><button type="button" className="settings-action" disabled={saving || !rule.name.trim()} onClick={() => void saveRule()}><Save size={15} />保存高级规则</button></section>;
  return <main className="terminal-page beginner-page monitor-center-view">
    <header className="monitor-header"><div><p className="eyebrow">实时监控</p><h1>监控中心</h1><p>统一查看规则、数据主题、告警生命周期和投递健康。</p></div><button type="button" className="settings-action" onClick={() => void load()} disabled={refreshing}><RefreshCw size={15} className={refreshing ? "monitor-spin" : ""} />{refreshing ? "刷新中" : "刷新监控状态"}</button></header>
    {error && <p className="cockpit-error" role="alert"><ShieldAlert size={15} />{error}</p>}
    {notice && <p className="monitor-notice" role="status"><CheckCircle2 size={15} />{notice}</p>}
    {lastRefreshError && !error && <p className="monitor-stale-note" role="status">上次有效数据仍在展示，最新刷新：{lastRefreshError}</p>}
    {advancedRuleBuilder}
    <section className="monitor-status-strip"><span className={`monitor-live-dot ${current.service.status === "healthy" ? "is-live" : ""}`} /><strong>监控服务：{statusLabel(current.service.status)}</strong><span>规则 {current.rules.enabled}/{current.rules.total} 启用</span><span>最近心跳 {current.service.last_heartbeat_at ? new Date(current.service.last_heartbeat_at).toLocaleTimeString("zh-CN", { hour12: false }) : "暂无"}</span><span>总线延迟 {current.service.latency_ms == null ? "暂无" : `${Math.round(current.service.latency_ms)} ms`}</span></section>
    <section className="monitor-kpi-grid" aria-label="监控摘要">
      <article className="monitor-kpi critical"><span>严重告警</span><strong>{current.alerts.critical}</strong><small>当前仍处于严重状态</small></article>
      <article className="monitor-kpi warning"><span>待确认</span><strong>{current.alerts.unconfirmed}</strong><small>需要人工确认的活跃告警</small></article>
      <article className="monitor-kpi delivery"><span>投递失败</span><strong>{current.delivery.failed}</strong><small>可在告警记录中重试</small></article>
      <article className="monitor-kpi source"><span>数据源异常</span><strong>{sourceIssueCount}</strong><small>主题暂无数据或处于风险</small></article>
    </section>
    <section className="settings-section monitor-topic-section"><div className="settings-heading"><div><Wifi size={20} /><span><h2>主题健康</h2><p>按真实告警与规则快照聚合，不生成模拟状态。</p></span></div></div>{current.topics.length === 0 ? <p className="data-import-empty">暂未收到主题快照，等待实时总线数据。</p> : <div className="monitor-topic-grid">{current.topics.map((item) => <article className={`monitor-topic-card ${item.status}`} key={item.topic}><div><strong>{topicLabel(item.topic)}</strong><span className={`status-chip ${item.status === "critical" ? "bad" : item.status === "warning" ? "warn" : item.status === "ok" ? "ok" : "muted"}`}>{statusLabel(item.status)}</span></div><b>{item.active_count}</b><small>活跃告警 · 累计 {item.alert_count} 条</small>{item.last_alert_at && <time>{new Date(item.last_alert_at).toLocaleString("zh-CN", { hour12: false })}</time>}</article>)}</div>}</section>
    <section className="settings-section monitor-alert-section"><div className="settings-heading"><div><BellRing size={20} /><span><h2>告警时间线</h2><p>支持按主题、严重级别、生命周期和标的快速定位。</p></span></div></div><div className="monitor-alert-filters"><label>主题<select aria-label="主题筛选" value={topicFilter} onChange={(event) => setTopicFilter(event.target.value)}><option value="all">全部主题</option>{topicOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>严重级别<select aria-label="严重级别筛选" value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}><option value="all">全部级别</option><option value="critical">严重</option><option value="warning">警告</option><option value="info">提示</option></select></label><label>状态<select aria-label="告警状态筛选" value={stateFilter} onChange={(event) => setStateFilter(event.target.value)}><option value="all">全部状态</option><option value="active">活跃</option><option value="recovered">已恢复</option></select></label><label>标的/规则<input aria-label="标的或规则筛选" value={symbolFilter} onChange={(event) => setSymbolFilter(event.target.value)} placeholder="代码或规则名称" /></label></div>{filteredAlerts.length === 0 ? <p className="data-import-empty">当前筛选条件下暂无告警。</p> : <div className="monitor-alert-timeline">{filteredAlerts.map((alert) => <article className={`monitor-alert-card ${alert.severity ?? "warning"} ${alert.state ?? "active"}`} key={alert.alert_id}><div className="monitor-alert-marker" /><div className="monitor-alert-main"><div className="monitor-alert-title"><strong>{alert.symbol || "全市场"}</strong><span className="monitor-alert-rule">{alert.rule_id}</span><span className={`status-chip ${alert.severity === "critical" ? "bad" : alert.severity === "info" ? "muted" : "warn"}`}>{severityNames[alert.severity ?? "warning"] ?? alert.severity ?? "警告"}</span><span className={`status-chip ${alert.state === "recovered" ? "ok" : "muted"}`}>{alert.state === "recovered" ? "已恢复" : "活跃"}</span></div><small>{topicLabel(alert.topic)} · {new Date(alert.observed_at).toLocaleString("zh-CN", { hour12: false })}</small><div className="monitor-delivery-tags">{Object.entries(alert.delivery).map(([key, value]) => <span className="monitor-delivery-item" key={key}><span className={`status-chip ${value === "sent" ? "ok" : value === "failed" ? "bad" : "muted"}`}>{deliveryLabel(key, value)}</span>{value === "failed" && <button type="button" className="monitor-retry-button" onClick={() => void retryDelivery(alert.alert_id, key)}>重试</button>}</span>)}</div>{alert.delivery_reason && Object.keys(alert.delivery_reason).length > 0 && <p className="monitor-alert-reason">{Object.entries(alert.delivery_reason).map(([key, value]) => `${channelNames[key] ?? key}：${value}`).join("；")}</p>}</div>{alert.state !== "recovered" && alert.confirmed !== true && <button type="button" className="monitor-confirm-button" onClick={() => void confirmAlert(alert.alert_id)}><Check size={15} />确认告警</button>}</article>)}</div>}</section>
    <div className="monitor-workbench-grid"><section className="settings-section monitor-rule-panel"><div className="settings-heading"><div><BellRing size={20} /><span><h2>规则配置</h2><p>每条规则绑定主题、指标阈值和独立投递通道。</p></span></div></div><div className="monitor-rule-form"><label>规则名称<input aria-label="规则名称" value={rule.name} onChange={(event) => setRule({ ...rule, name: event.target.value })} /></label><label>数据主题<select aria-label="数据主题" value={rule.topics[0]} onChange={(event) => setRule({ ...rule, topics: [event.target.value] })}>{topicOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>监控指标<select aria-label="监控指标" value={rule.field} onChange={(event) => setRule({ ...rule, field: event.target.value })}>{metricOptionsFor(rule.field).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>比较方式<select aria-label="比较方式" value={rule.operator} onChange={(event) => setRule({ ...rule, operator: event.target.value })}><option value="gte">大于等于</option><option value="lte">小于等于</option><option value="gt">大于</option><option value="lt">小于</option></select></label><label>阈值<input aria-label="阈值" type="number" value={rule.threshold} onChange={(event) => setRule({ ...rule, threshold: Number(event.target.value) })} /></label></div><div className="monitor-channel-toggles"><span>投递通道</span>{(["in_app", "tts", "feishu"] as const).map((channel) => <label key={channel}><input type="checkbox" checked={rule.channels[channel]} onChange={(event) => setRule({ ...rule, channels: { ...rule.channels, [channel]: event.target.checked } })} />{channel === "tts" ? <Volume2 size={14} /> : channel === "feishu" ? <Cloud size={14} /> : <BellRing size={14} />}{channelNames[channel]}</label>)}</div><button type="button" className="settings-action" disabled={saving || !rule.name.trim()} onClick={() => void saveRule()}><Save size={15} />保存监控规则</button>{rules.length > 0 && <div className="monitor-rule-list">{rules.map((item) => { const draft = ruleDraft(item); return <button type="button" key={item.id} onClick={() => setRule(draft)}><strong>{item.name}</strong><small>{draft.topics.map((topic) => topicLabel(topic)).join("、")} · {metricLabel(draft.field)} {operatorLabel(draft.operator)} {draft.threshold}</small></button>; })}</div>}</section><section className="settings-section monitor-channel-panel"><div className="settings-heading"><div><Cloud size={20} /><span><h2>通知通道</h2><p>飞书机器人地址使用本机凭据保护保存，页面只回显脱敏状态。</p></span></div></div><div className="monitor-channel-status"><article><BellRing size={17} /><strong>站内告警</strong><span className="status-chip ok">已启用</span></article><article><Volume2 size={17} /><strong>语音播报</strong><span className="status-chip ok">已接入</span></article><article><Cloud size={17} /><strong>飞书</strong><span className={`status-chip ${settings?.feishu_configured && settings.feishu_enabled ? "ok" : "muted"}`}>{settings?.feishu_configured && settings.feishu_enabled ? `已配置 · ${settings.webhook_hint}` : "未配置"}</span></article></div><div className="monitor-feishu-form"><label><input type="checkbox" checked={feishuEnabled} onChange={(event) => setFeishuEnabled(event.target.checked)} />启用飞书机器人</label><label>飞书机器人地址<input type="password" value={webhook} onChange={(event) => setWebhook(event.target.value)} placeholder={settings?.feishu_configured ? "已安全保存，重新填写可替换" : "请填写飞书机器人地址"} autoComplete="off" /></label><div><button type="button" className="settings-action" onClick={() => void saveFeishu()}><Save size={15} />保存配置</button><button type="button" className="settings-action secondary" disabled={!settings?.feishu_configured || !settings.feishu_enabled} onClick={() => void testFeishu()}>测试发送</button></div></div></section></div>
  </main>;
}
