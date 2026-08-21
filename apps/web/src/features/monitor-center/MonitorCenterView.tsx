import { BellRing, CheckCircle2, Cloud, RefreshCw, Save, ShieldAlert, Volume2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { apiClient } from "../../shared/apiClient";

type Alert = {
  alert_id: string;
  rule_id: string;
  topic?: string | null;
  symbol?: string | null;
  observed_at: string;
  delivery: Record<string, string>;
  delivery_reason?: Record<string, string>;
  snapshot?: Record<string, unknown>;
};
type Rule = { id: string; name: string; topics: string[]; conditions: Record<string, Record<string, number>>; channels?: { in_app?: boolean; tts?: boolean; feishu?: boolean } };
type RuleDraft = { id: string; name: string; topics: string[]; field: string; operator: string; threshold: number; channels: { in_app: boolean; tts: boolean; feishu: boolean } };
type NotificationSettings = { feishu_configured: boolean; feishu_enabled: boolean; webhook_hint: string | null };

const topicOptions = [["market_overview", "市场总览"], ["quant_strategy", "量化策略"], ["news_events", "新闻事件"], ["late_session_candidates", "尾盘选股"]] as const;
const channelNames: Record<string, string> = { in_app: "站内", tts: "语音", feishu: "飞书" };
const statusNames: Record<string, string> = { sent: "已送达", pending: "等待投递", playing: "正在播报", failed: "失败", "未配置": "未配置" };

const defaultRule = (): RuleDraft => ({ id: `rule-${Date.now()}`, name: "新监控规则", topics: ["quant_strategy"], field: "risk_score", operator: "gte", threshold: 65, channels: { in_app: true, tts: true, feishu: false } });
function ruleDraft(item: Rule): RuleDraft {
  const [field, operators] = Object.entries(item.conditions)[0] ?? ["risk_score", { gte: 65 }];
  const [operator, threshold] = Object.entries(operators)[0] ?? ["gte", 65];
  return { id: item.id, name: item.name, topics: item.topics ?? ["quant_strategy"], field, operator, threshold: Number(threshold), channels: { in_app: item.channels?.in_app !== false, tts: item.channels?.tts !== false, feishu: item.channels?.feishu === true } };
}

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  return (await apiClient.request<T>(path, { ...init, context: "监控中心" })).data;
}

function deliveryLabel(channel: string, status: string): string {
  return `${channelNames[channel] ?? channel}${statusNames[status] ?? status}`;
}

