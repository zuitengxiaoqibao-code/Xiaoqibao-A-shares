import { Activity, CheckCircle2, Clock3, ShieldAlert } from "lucide-react";

import type { Advice, DecisionPhase } from "../decision-workbench/types";
import { qualityReasonLabel } from "../decision-workbench/PhaseContextPanel";
import { beginnerAdviceExplanation } from "../decision-workbench/explanation";
import { phaseExecutionCopy } from "../decision-workbench/phaseExecution";
import type { StockCockpitSnapshot } from "./types";

const phases: Array<[DecisionPhase, string, string]> = [
  ["premarket", "盘前研判", "开盘前的初始判断"],
  ["intraday", "盘中观察", "行情变化后的最新判断"],
  ["postclose", "盘后验证", "收盘后的验证与归因"],
];
const actions: Record<Advice["action"], string> = { observe: "加入观察", wait: "暂不参与", avoid: "回避", invalidated: "已失效" };

export function PhaseTimeline({ phases: histories, symbol }: { phases: StockCockpitSnapshot["phases"]; symbol: string }) {
  return <section className="stock-phase-timeline" aria-labelledby="phase-timeline-title"><header className="cockpit-block-title"><div><p className="eyebrow">一天中的观察节奏</p><h2 id="phase-timeline-title">盘前 · 盘中 · 盘后</h2></div></header>
    <div className="phase-lanes">{phases.map(([phase, title, description]) => {
      const history = histories[phase];
      const selected = (history?.advice ?? []).filter((item) => item.symbol === symbol);
      const latest = selected.at(-1);
      const executionCopy = phaseExecutionCopy(history?.execution ?? undefined, phase);
      const phaseRan = (history?.change_stream ?? []).length > 0 || history?.execution?.status === "completed";
      const blocked = history?.phase_status === "blocked";
      const blockedReason = qualityReasonLabel(
        history?.quality_reasons?.[0] ?? "block_reason_unrecorded",
      );
      const blockedNotice = blocked
        ? `本轮${title}已拦截：${blockedReason}。${latest ? "下方保留最近一次可验证判断。" : "当前没有新的可验证判断。"}`
        : null;
      const laneState = blocked ? "blocked" : history?.execution?.status ?? history?.phase_status ?? (latest ? "ready" : "empty");
      return <section className={`phase-lane state-${laneState}`} key={phase}><header><div><Activity size={15} /><h3>{title}</h3></div><p>{description}</p></header>
        {blockedNotice && <p className="phase-blocked-notice" role="status"><ShieldAlert size={14} /><span>{blockedNotice}</span></p>}
        {!latest ? !blockedNotice && <p className={`phase-empty execution-${history?.execution?.status ?? "empty"}`}><Clock3 size={14} />{executionCopy?.label ?? (phaseRan ? "本阶段已运行，当时未纳入这只股票" : "本阶段没有生成可核验记录")}</p> : <>{executionCopy && <p className={`phase-empty execution-${history?.execution?.status}`}><Clock3 size={14} />{executionCopy.label}</p>}<article className={`phase-summary action-${latest.action}`}><span><CheckCircle2 size={14} />{actions[latest.action]}</span><h4>{latest.conclusion}</h4><p>{beginnerAdviceExplanation(latest, phase) || latest.supporting_evidence[0]?.summary || "等待更多可验证信息"}</p><time>{new Date(latest.created_at).toLocaleString("zh-CN", { hour12: false })}</time></article></>}
      </section>;
    })}</div>
  </section>;
}
