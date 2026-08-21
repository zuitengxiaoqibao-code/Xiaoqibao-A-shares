import { useEffect, useRef, useState } from "react";
import { apiClient } from "../../shared/apiClient";

type PendingAlert = {
  alert_id: string;
  rule_id: string;
  symbol?: string | null;
  topic?: string | null;
  observed_at: string;
  snapshot?: Record<string, unknown>;
};

type Synthesize = (input: { text: string }, signal?: AbortSignal) => Promise<Blob>;

function alertText(alert: PendingAlert): string {
  const symbol = alert.symbol ? `股票 ${alert.symbol}。` : "全市场。";
  const values = Object.entries(alert.snapshot ?? {})
    .filter(([, value]) => value !== null && value !== undefined && typeof value !== "object")
    .slice(0, 3)
    .map(([key, value]) => `${key} ${String(value)}`)
    .join("，");
  return `监控中心提醒。${symbol}规则 ${alert.rule_id} 已触发。${values}`;
}

async function complete(alertId: string, status: "playing" | "sent" | "failed", reason?: string) {
  await apiClient.post(
    `/api/v1/monitor-center/alerts/${encodeURIComponent(alertId)}/delivery`,
    { channel: "tts", status, reason },
    { context: "监控语音状态写入" },
  );
}

export function MonitorTtsAnnouncer({ synthesize, pollMs = 15_000 }: { synthesize: Synthesize; pollMs?: number }) {
  const mounted = useRef(true);
  const running = useRef(false);
  const controller = useRef<AbortController | null>(null);
  const audio = useRef<HTMLAudioElement | null>(null);
  const objectUrl = useRef<string | null>(null);
  const [status, setStatus] = useState("监控语音待命");

  const release = () => {
    if (audio.current) {
      audio.current.onended = null;
      audio.current.onerror = null;
      audio.current.pause();
      audio.current = null;
    }
    if (objectUrl.current) {
      if (typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(objectUrl.current);
      objectUrl.current = null;
    }
  };

  const pump = async () => {
    if (!mounted.current || running.current) return;
    running.current = true;
    let activeAlert: PendingAlert | null = null;
    try {
      const alerts = await apiClient.get<PendingAlert[]>(
        "/api/v1/monitor-center/alerts/pending-tts?limit=1",
        { signal: controller.current?.signal, context: "监控语音告警读取" },
      );
      activeAlert = alerts[0];
      if (!activeAlert || !mounted.current) return;
      await complete(activeAlert.alert_id, "playing");
      setStatus(`正在播报 ${activeAlert.symbol || "全市场"}`);
      const blob = await synthesize({ text: alertText(activeAlert) }, controller.current?.signal);
      if (!mounted.current) return;
      const url = URL.createObjectURL(blob);
      const player = new Audio(url);
      objectUrl.current = url;
      audio.current = player;
      const finish = async (nextStatus: "sent" | "failed", reason?: string) => {
        release();
        try {
          await complete(activeAlert!.alert_id, nextStatus, reason);
        } finally {
          if (mounted.current) setStatus(nextStatus === "sent" ? "监控语音待命" : "监控语音异常");
        }
      };
      player.onended = () => { void finish("sent"); };
      player.onerror = () => { void finish("failed", "音频播放失败，请检查系统输出设备"); };
      await player.play();
    } catch (error) {
      if (controller.current?.signal.aborted || !mounted.current) return;
      if (activeAlert) {
        try { await complete(activeAlert.alert_id, "failed", error instanceof Error ? error.message : "监控语音暂不可用"); } catch { /* state write is best effort */ }
      }
      setStatus(error instanceof Error ? error.message : "监控语音暂不可用");
    } finally {
      running.current = false;
    }
  };

  useEffect(() => {
    mounted.current = true;
    controller.current = new AbortController();
    void pump();
    const timer = window.setInterval(() => void pump(), pollMs);
    return () => {
      mounted.current = false;
      controller.current?.abort();
      window.clearInterval(timer);
      release();
    };
  }, [pollMs, synthesize]);

  return <span className="sr-only" role="status" aria-live="polite">{status}</span>;
}
