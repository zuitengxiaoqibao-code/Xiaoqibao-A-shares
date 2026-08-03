import { Activity, CheckCircle2, Gauge, ShieldAlert, TimerReset } from "lucide-react";
import type { CSSProperties, ReactNode } from "react";

import type { CandidateSentimentBand, CandidateSentimentSnapshot } from "../candidate-sentiment/types";
import type { StockAssessment, StockCockpitSnapshot } from "./types";

type Tone = "positive" | "warning" | "danger" | "info";
type GaugeStyle = CSSProperties & { "--gauge-value": string };
type Props = {
  assessment: StockAssessment;
  overallQuality: StockCockpitSnapshot["overall_quality"];
  readySources: number;
  totalSources: number;
  candidateSentiment: CandidateSentimentSnapshot | null;
};

const actionNames: Record<StockAssessment["action"], string> = {
  observe: "加入观察",
  wait: "暂不参与",
  avoid: "回避",
};
const actionTones: Record<StockAssessment["action"], Tone> = {
  observe: "positive",
  wait: "warning",
  avoid: "danger",
};
const sentimentNames: Record<CandidateSentimentBand, string> = {
  strongly_bearish: "显著偏空",
  cautious: "偏谨慎",
  neutral: "中性",
  positive: "偏积极",
  overheated: "情绪过热",
  unavailable: "未评分",
};

function boundedPercentage(value: unknown): number | null {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return Math.min(100, Math.max(0, numeric));
}

function confidencePercentage(value: string): number | null {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return null;
  return boundedPercentage(numeric <= 1 ? numeric * 100 : numeric);
}

function sentimentTone(band: CandidateSentimentBand): Tone {
  if (band === "positive") return "positive";
  if (band === "cautious") return "warning";
  if (band === "strongly_bearish" || band === "overheated") return "danger";
  return "info";
}

function displayScore(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function ActionIcon({ action }: { action: StockAssessment["action"] }) {
  if (action === "observe") return <CheckCircle2 size={18} />;
  if (action === "wait") return <TimerReset size={18} />;
  return <ShieldAlert size={18} />;
}

function SignalGauge({ label, value, tone, detail }: { label: string; value: number; tone: Tone; detail: ReactNode }) {
  return <section className={`signal-meter tone-${tone}`}>
    <header><Gauge size={15} /><h3>{label}</h3></header>
    <div
      className="signal-gauge"
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
      aria-valuetext={`${displayScore(value)}%`}
      style={{ "--gauge-value": `${value}%` } as GaugeStyle}
    ><span><strong>{displayScore(value)}</strong><small>%</small></span></div>
    <p>{detail}</p>
  </section>;
}

export function KeySignalDashboard({ assessment, overallQuality, readySources, totalSources, candidateSentiment }: Props) {
  const actionTone = actionTones[assessment.action];
  const confidence = confidencePercentage(assessment.confidence);
  const evidenceCoverage = totalSources > 0 ? boundedPercentage((readySources / totalSources) * 100) : null;
  const evidenceTone: Tone = overallQuality === "ready" ? "positive" : overallQuality === "partial" ? "warning" : "danger";
  const sentimentScore = candidateSentiment ? boundedPercentage(candidateSentiment.score) : null;
  const currentSentimentTone = candidateSentiment ? sentimentTone(candidateSentiment.band) : "info";
  const sentimentConflicts = Boolean(
    candidateSentiment
    && (candidateSentiment.band === "positive" || candidateSentiment.band === "overheated")
    && assessment.action !== "observe",
  );
  const primaryRisk = assessment.risks[0]
    ?? assessment.contrary_evidence[0]?.summary
    ?? "当前未发现明确风险，仍需观察失效条件。";
  const riskTone = assessment.action === "avoid" ? "danger" : "warning";

  return <div
    className={`key-signal-dashboard action-${assessment.action} evidence-${evidenceTone}`}
    role="region"
    aria-label="关键状态仪表"
  >
    <header className="key-signal-heading">
      <div><p className="eyebrow">有证据的辅助决策</p><h2>关键状态仪表</h2></div>
      <span className={`key-signal-quality tone-${evidenceTone}`}>{overallQuality === "ready" ? "证据较完整" : overallQuality === "partial" ? "证据部分可用" : "证据不足以判断"}</span>
    </header>
    <div className="key-signal-grid">
      <section className={`signal-action tone-${actionTone}`}>
        <header><ActionIcon action={assessment.action} /><h3>当前行动</h3></header>
        <strong>{actionNames[assessment.action]}</strong>
        <p>{assessment.conclusion}</p>
      </section>
      {confidence === null
        ? <section className="signal-meter unavailable"><header><Gauge size={15} /><h3>决策置信度</h3></header><strong>不可用</strong><p>本次未提供有效置信度</p></section>
        : <SignalGauge label="决策置信度" value={confidence} tone="info" detail="表示当前判断的确定程度" />}
      {evidenceCoverage === null
        ? <section className="signal-meter unavailable"><header><Gauge size={15} /><h3>证据覆盖率</h3></header><strong>不可用</strong><p>核心数据总数未提供</p></section>
        : <SignalGauge label="证据覆盖率" value={evidenceCoverage} tone={evidenceTone} detail={<>{readySources} / {totalSources} 类可用{evidenceTone !== "positive" && <strong> · 不确定性更高</strong>}</>} />}
      {candidateSentiment && sentimentScore !== null && candidateSentiment.band !== "unavailable"
        ? <SignalGauge label="个股情绪" value={sentimentScore} tone={currentSentimentTone} detail={`${sentimentNames[candidateSentiment.band]} · 独立观察`} />
        : <section className="signal-meter unavailable"><header><Activity size={15} /><h3>个股情绪</h3></header><strong>未评分</strong><p>不影响当前行动结论</p></section>}
    </div>
    <div className={`key-risk-alert tone-${riskTone}`} aria-label="关键风险提醒">
      <ShieldAlert size={17} />
      <div><span>优先提醒</span><b>{primaryRisk}</b>{sentimentConflicts && <strong>情绪不能覆盖当前风险结论</strong>}</div>
    </div>
  </div>;
}
