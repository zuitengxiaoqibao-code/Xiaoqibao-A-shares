import { AlertTriangle, Building2, CheckCircle2, Clock3, Database, RefreshCw, ShieldAlert, Target, TrendingDown, TrendingUp } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { useSelectedInstrument } from "../instrument-selection/SelectedInstrumentProvider";
import { friendlyError } from "../../shared/friendlyError";
import { isAutoSyncEnabled } from "../data-settings/syncPolicy";
import type { Advice } from "../decision-workbench/types";
import type { AssessmentAIExplanation, AssessmentAIStatus, StockCockpitSnapshot, StockPreparation } from "./types";
import { CockpitSections } from "./CockpitSections";
import { KeySignalDashboard } from "./KeySignalDashboard";
import { PhaseTimeline } from "./PhaseTimeline";
import type { CandidateSentimentSnapshot } from "../candidate-sentiment/types";
import { CandidateSentimentPanel } from "../candidate-sentiment/CandidateSentimentPanel";
import { WatchlistMarketSentiment } from "../market-sentiment/WatchlistMarketSentiment";
import type { MarketSentimentResponse } from "../market-sentiment/types";
import { StockEventKline } from "../stock-timeline/StockEventKline";
import type { StockTimelineLoader } from "../stock-timeline/types";
import { BreakingNewsStrip } from "../news-alerts/BreakingNewsStrip";
import type { BreakingNewsAlertLoader } from "../news-alerts/types";
import { useBreakingNewsAlerts } from "../news-alerts/useBreakingNewsAlerts";
import { DailyRefreshStatus } from "../../shared/DailyRefreshStatus";
import { readDailySnapshot, writeDailySnapshot, type DailySnapshotHit } from "../../shared/dailySnapshotCache";
import type { LoadProgress, LoadProgressCallback } from "../../shared/fetchJsonWithProgress";

type Loader = (symbol: string, asOf?: string, signal?: AbortSignal, onProgress?: LoadProgressCallback) => Promise<StockCockpitSnapshot>;
type Preparer = (symbol: string, signal?: AbortSignal) => Promise<import("./types").StockPreparation>;
type Props = { load: Loader; loadAI?: Loader; prepare?: Preparer; loadTimeline?: StockTimelineLoader; loadAlerts?: BreakingNewsAlertLoader; asOf?: string; refreshToken?: number; onRefreshRequest?: () => void; onSnapshot?: (snapshot: StockCockpitSnapshot) => void; candidateSentiment?: CandidateSentimentSnapshot | null; loadMarketSentiment?: () => Promise<MarketSentimentResponse>; onOpenCompanyResearch?: (symbol: string) => void };

const qualityNames = { ready: "数据完整", partial: "部分可用", blocked: "数据已拦截" } as const;
const sectionQualityNames = { ready: "行情有效", partial: "行情部分可用", stale: "行情陈旧", unavailable: "行情不可用", blocked: "行情已拦截" } as const;

