import { BellRing, RefreshCw, ShieldAlert } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

type Alert = { alert_id: string; symbol: string; observed_at: string; delivery: Record<string, string>; snapshot?: Record<string, unknown> };

export function MonitorCenterView() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    setError("");
    void fetch("/api/v1/monitor-center/alerts?limit=30").then(async (response) => {
      if (!response.ok) throw new Error("监控告警读取失败");
      setAlerts(await response.json() as Alert[]);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "监控中心暂不可用"));
  }, []);
  useEffect(() => { load(); }, [load]);
  return <main className="terminal-page beginner-page monitor-center-view"><header><p className="eyebrow">REALTIME MONITOR</p><h1>监控中心</h1><p>集中查看价格、成交、策略、新闻与风险闸门触发记录。</p><button type="button" className="settings-action" onClick={load}><RefreshCw size={15} />刷新告警</button></header>{error && <p className="cockpit-error" role="alert"><ShieldAlert size={15} />{error}</p>}<section className="settings-section"><div className="settings-heading"><div><BellRing size={20} /><span><h2>告警历史</h2><p>每条告警保留触发快照、时间和投递状态。</p></span></div></div>{alerts.length === 0 ? <p className="data-import-empty">暂无已触发告警</p> : <div className="monitor-alert-grid">{alerts.map((alert) => <article key={alert.alert_id}><strong>{alert.symbol || "全市场"}</strong><time>{new Date(alert.observed_at).toLocaleString("zh-CN", { hour12: false })}</time><small>{Object.entries(alert.delivery).map(([key, value]) => `${key}: ${value}`).join(" · ")}</small></article>)}</div>}</section></main>;
}