export function MonitorCenterView() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [rules, setRules] = useState<Rule[]>([]);
  const [settings, setSettings] = useState<NotificationSettings | null>(null);
  const [rule, setRule] = useState<RuleDraft>(defaultRule);
  const [webhook, setWebhook] = useState("");
  const [feishuEnabled, setFeishuEnabled] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const [nextAlerts, nextRules, nextSettings] = await Promise.all([
        jsonFetch<Alert[]>("/api/v1/monitor-center/alerts?limit=30"),
        jsonFetch<Rule[]>("/api/v1/monitor-center/rules"),
        jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings"),
      ]);
      setAlerts(nextAlerts);
      setRules(nextRules);
      setSettings(nextSettings);
      setFeishuEnabled(nextSettings.feishu_enabled);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "监控中心暂不可用");
    }
  }, []);
  useEffect(() => { void load(); }, [load]);

  const saveRule = async () => {
    setSaving(true);
    setError("");
    try {
      await jsonFetch<Rule>("/api/v1/monitor-center/rules", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: rule.id, name: rule.name, topics: rule.topics, conditions: { [rule.field]: { [rule.operator]: rule.threshold } }, channels: rule.channels }) });
      setNotice("监控规则已保存，下一次实时快照将按新规则评估");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "监控规则保存失败");
    } finally { setSaving(false); }
  };

  const testFeishu = async () => {
    setNotice("");
    try {
      const result = await jsonFetch<{ status: string; message: string }>("/api/v1/monitor-center/notification-settings/test", { method: "POST" });
      setNotice(result.message);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "飞书测试发送失败"); }
  };
  const saveFeishu = async () => {
    if (feishuEnabled && !webhook.trim() && !settings?.feishu_configured) { setError("启用飞书前必须填写飞书 Webhook"); return; }
    try {
      if (!webhook.trim() && settings?.feishu_configured && !feishuEnabled) {
        setSettings(await jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings", { method: "DELETE" }));
      } else {
        setSettings(await jsonFetch<NotificationSettings>("/api/v1/monitor-center/notification-settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ feishu_enabled: feishuEnabled, feishu_webhook: webhook.trim() || null }) }));
      }
      setWebhook(""); setNotice("飞书通知配置已安全保存");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "飞书配置保存失败"); }
  };

  return <main className="terminal-page beginner-page monitor-center-view">
    <header><p className="eyebrow">REALTIME MONITOR</p><h1>监控中心</h1><p>按实时主题评估规则，独立处理站内、Edge TTS 语音和飞书投递。</p><button type="button" className="settings-action" onClick={() => void load()}><RefreshCw size={15} />刷新监控状态</button></header>
    {error && <p className="cockpit-error" role="alert"><ShieldAlert size={15} />{error}</p>}
    {notice && <p className="monitor-notice" role="status"><CheckCircle2 size={15} />{notice}</p>}
    <div className="monitor-workbench-grid">
      <section className="settings-section monitor-rule-panel"><div className="settings-heading"><div><BellRing size={20} /><span><h2>规则配置</h2><p>每条规则绑定主题、指标阈值和独立投递通道。</p></span></div></div>
        <div className="monitor-rule-form">
          <label>规则名称<input aria-label="规则名称" value={rule.name} onChange={(event) => setRule({ ...rule, name: event.target.value })} /></label>
          <label>数据主题<select aria-label="数据主题" value={rule.topics[0]} onChange={(event) => setRule({ ...rule, topics: [event.target.value] })}>{topicOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label>字段路径<input aria-label="字段路径" value={rule.field} onChange={(event) => setRule({ ...rule, field: event.target.value })} placeholder="例如 regime.risk_score" /></label>
          <label>比较符<select aria-label="比较符" value={rule.operator} onChange={(event) => setRule({ ...rule, operator: event.target.value })}><option value="gte">大于等于</option><option value="lte">小于等于</option><option value="gt">大于</option><option value="lt">小于</option></select></label>
          <label>阈值<input aria-label="阈值" type="number" value={rule.threshold} onChange={(event) => setRule({ ...rule, threshold: Number(event.target.value) })} /></label>
        </div>
        <div className="monitor-channel-toggles"><span>投递通道</span>{(["in_app", "tts", "feishu"] as const).map((channel) => <label key={channel}><input type="checkbox" checked={rule.channels[channel]} onChange={(event) => setRule({ ...rule, channels: { ...rule.channels, [channel]: event.target.checked } })} />{channel === "tts" ? <Volume2 size={14} /> : channel === "feishu" ? <Cloud size={14} /> : <BellRing size={14} />}{channelNames[channel]}</label>)}</div>
        <button type="button" className="settings-action" disabled={saving || !rule.name.trim()} onClick={() => void saveRule()}><Save size={15} />保存监控规则</button>
        {rules.length > 0 && <div className="monitor-rule-list">{rules.map((item) => { const draft = ruleDraft(item); return <button type="button" key={item.id} onClick={() => setRule(draft)}><strong>{item.name}</strong><small>{draft.topics.map((topic) => topicOptions.find(([value]) => value === topic)?.[1] ?? topic).join("、")} · {draft.field} {draft.operator} {draft.threshold}</small></button>; })}</div>}
      </section>
      <section className="settings-section monitor-channel-panel"><div className="settings-heading"><div><Cloud size={20} /><span><h2>通知通道</h2><p>Webhook 使用本机凭据保护保存，页面只回显脱敏状态。</p></span></div></div><div className="monitor-channel-status"><article><BellRing size={17} /><strong>站内告警</strong><span className="status-chip ok">已启用</span></article><article><Volume2 size={17} /><strong>Edge TTS</strong><span className="status-chip ok">已接入</span></article><article><Cloud size={17} /><strong>飞书</strong><span className={`status-chip ${settings?.feishu_configured && settings.feishu_enabled ? "ok" : "muted"}`}>{settings?.feishu_configured && settings.feishu_enabled ? `已配置 · ${settings.webhook_hint}` : "未配置"}</span></article></div><div className="monitor-feishu-form"><label><input type="checkbox" checked={feishuEnabled} onChange={(event) => setFeishuEnabled(event.target.checked)} />启用飞书机器人</label><label>飞书 Webhook<input type="password" value={webhook} onChange={(event) => setWebhook(event.target.value)} placeholder={settings?.feishu_configured ? "已安全保存，重新填写可替换" : "https://open.feishu.cn/open-apis/bot/v2/hook/..."} autoComplete="off" /></label><div><button type="button" className="settings-action" onClick={() => void saveFeishu()}><Save size={15} />保存配置</button><button type="button" className="settings-action secondary" disabled={!settings?.feishu_configured || !settings.feishu_enabled} onClick={() => void testFeishu()}>测试发送</button></div></div></section>
    </div>
    <section className="settings-section"><div className="settings-heading"><div><BellRing size={20} /><span><h2>告警历史</h2><p>每条告警保留触发主题、快照时间和独立投递状态。</p></span></div></div>{alerts.length === 0 ? <p className="data-import-empty">暂无已触发告警</p> : <div className="monitor-alert-grid">{alerts.map((alert) => <article key={alert.alert_id}><div className="monitor-alert-title"><strong>{alert.symbol || "全市场"}</strong><small>{alert.rule_id} · {topicOptions.find(([value]) => value === alert.topic)?.[1] ?? alert.topic ?? "实时快照"}</small></div><time>{new Date(alert.observed_at).toLocaleString("zh-CN", { hour12: false })}</time><div className="monitor-delivery-tags">{Object.entries(alert.delivery).map(([key, value]) => <span className={`status-chip ${value === "sent" ? "ok" : value === "failed" ? "bad" : "muted"}`} key={key}>{deliveryLabel(key, value)}</span>)}</div>{alert.delivery_reason && <p className="monitor-alert-reason">{Object.entries(alert.delivery_reason).map(([key, value]) => `${channelNames[key] ?? key}：${value}`).join("；")}</p>}</article>)}</div>}</section>
  </main>;
}