function metric(data: StockCockpitSnapshot, key: string): unknown {
  const metrics = data.sections.market?.payload.metrics as Record<string, unknown> | undefined;
  if (key === "latest_price") return metrics?.price ?? metrics?.latest_price;
  return metrics?.[key];
}
function displayNumber(value: unknown, suffix = ""): string {
  return value === null || value === undefined || value === "" ? "--" : `${String(value)}${suffix}`;
}
function numericOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}
function displayPercent(value: unknown): string {
  const numeric = numericOrNull(value);
  return numeric === null ? "--" : `${numeric.toFixed(2)}%`;
}
const sectionChanges: Record<string, string> = {
  market: "实时行情发生变化需重评", quote: "实时行情发生变化需重评",
  trend: "走势数据发生变化需重评", price_volume: "走势数据发生变化需重评",
  fundamentals: "基本面或估值发生变化需重评", valuation: "基本面或估值发生变化需重评",
  risk: "风险状态发生变化需重评", news: "新闻或行业信息发生变化需重评", industry: "新闻或行业信息发生变化需重评",
};
const phaseStatusNames = {
  blocked: "已拦截",
  partial: "部分可用",
  ready: "已运行",
  empty: "尚无记录",
} as const;
const phaseStatusTitles: Array<[keyof StockCockpitSnapshot["phases"], string]> = [
  ["premarket", "盘前研判"],
  ["intraday", "盘中观察"],
  ["postclose", "盘后验证"],
];
const actionNames: Record<Advice["action"], string> = { observe: "加入观察", wait: "暂不参与", avoid: "回避", invalidated: "已失效" };
const actionTones: Record<Advice["action"], "positive" | "warning" | "danger"> = {
  observe: "positive", wait: "warning", avoid: "danger", invalidated: "danger",
};
const changeFieldNames: Record<string, string> = {
  action: "建议状态发生变化", conclusion: "结论发生变化", risks: "风险提示发生变化",
  invalidation_conditions: "重新判断条件发生变化", membership: "候选资格发生变化",
  outcome_status: "盘后结果发生变化", observation_state: "观察状态发生变化",
};
const checklistSources: Array<[string, string[]]> = [
  ["行情", ["market", "price_volume"]],
  ["趋势", ["trend"]],
  ["新闻与热点", ["news", "industry"]],
  ["资金", ["funds"]],
];
const outcomeStatusNames: Record<string, string> = { correct: "判断成立", unverifiable: "无法验证", wrong: "判断未成立", invalidated: "条件失效", risk_blocked: "风险拦截" };
const outcomeAttributionNames: Record<string, string> = { trend_failure: "趋势结果", data_unavailable: "数据不足", risk_event: "风险事件", news_misread: "新闻解读", data_issue: "数据问题", rule_block: "规则拦截" };

function allAdvice(data: StockCockpitSnapshot): Advice[] {
  const values = [
    ...data.current_advice,
    ...Object.values(data.phases).flatMap((history) => history.advice),
  ];
  return [...new Map(values.map((item) => [item.advice_id, item])).values()];
}

function adviceChangeSummary(data: StockCockpitSnapshot): { current: Advice; previous: Advice; fields: string[] } | null {
  const values = allAdvice(data).sort((left, right) => right.created_at.localeCompare(left.created_at));
  const current = values.find((item) => item.previous_advice_id && item.changed_fields.length > 0);
  if (!current?.previous_advice_id) return null;
  const previous = values.find((item) => item.advice_id === current.previous_advice_id);
  if (!previous) return null;
  const fields = [...new Set(current.changed_fields.map((field) => changeFieldNames[field]).filter(Boolean))];
  return { current, previous, fields };
}

function postcloseFeedback(data: StockCockpitSnapshot): { status: string; attribution: string | null; original: Advice | null } | null {
  const reviewed = data.phases.postclose.advice
    .slice()
    .sort((left, right) => right.created_at.localeCompare(left.created_at))
    .find((item) => typeof item.quantitative_result.outcome_status === "string" && outcomeStatusNames[item.quantitative_result.outcome_status]);
  if (!reviewed) return null;
  const originalId = reviewed.quantitative_result.original_advice_id;
  const original = typeof originalId === "string" ? allAdvice(data).find((item) => item.advice_id === originalId) ?? null : null;
  const attributionCode = reviewed.quantitative_result.error_attribution;
  return {
    status: outcomeStatusNames[reviewed.quantitative_result.outcome_status as string],
    attribution: typeof attributionCode === "string" ? outcomeAttributionNames[attributionCode] ?? null : null,
    original,
  };
}

function feedbackTone(status: string): "positive" | "warning" | "danger" {
  if (status === "判断成立") return "positive";
  if (status === "无法验证" || status === "条件失效") return "warning";
  return "danger";
}

function checklistStatus(data: StockCockpitSnapshot, names: string[]): "已验证" | "部分可用" | "数据陈旧" | "暂不可用" | "已拦截" {
  const statuses = names.map((name) => data.sections[name]?.status ?? "unavailable");
  if (statuses.includes("blocked")) return "已拦截";
  if (statuses.includes("unavailable")) return "暂不可用";
  if (statuses.includes("stale")) return "数据陈旧";
  if (statuses.includes("partial")) return "部分可用";
  return "已验证";
}

