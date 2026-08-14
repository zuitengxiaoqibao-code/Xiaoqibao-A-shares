import { AlertTriangle, Radio, Volume2, Waves } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { OverviewAnomaly } from "../market-overview/types";
import type { SpeechSynthesizer } from "./types";


type AnnouncerPhase = "waiting" | "synthesizing" | "playing" | "error";

function anomalyText(item: OverviewAnomaly): string {
  const symbols = item.symbols.length > 0
    ? `关联股票，${item.symbols.join("、")}。`
    : "";
  return `${item.label}。${item.headline}。${symbols}`;
}

function byOccurredAt(left: OverviewAnomaly, right: OverviewAnomaly): number {
  return new Date(left.occurred_at).getTime() - new Date(right.occurred_at).getTime();
}

export function isVoiceEligible(item: OverviewAnomaly): boolean {
  return item.credibility !== "pending"
    && item.credibility !== "rejected"
    && item.strength !== "low"
    && item.direction !== "uncertain";
}

export function AnomalyVoiceAnnouncer({ anomalies, synthesize }: {
  anomalies: OverviewAnomaly[];
  synthesize: SpeechSynthesizer;
}) {
  const [phase, setPhase] = useState<AnnouncerPhase>("waiting");
  const [current, setCurrent] = useState<OverviewAnomaly | null>(null);
  const [queueCount, setQueueCount] = useState(0);
  const [error, setError] = useState("");
  const mounted = useRef(true);
  const initialized = useRef(false);
  const knownIds = useRef(new Set<string>());
  const queue = useRef<OverviewAnomaly[]>([]);
  const processing = useRef(false);
  const audio = useRef<HTMLAudioElement | null>(null);
  const audioUrl = useRef<string | null>(null);
  const controller = useRef<AbortController | null>(null);
  const pump = useRef<() => Promise<void>>(async () => undefined);

  const releaseAudio = () => {
    if (audio.current) {
      audio.current.onended = null;
      audio.current.onerror = null;
      audio.current.pause();
      audio.current = null;
    }
    if (audioUrl.current) {
      if (typeof URL.revokeObjectURL === "function") URL.revokeObjectURL(audioUrl.current);
      audioUrl.current = null;
    }
  };

  pump.current = async () => {
    if (!mounted.current || processing.current || queue.current.length === 0) return;
    const item = queue.current.shift();
    if (!item) return;
    processing.current = true;
    setQueueCount(queue.current.length);
    setCurrent(item);
    setPhase("synthesizing");
    setError("");
    const nextController = new AbortController();
    controller.current = nextController;
    try {
      const blob = await synthesize({ text: anomalyText(item) }, nextController.signal);
      if (!mounted.current || nextController.signal.aborted) return;
      const url = URL.createObjectURL(blob);
      const player = new Audio(url);
      audioUrl.current = url;
      audio.current = player;
      const finish = () => {
        releaseAudio();
        processing.current = false;
        if (!mounted.current) return;
        setCurrent(null);
        setPhase("waiting");
        void pump.current();
      };
      player.onended = finish;
      player.onerror = () => {
        setError("音频播放失败，请检查系统输出设备。");
        setPhase("error");
        finish();
      };
      await player.play();
      if (mounted.current) setPhase("playing");
    } catch (reason) {
      if (nextController.signal.aborted || !mounted.current) return;
      processing.current = false;
      setCurrent(null);
      setPhase("error");
      setError(reason instanceof Error ? reason.message : "语音合成暂不可用");
      void pump.current();
    } finally {
      if (controller.current === nextController) controller.current = null;
    }
  };

  useEffect(() => {
    const ordered = [...anomalies].filter(isVoiceEligible).sort(byOccurredAt);
    if (!initialized.current) {
      ordered.forEach((item) => knownIds.current.add(item.anomaly_id));
      const latest = ordered.at(-1);
      if (latest) queue.current.push(latest);
      initialized.current = true;
    } else {
      const fresh = ordered.filter((item) => !knownIds.current.has(item.anomaly_id));
      fresh.forEach((item) => {
        knownIds.current.add(item.anomaly_id);
        queue.current.push(item);
      });
    }
    setQueueCount(queue.current.length);
    void pump.current();
  }, [anomalies]);

  useEffect(() => () => {
    mounted.current = false;
    queue.current = [];
    controller.current?.abort();
    releaseAudio();
  }, []);

  const phaseLabel = phase === "playing" ? "正在播报"
    : phase === "synthesizing" ? "正在生成语音"
    : phase === "error" ? "播报异常"
    : anomalies.length > 0 ? "监听新异动" : "等待已验证异动";

  return <section className="overview-voice-announcer" aria-label="异动语音播报">
    <header>
      <div><Volume2 size={20} /><span><b>异动语音播报</b><small>Microsoft Edge TTS 真实语音</small></span></div>
      <strong className={`voice-phase ${phase}`}><Radio size={14} />{phaseLabel}</strong>
    </header>
    <div className="voice-now-playing" role="status">
      <Waves size={30} />
      <div>
        <span>{current ? "NOW ANNOUNCING" : "VOICE CHANNEL"}</span>
        <h2>{current?.headline ?? "已连接异动监测，发现新事件后自动播报"}</h2>
        <p>{current ? `${current.label} · ${current.symbols.join(" / ")}` : `待播队列 ${queueCount} 条`}</p>
      </div>
    </div>
    {error && <div className="voice-error" role="alert"><AlertTriangle size={16} /><span><b>语音合成暂不可用</b>{error}</span></div>}
    <div className="voice-event-list">
      {anomalies.length === 0
        ? <p className="overview-empty">当前没有可播报的已验证 A 股异动</p>
        : [...anomalies].sort(byOccurredAt).reverse().slice(0, 12).map((item) => <article key={item.anomaly_id}>
          <time>{new Intl.DateTimeFormat("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Shanghai" }).format(new Date(item.occurred_at))}</time>
          <span><b>{item.label}</b><small>{item.headline}</small></span>
          <em>{knownIds.current.has(item.anomaly_id) ? "已进入播报通道" : "待识别"}</em>
        </article>)}
    </div>
  </section>;
}
