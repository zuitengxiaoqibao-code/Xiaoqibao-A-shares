import { AlertTriangle, Check, Database, LoaderCircle, MonitorUp, RotateCw } from "lucide-react";
import { useEffect, useState } from "react";

import type { MarketOverviewResponse } from "./types";

type Props = {
  data: MarketOverviewResponse | null;
  error: string | null;
  loading: boolean;
  onRetry: () => void;
};

type StageState = "complete" | "active" | "waiting" | "error";

type Stage = {
  label: string;
  detail: string;
  state: StageState;
};

function initialProgress(): number {
  const desktopProgress = Number(new URLSearchParams(window.location.search).get("desktopBoot"));
  return Number.isFinite(desktopProgress) && desktopProgress >= 1 && desktopProgress < 48
    ? Math.floor(desktopProgress)
    : 1;
}

function reducedMotionRequested(): boolean {
  return typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function HomepageStartupOverlay({ data, error, loading, onRetry }: Props) {
  const [visible, setVisible] = useState(true);
  const [progress, setProgress] = useState(initialProgress);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const failed = Boolean(error && !data);
  const verifiedTarget = data ? 100 : 48;

  useEffect(() => {
    if (progress >= verifiedTarget) return;
    if (reducedMotionRequested()) {
      setProgress(verifiedTarget);
      return;
    }
    const timer = window.setInterval(() => {
      setProgress((current) => {
        if (current >= verifiedTarget) {
          window.clearInterval(timer);
          return current;
        }
        return current + 1;
      });
    }, 20);
    return () => window.clearInterval(timer);
  }, [verifiedTarget]);

  useEffect(() => {
    if (data || failed || !loading) return;
    setElapsedSeconds(0);
    const timer = window.setInterval(() => setElapsedSeconds((current) => current + 1), 1000);
    return () => window.clearInterval(timer);
  }, [data, failed, loading]);

  useEffect(() => {
    if (!data) {
      setVisible(true);
      return;
    }
    if (progress < 100) return;
    const timer = window.setTimeout(() => setVisible(false), 240);
    return () => window.clearTimeout(timer);
  }, [data, progress]);

  if (!visible) return null;

  const marketDetail = data
    ? `${data.market_data.quote_count.toLocaleString("zh-CN")} 条行情 / ${data.market_data.universe_count.toLocaleString("zh-CN")} 只标的`
    : failed ? error ?? "读取失败" : "正在读取通达信与本地缓存";
  const summaryDetail = data
    ? `${data.indices.length} 个指数 · ${data.sectors.length} 个板块 · ${data.anomalies.length} 条异动`
    : "等待市场快照完成后校验";
  const stages: Stage[] = [
    { label: "桌面窗口", detail: "窗口框架已显示", state: "complete" },
    { label: "本地服务", detail: "本地 API 已就绪", state: "complete" },
    { label: "前端资源", detail: "React 资源已挂载", state: "complete" },
    { label: "全市场快照", detail: marketDetail, state: data ? "complete" : failed ? "error" : "active" },
    { label: "首页数据校验", detail: summaryDetail, state: data ? "complete" : "waiting" },
  ];
  const currentStep = data
    ? "首页关键数据已完整加载"
    : failed ? "关键数据加载失败"
    : loading ? "读取本地 A 股全市场快照" : "等待数据任务启动";

  return <section
    className={`homepage-startup-overlay ${failed ? "is-error" : data ? "is-complete" : "is-loading"}`}
    role="dialog"
    aria-modal="true"
    aria-label={failed ? "信息总览加载失败" : "正在加载信息总览"}
  >
    <div className="homepage-startup-visual" aria-hidden="true">
      <span className="homepage-startup-radar" data-testid="startup-radar" />
      <span className="homepage-startup-sweep" data-testid="startup-radar-sweep" />
      <Database size={25} />
    </div>
    <div className="homepage-startup-copy">
      <p>REAL DATA STARTUP PIPELINE</p>
      <h2>{failed ? "信息总览未能完整加载" : data ? "首页数据准备完成" : "正在建立 A 股数据视图"}</h2>
      <div className="homepage-startup-current">
        {failed ? <AlertTriangle size={16} /> : data ? <Check size={16} /> : <LoaderCircle className="spinning" size={16} />}
        <span><b>{currentStep}</b>{!data && !failed && loading && <small>已持续 {elapsedSeconds} 秒 · 数据任务运行中</small>}</span>
        <strong>{progress}%</strong>
      </div>
      <div
        className="homepage-startup-progress"
        role="progressbar"
        aria-label="首页数据加载进度"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={progress}
        data-verified-target={verifiedTarget}
      ><span style={{ width: `${progress}%` }} /><i aria-hidden="true" /></div>
      <div className="homepage-startup-stages">
        {stages.map((stage) => <div key={stage.label} data-state={stage.state}>
          <span>{stage.state === "complete" ? <Check size={13} /> : stage.state === "active" ? <LoaderCircle className="spinning" size={13} /> : stage.state === "error" ? <AlertTriangle size={13} /> : <MonitorUp size={13} />}</span>
          <b>{stage.label}</b>
          <small>{stage.detail}</small>
        </div>)}
      </div>
      {failed && <button type="button" aria-label="重试首页数据" onClick={onRetry} disabled={loading}>
        <RotateCw size={15} />重新读取关键数据
      </button>}
      <footer>百分比逐点平滑更新，已完成值不会超过真实任务节点</footer>
    </div>
  </section>;
}