function checklistTone(status: ReturnType<typeof checklistStatus>): "ready" | "partial" | "unavailable" {
  return status === "已验证" ? "ready" : status === "部分可用" || status === "数据陈旧" ? "partial" : "unavailable";
}

function conditionPhrase(value: string): string {
  return value.replace(/[。！？；，、.!?;,]+$/u, "");
}

function phaseEmptyDetail(phase: keyof StockCockpitSnapshot["phases"]): string {
  return phase === "postclose" ? "盘后复盘尚未生成" : phase === "premarket" ? "盘前研判尚未生成" : "盘中监测尚未生成";
}

function phaseStatusSummary(data: StockCockpitSnapshot, phase: keyof StockCockpitSnapshot["phases"]): { label: string; detail: string; tone: string } {
  const history = data.phases?.[phase];
  if (!history) return { label: "尚无记录", detail: phaseEmptyDetail(phase), tone: "empty" };
  if (history.phase_status === "blocked") {
    return { label: "已拦截", detail: history.advice.length > 0 ? "保留最近一次可核验判断" : "数据质量不足，未生成新结论", tone: "blocked" };
  }
  if (history.advice.length > 0) {
    return { label: "已生成建议", detail: `${history.advice.length} 条可核验判断`, tone: "ready" };
  }
  const execution = history.execution;
  if (execution?.status === "scheduled") return { label: "已计划", detail: "到计划时间后生成", tone: "scheduled" };
  if (execution?.status === "running") return { label: "生成中", detail: "完成前不展示推测", tone: "running" };
  if (execution?.status === "failed") return { label: "生成失败", detail: "不会用虚构内容补位", tone: "failed" };
  if (execution?.status === "overdue") return { label: "已超时", detail: "尚无可核验结果", tone: "overdue" };
  if (history.phase_status === "partial") return { label: "部分可用", detail: "当前没有这只股票的新判断", tone: "partial" };
  if (history.change_stream.length > 0 || history.phase_status === "ready") {
    return { label: "已运行", detail: "本阶段未纳入这只股票", tone: "ready" };
  }
  return { label: phaseStatusNames.empty, detail: phaseEmptyDetail(phase), tone: "empty" };
}
function beginnerAssessmentText(value: string): string {
  const code = value.match(/^source_snapshot_unavailable:([a-z_]+)$/)?.[1];
  if (code) return sectionChanges[code] ?? "数据状态发生变化需重新判断";
  if (/缺失或晚于截止时间的分区/.test(value)) {
    if (/industry|news/.test(value)) return "新闻或行业信息晚于研判截止时间或暂缺";
    if (/market|quote/.test(value)) return "实时行情晚于研判截止时间或暂缺";
    if (/trend|price_volume/.test(value)) return "走势数据晚于研判截止时间或暂缺";
    if (/fundamentals|valuation/.test(value)) return "基本面或估值晚于研判截止时间或暂缺";
    return "部分数据晚于研判截止时间或暂缺";
  }
  if (/[a-z]+_[a-z_]+|[A-Z]{3,}(?:_[A-Z]+)*|[a-z_]+:[a-z_]+/.test(value)) return "数据状态发生变化需重新判断";
  return value
    .replace(/price_volume|trend/g, "走势数据").replace(/fundamentals|valuation/g, "基本面或估值")
    .replace(/industry|news/g, "新闻或行业信息").replace(/market|quote/g, "实时行情");
}
function beginnerAssessmentList(values: string[]): string[] {
  return [...new Set(values.map(beginnerAssessmentText))].slice(0, 3);
}

function preparationForSummary(data: StockCockpitSnapshot): StockPreparation {
  if (data.preparation) return data.preparation;
  const sourceNames = [
    ["quote", "market"], ["history", "trend"], ["finance", "fundamentals"], ["news", "news"],
    ["classification", "industry"], ["fund_flow", "funds"],
  ] as const;
  return {
    symbol: data.symbol,
    status: sourceNames.every(([, section]) => data.sections[section]?.status === "ready") ? "ready" : "partial",
    sources: sourceNames.map(([name, section]) => ({
      name,
      status: data.sections[section]?.status === "ready" ? "ready" : "partial",
      observed_at: data.sections[section]?.observed_at ?? null,
      reason: data.sections[section]?.reason ?? null,
    })),
    refreshed: false,
    started_at: data.cutoff,
    completed_at: data.cutoff,
  };
}

function EvidenceDecisionSummary({ data, candidateSentiment }: { data: StockCockpitSnapshot; candidateSentiment: CandidateSentimentSnapshot | null }) {
  const assessment = data.assessment;
  const preparation = preparationForSummary(data);
  const ready = preparation.sources.filter((source) => source.status === "ready").length;
  const total = preparation.sources.length;
  const evidence = beginnerAssessmentList(assessment.supporting_evidence.map((item) => item.summary));
  const risks = beginnerAssessmentList([...assessment.contrary_evidence.map((item) => item.summary), ...assessment.risks]);
  const invalidation = beginnerAssessmentList(assessment.invalidation_conditions);
  const nextStep = assessment.action === "observe"
    ? "观察量价、趋势和新闻是否继续相互印证"
    : assessment.action === "wait" ? "等待缺失数据补齐，或风险信号减弱" : "等待风险条件解除后重新评估";
  const change = adviceChangeSummary(data);
  const feedback = postcloseFeedback(data);
  const actionTone = actionTones[assessment.action];
  const dashboardAssessment = { ...assessment, risks };
  return <section className={`evidence-decision-summary evidence-${data.overall_quality} action-${assessment.action}`} aria-label="证据决策摘要">
    <KeySignalDashboard assessment={dashboardAssessment} overallQuality={data.overall_quality} readySources={ready} totalSources={total} candidateSentiment={candidateSentiment} />
    <AssessmentAI status={data.ai_status} explanation={data.ai_explanation} />
    <div className="phase-status-strip" aria-label="今日三阶段状态"><div className="phase-origin-note"><span>当前结论来自单股研判</span><b>单股研判</b><small>三阶段聚合任务独立显示，不会用空白覆盖已有结论</small></div>{phaseStatusTitles.map(([phase, title]) => { const status = phaseStatusSummary(data, phase); return <div className={`phase-status-item ${status.tone}`} key={phase}><span>{title}</span><b>{status.label}</b><small>{status.detail}</small></div>; })}</div>
    {change && <section className={`decision-change-summary tone-${actionTones[change.current.action]}`}><h3><RefreshCw size={15} />与上次相比</h3><p><strong>{actionNames[change.previous.action]} → {actionNames[change.current.action]}</strong></p><p>{change.fields.length ? change.fields.join("、") : "结论发生变化"}</p></section>}
    <section className="observation-checklist"><h3><CheckCircle2 size={15} />观察检查清单</h3><div>{checklistSources.map(([name, sections]) => { const status = checklistStatus(data, sections); return <span className={checklistTone(status)} key={name}><b>{name}</b><small>{status}</small></span>; })}</div></section>
    {feedback && <section className={`postclose-feedback tone-${feedbackTone(feedback.status)}`}><h3><Clock3 size={15} />盘后反馈</h3><p><strong>{feedback.status}</strong>{feedback.original ? ` · 对应原判断：${feedback.original.conclusion}` : ""}</p>{feedback.attribution && <small>归因：{feedback.attribution}</small>}</section>}
    <div className="evidence-decision-grid">
      <section className="tone-positive"><h3><CheckCircle2 size={15} />主要依据</h3>{evidence.length ? evidence.slice(0, 2).map((item) => <p key={item}>依据：{item}</p>) : <p>暂缺足够的已验证依据</p>}</section>
      <section className="risk tone-danger"><h3><ShieldAlert size={15} />主要风险</h3>{risks.length ? risks.slice(0, 2).map((item) => <p key={item}>风险：{item}</p>) : <p>未发现明确风险，但仍需持续观察</p>}</section>
      <section className={`tone-${actionTone}`}><h3><Clock3 size={15} />下一步</h3><p>{nextStep}</p></section>
      <section className="tone-danger"><h3><Target size={15} />何时推翻</h3>{invalidation.length ? invalidation.slice(0, 2).map((item) => <p key={item}>若{conditionPhrase(item)}，重新判断</p>) : <p>出现新的行情、公告或风险证据时重新判断</p>}</section>
    </div>
    <footer><span>数据截止：{new Date(data.cutoff).toLocaleString("zh-CN", { hour12: false })}</span><span>仅供观察，不构成买卖指令</span></footer>
  </section>;
}

function AssessmentAI({ status, explanation }: { status: AssessmentAIStatus; explanation: AssessmentAIExplanation | null }) {
  if (status === "unconfigured") return <section className="assessment-ai status-warning"><h3>AI 补充分析未启用</h3><p>当前行动结论仍由可验证数据生成，可在“数据设置”中配置 AI。</p></section>;
  if (status === "deferred") return <section className="assessment-ai status-warning"><h3>AI 补充分析后台生成中</h3><p>确定性分析已先显示，AI 解释完成后会自动补入，不影响继续查看其他股票。</p></section>;
  if (status === "timeout") return <section className="assessment-ai status-warning"><h3>AI 服务响应超时</h3><p>配置已生效，但本次生成超过等待时限。可稍后刷新，确定性研判未受影响。</p></section>;
  if (status === "http_error") return <section className="assessment-ai status-danger"><h3>AI 服务返回错误</h3><p>请检查服务地址、模型权限或账户状态。确定性研判仍然有效。</p></section>;
  if (status === "invalid") return <section className="assessment-ai status-danger"><h3>AI 返回内容未通过校验</h3><p>系统没有采用未经验证的内容，当前只展示确定性研判。</p></section>;
  if (!explanation) return <section className="assessment-ai status-warning"><h3>AI 解释缺少有效内容</h3><p>确定性研判未受影响，可稍后刷新。</p></section>;
  return <section className="assessment-ai status-ready"><h3>AI 补充解释</h3><p>{explanation.plain_language}</p><dl><div className="tone-info"><dt>新闻影响</dt><dd>{explanation.news_impact}</dd></div><div className="tone-info"><dt>热点归因</dt><dd>{explanation.hotspot_attribution}</dd></div><div className="tone-warning"><dt>不确定性</dt><dd>{explanation.uncertainty}</dd></div><div className="tone-danger"><dt>反方观点</dt><dd>{explanation.contrary_view}</dd></div></dl><small>仅解释冻结证据，不改变确定性动作、置信度或方案资格。</small></section>;
}

function PreparationStatus({ data, preparing = false }: { data: StockCockpitSnapshot; preparing?: boolean }) {
  const fallbackSources = [
    ["quote", "market"], ["history", "trend"], ["finance", "fundamentals"], ["news", "news"],
    ["classification", "industry"], ["fund_flow", "funds"],
  ].map(([name, section]) => ({
    name: name as "quote" | "history" | "finance" | "news" | "classification" | "fund_flow",
    status: data.sections[section]?.status === "ready" ? "ready" as const : "partial" as const,
    observed_at: data.sections[section]?.observed_at ?? null,
    reason: data.sections[section]?.reason ?? null,
  }));
  const preparation = data.preparation ?? {
    symbol: data.symbol, status: fallbackSources.every((source) => source.status === "ready") ? "ready" as const : "partial" as const,
    sources: fallbackSources, refreshed: false, started_at: data.cutoff, completed_at: data.cutoff,
  };
  const ready = preparation.sources.filter((source) => source.status === "ready").length;
  const names = { quote: "实时行情", history: "历史走势", finance: "基本面", news: "新闻", classification: "行业与板块", fund_flow: "资金流" } as const;
  const title = preparing ? "正在补齐数据" : !data.preparation ? "根据现有数据估算" : preparation.status === "ready" ? "数据已准备" : "部分数据待补齐";
  const detail = preparation.refreshed ? "已自动检查并更新" : !data.preparation ? "尚未执行自动补齐" : preparation.status === "ready" ? "数据无需再次补齐" : "仍有数据等待补齐";
  return <section className={`preparation-status ${preparation.status}`} aria-label="数据准备状态"><div><Database size={17} /><span><b>{title}</b><small>{detail}</small></span></div><div className="preparation-sources">{preparation.sources.map((source) => <span className={source.status} key={source.name}>{names[source.name]}<b>{source.status === "ready" ? "可用" : "待补齐"}</b></span>)}</div><small>{ready}/{preparation.sources.length} 类核心数据可用</small></section>;
}

export function StockDecisionCockpit({ load, loadAI, prepare, loadTimeline, loadAlerts, asOf, refreshToken = 0, onRefreshRequest, onSnapshot, candidateSentiment, loadMarketSentiment, onOpenCompanyResearch }: Props) {
  const { symbol, source } = useSelectedInstrument();
  const alertState = useBreakingNewsAlerts(loadAlerts, symbol, 3);
  const [data, setData] = useState<StockCockpitSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stale, setStale] = useState(false);
  const [preparing, setPreparing] = useState(false);
  const [loadProgress, setLoadProgress] = useState<LoadProgress | null>(null);
  const [cachedAt, setCachedAt] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const generation = useRef(0);
  const controller = useRef<AbortController | null>(null);
  const hasData = useRef(false);
  const loadedContext = useRef<string | null>(null);
  const preparedContext = useRef<string | null>(null);
  const snapshotCache = useRef(new Map<string, DailySnapshotHit<StockCockpitSnapshot>>());
  const contextKey = symbol ? `${symbol}:${asOf || "live"}` : null;
  const cacheScope = asOf ? `stock-cockpit:${asOf}` : "stock-cockpit";
  const loadRef = useRef(load); const loadAIRef = useRef(loadAI); const prepareRef = useRef(prepare); const snapshotRef = useRef(onSnapshot);
  loadRef.current = load; loadAIRef.current = loadAI; prepareRef.current = prepare; snapshotRef.current = onSnapshot;
  const refreshRef = useRef<(() => Promise<void>) | null>(null);
  const loadingRef = useRef(false);

  const refresh = useCallback(async () => {
    if (!symbol) return;
    if (loadingRef.current && !controller.current?.signal.aborted) return;
    const request = ++generation.current;
    controller.current?.abort();
    const nextController = new AbortController();
    controller.current = nextController;
    loadingRef.current = true;
    setLoading(true); setError(""); setUpdatedAt(null);
    setLoadProgress({ percent: 1, stage: "connecting", detail: "正在连接本地个股数据服务" });
    try {
      const next = await loadRef.current(
        symbol,
        asOf || undefined,
        nextController.signal,
        (progress) => {
          if (request === generation.current && !nextController.signal.aborted) setLoadProgress(progress);
        },
      );
      if (request !== generation.current || nextController.signal.aborted) return;
      const cached = writeDailySnapshot(cacheScope, symbol, next);
      if (contextKey) snapshotCache.current.set(contextKey, cached);
      setCachedAt(cached.cachedAt); setUpdatedAt(cached.cachedAt);
      setData(next); snapshotRef.current?.(next); loadedContext.current = contextKey; hasData.current = true; setStale(false);
      setLoadProgress({ percent: 100, stage: "complete", detail: "最新个股观察数据已载入" });
      setLoading(false);
      if (next.ai_status === "deferred" && loadAIRef.current) {
        void loadAIRef.current(symbol, asOf || undefined, nextController.signal).then((withAI) => {
          if (request !== generation.current || nextController.signal.aborted) return;
          setData((current) => {
            if (!current || current.symbol !== symbol) return current;
            const enriched = {
              ...current,
              ai_status: withAI.ai_status,
              ai_explanation: withAI.ai_explanation,
            };
            const enrichedCache = writeDailySnapshot(cacheScope, symbol, enriched);
            if (contextKey) snapshotCache.current.set(contextKey, enrichedCache);
            return enriched;
          });
        }).catch(() => {
          if (request !== generation.current || nextController.signal.aborted) return;
          setData((current) => current?.symbol === symbol && current.ai_status === "deferred"
            ? { ...current, ai_status: "http_error", ai_explanation: null }
            : current);
        });
      }
      if (!asOf && prepareRef.current && isAutoSyncEnabled() && preparedContext.current !== contextKey) {
        preparedContext.current = contextKey; setPreparing(true);
        try {
          const report = await prepareRef.current(symbol, nextController.signal);
          if (request !== generation.current || nextController.signal.aborted) return;
          setData((current) => {
            if (!current) return current;
            const updated = { ...current, preparation: report };
            const preparedCache = writeDailySnapshot(cacheScope, symbol, updated);
            if (contextKey) snapshotCache.current.set(contextKey, preparedCache);
            return updated;
          });
          if (report.refreshed) {
            const refreshed = await loadRef.current(symbol, undefined, nextController.signal);
            if (request !== generation.current || nextController.signal.aborted) return;
            setData((current) => {
              const merged = current?.symbol === refreshed.symbol && current.ai_status !== "deferred"
                ? { ...refreshed, ai_status: current.ai_status, ai_explanation: current.ai_explanation }
                : refreshed;
              const refreshedCache = writeDailySnapshot(cacheScope, symbol, merged);
              if (contextKey) snapshotCache.current.set(contextKey, refreshedCache);
              return merged;
            });
            snapshotRef.current?.(refreshed);
          }
        } catch (caught) {
          if (request === generation.current && !nextController.signal.aborted) setError(friendlyError(caught, "数据同步"));
        } finally { if (request === generation.current) setPreparing(false); }
      }
    } catch (caught) {
      if (request !== generation.current || nextController.signal.aborted) return;
      setError(friendlyError(caught, "股票分析"));
      setStale(hasData.current);
    } finally {
      if (request === generation.current) {
        loadingRef.current = false;
        setLoading(false);
      }
    }
  }, [asOf, cacheScope, contextKey, symbol]);
  refreshRef.current = refresh;

  useEffect(() => {
    if (!symbol) { generation.current += 1; controller.current?.abort(); setData(null); loadedContext.current = null; preparedContext.current = null; hasData.current = false; setError(""); setStale(false); setCachedAt(null); setUpdatedAt(null); setLoadProgress(null); return; }
    if (loadedContext.current !== contextKey) {
      const persistent = readDailySnapshot<StockCockpitSnapshot>(cacheScope, symbol);
      const cached = persistent ?? (contextKey ? snapshotCache.current.get(contextKey) ?? null : null);
      setData(cached?.value ?? null);
      setCachedAt(cached?.cachedAt ?? null);
      setUpdatedAt(null);
      loadedContext.current = cached ? contextKey : null;
      preparedContext.current = null;
      hasData.current = cached !== null;
      setStale(false);
    }
    void refresh();
    return () => controller.current?.abort();
  }, [contextKey, refresh, refreshToken, symbol]);

  useEffect(() => {
    if (!symbol) return;
    const refreshIfVisible = () => {
      if (document.visibilityState === "visible") void refreshRef.current?.();
    };
    const interval = window.setInterval(refreshIfVisible, 30_000);
    document.addEventListener("visibilitychange", refreshIfVisible);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener("visibilitychange", refreshIfVisible);
    };
  }, [contextKey, symbol]);

  if (!symbol) return <main className="terminal-page stock-cockpit empty-cockpit"><Target size={24} /><h1>先选择一只 A 股</h1><p>从左侧候选池、自选或代码与名称搜索中选择，系统不会猜测股票。</p></main>;
  if (data && data.symbol !== symbol) return <main className="terminal-page stock-cockpit cockpit-loading" aria-busy="true"><RefreshCw size={22} /><h1>正在切换股票</h1><p>{symbol}</p></main>;
  if (!data && loading) return <main className="terminal-page stock-cockpit cockpit-loading" aria-busy="true"><RefreshCw size={22} /><h1>正在组装单股决策底稿</h1><p>{symbol}</p><DailyRefreshStatus label="个股观察" loading progress={loadProgress} /></main>;
  if (!data) return <main className="terminal-page stock-cockpit cockpit-loading"><AlertTriangle size={22} /><h1>驾驶舱暂不可用</h1><p role="alert">{error}</p><button type="button" onClick={() => void refresh()}>重试</button></main>;

  const change = numericOrNull(metric(data, "change_percent"));
  const positive = change !== null && change >= 0;
  const fallbackPreparationPartial = !data.preparation && ["market", "trend", "fundamentals", "news", "industry", "funds"]
    .some((section) => data.sections[section]?.status !== "ready");
  const preparationIncomplete = preparing || data.preparation?.status === "partial" || fallbackPreparationPartial;
  return <main className="terminal-page stock-cockpit">
    <header className="cockpit-identity"><div><p className="eyebrow">个股观察 / {data.instrument.exchange.toUpperCase()}</p><h1>{data.instrument.name} <span>{data.symbol}</span></h1><div className="cockpit-quote"><strong>{displayNumber(metric(data, "latest_price"))}</strong><span className={change === null ? undefined : positive ? "positive" : "negative"}>{change !== null ? positive ? <TrendingUp size={15} /> : <TrendingDown size={15} /> : null}{displayPercent(metric(data, "change_percent"))}</span></div></div>
      <div className="cockpit-tools">
        <div className={`cockpit-quality quality-${data.overall_quality}`}>{onOpenCompanyResearch && <button className="company-research-jump" type="button" aria-label="进入公司研究" onClick={() => onOpenCompanyResearch(data.symbol)}><Building2 size={17} /><span>进入公司研究</span><small>同一只股票 · 一键切换</small></button>}<div><Clock3 size={15} /><span>行情时间</span><b>{data.sections.market?.observed_at ? new Date(data.sections.market.observed_at).toLocaleString("zh-CN", { hour12: false }) : "未提供"}</b></div><div className={`market-${data.sections.market?.status ?? "unavailable"}`}><span>快照质量</span><b>{qualityNames[data.overall_quality]}</b><small>{data.sections.market ? sectionQualityNames[data.sections.market.status] : "行情不可用"}</small>{loading && <small className="cockpit-refreshing">后台更新中</small>}</div><button type="button" aria-label="刷新驾驶舱" onClick={() => onRefreshRequest ? onRefreshRequest() : void refresh()} disabled={loading}><RefreshCw size={15} className={loading ? "spin" : ""} /></button></div>
      </div>
    </header>
    <DailyRefreshStatus label="个股观察" cachedAt={cachedAt} loading={loading} completion={preparationIncomplete ? "partial" : "live"} progress={loadProgress} error={data ? error : null} updatedAt={updatedAt} />
    {error && <div className="cockpit-error" role="alert"><AlertTriangle size={16} /><span>{error}</span>{stale && <b>当前内容已陈旧</b>}</div>}
    <PreparationStatus data={data} preparing={preparing} />
    {loadAlerts && <BreakingNewsStrip {...alertState} />}
    {loadTimeline && <StockEventKline
      symbol={data.symbol}
      asOf={asOf}
      refreshToken={data.sections.news?.snapshot_id ?? refreshToken}
      load={loadTimeline}
    />}
    <EvidenceDecisionSummary data={data} candidateSentiment={candidateSentiment?.symbol === data.symbol ? candidateSentiment : null} />
    {source === "watchlist" && loadMarketSentiment && <WatchlistMarketSentiment load={loadMarketSentiment} />}
    {candidateSentiment?.symbol === data.symbol && (
      <CandidateSentimentPanel sentiment={candidateSentiment} />
    )}
    <PhaseTimeline phases={data.phases} symbol={data.symbol} />
    <CockpitSections sections={data.sections} />
  </main>;
}
