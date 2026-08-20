import { lazy, type FormEvent, Suspense, useEffect, useState } from "react";
import {
  Activity, Archive, BarChart3, BookOpenCheck, Boxes, BriefcaseBusiness, Building2,
  ChevronRight, CircleDollarSign, Database, Gauge, Landmark, Radar, Search,
  RefreshCw, ShieldAlert, ShieldCheck, Siren, Workflow,
} from "lucide-react";

import { DataStatusPanel } from "../data-status/DataStatusPanel";
import type { DataStatusState, SyncReport } from "../data-status/types";
import type { BacktestRunner } from "../backtest/types";
import type { ResearchCard } from "./types";
import type { AuditStatus, ComplianceStatus, RiskStatus } from "../governance/GovernanceViews";
import type { BondCandidates, BondDashboard, BondDiagnosis, BondDiagnosisBatch } from "../convertible-bonds/types";
import type { CorrectionInput, EventImpactReport, NewsIntelligenceBundle } from "../news-intelligence/types";
import type { BackupRecord, BackupVerification, CacheCleanupResult, CleanupPreview, ObservabilitySnapshot, OperationsDiagnostics, OperationsStatus, PerformanceSummary } from "../operations/types";
import type { AShareDiagnosis, CandidateBoard, CandidateScoreLoader } from "../a-shares/types";
import type { DecisionResponse } from "../decision-workbench/types";
import type { MarketSentimentResponse, MarketSentimentSnapshot } from "../market-sentiment/types";
import type {
  CandidateSentimentBatch,
  CandidateSentimentLoader,
  CandidateSentimentSnapshot,
} from "../candidate-sentiment/types";
import { StockSelector } from "../stock-cockpit/StockSelector";
import { StockDecisionCockpit } from "../stock-cockpit/StockDecisionCockpit";
import type { InstrumentSearchResponse, StockCockpitSnapshot } from "../stock-cockpit/types";
import { commitLocation } from "../instrument-selection/location";
import { useOptionalSelectedInstrument, useSelectedInstrument } from "../instrument-selection/SelectedInstrumentProvider";
import { loadWorkspaceState, saveWorkspaceState } from "../../shared/workspace/workspaceState";
import { BeginnerNavigation, type BeginnerView } from "../beginner-shell/BeginnerNavigation";
import type { FirstLimitUpBoard } from "../first-limit-up/types";
import type { DecisionJournalCreator, DecisionJournalLoader, QuantCalibrationLoader, QuantForecastLoader, QuantShadowAnalyticsLoader, QuantShadowLoader, QuantStrategyLoader, QuantTickLoader, QuantWalkForwardLoader, TdxFormulaLoader } from "../quant-analysis/types";
import { MarketOverviewView } from "../market-overview/MarketOverviewView";
import type { MarketIntervalReviewLoader, MarketOverviewLoader } from "../market-overview/types";
import type { StockTimelineLoader } from "../stock-timeline/types";
import type { BreakingNewsAlertLoader } from "../news-alerts/types";
import type { PortfolioPositionRemover, PortfolioPositionSaver, PortfolioRiskAnalyzer, PortfolioRiskLoader, WatchlistRiskLoader } from "../portfolio-risk/types";
import type { CompanyResearchComparison } from "../company-research/api";
import type { CompanyResearchResponse } from "../company-research/types";
import type { LateSessionSelectionLoader } from "../late-session-selection/types";
import { scheduleRoutePreload } from "./routePreload";
import type {
  SpeechSettingsLoader,
  SpeechSettingsSaver,
  SpeechSynthesizer,
  SpeechVoiceLoader,
} from "../speech/types";
import type {
  AShareUniverseSyncLoader,
  AISettingsDeleter,
  AISettingsLoader,
  AISettingsSaver,
  HistoryCoverageLoader,
  HistorySupplementLoader,
  HistorySupplementStarter,
  HistoryRepairCenterLoader,
  HistorySyncController,
  HistorySyncLoader,
  HistorySyncStarter,
  OfficialTdxInfoLoader,
  LocalSourceSettingsLoader,
  LocalSourceSettingsWriter,
  PreparationLoader,
  SourceHealthLoader,
} from "../data-settings/types";

const loadConvertibleBondModule = () => import("../convertible-bonds/ConvertibleBondView");
const loadNewsIntelligenceModule = () => import("../news-intelligence/NewsIntelligenceView");
const loadTodayDecisionModule = () => import("../decision-workbench/TodayDecisionView");
const loadFirstLimitUpModule = () => import("../first-limit-up/FirstLimitUpView");
const loadLateSessionSelectionModule = () => import("../late-session-selection/LateSessionSelectionView");
const loadQuantAnalysisModule = () => import("../quant-analysis/QuantAnalysisDashboard");
const loadCompanyResearchModule = () => import("../company-research/CompanyResearchView");
const loadBeginnerRiskModule = () => import("../beginner-shell/BeginnerRiskView");
const loadHistoryReviewModule = () => import("../beginner-shell/HistoryReview");
const loadDataSettingsModule = () => import("../data-settings/DataSettingsView");
const loadOperationsModule = () => import("../operations/OperationsView");

const ConvertibleBondView = lazy(() => loadConvertibleBondModule().then(({ ConvertibleBondView: view }) => ({ default: view })));
const NewsIntelligenceView = lazy(() => loadNewsIntelligenceModule().then(({ NewsIntelligenceView: view }) => ({ default: view })));
const TodayDecisionView = lazy(() => loadTodayDecisionModule().then(({ TodayDecisionView: view }) => ({ default: view })));
const FirstLimitUpView = lazy(() => loadFirstLimitUpModule().then(({ FirstLimitUpView: view }) => ({ default: view })));
const LateSessionSelectionView = lazy(() => loadLateSessionSelectionModule().then(({ LateSessionSelectionView: view }) => ({ default: view })));
const QuantAnalysisDashboard = lazy(() => loadQuantAnalysisModule().then(({ QuantAnalysisDashboard: view }) => ({ default: view })));
const CompanyResearchView = lazy(() => loadCompanyResearchModule().then(({ CompanyResearchView: view }) => ({ default: view })));
const BeginnerRiskView = lazy(() => loadBeginnerRiskModule().then(({ BeginnerRiskView: view }) => ({ default: view })));
const HistoryReview = lazy(() => loadHistoryReviewModule().then(({ HistoryReview: view }) => ({ default: view })));
const DataSettingsView = lazy(() => loadDataSettingsModule().then(({ DataSettingsView: view }) => ({ default: view })));
const OperationsView = lazy(() => loadOperationsModule().then(({ OperationsView: view }) => ({ default: view })));

const primaryRoutePreloaders = [
  loadTodayDecisionModule,
  loadCompanyResearchModule,
  loadFirstLimitUpModule,
  loadQuantAnalysisModule,
  loadNewsIntelligenceModule,
  loadBeginnerRiskModule,
  loadHistoryReviewModule,
  loadDataSettingsModule,
  loadOperationsModule,
  loadConvertibleBondModule,
];

type ViewState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; card: ResearchCard }
  | { kind: "error"; message: string };

type Props = {
  loadSnapshot: (symbol: string) => Promise<ResearchCard>;
  syncHistory?: (symbol: string, limit?: number) => Promise<SyncReport>;
  runBacktest?: BacktestRunner;
  loadRisk?: () => Promise<RiskStatus>; loadCompliance?: (asset?: "a_share" | "convertible_bond") => Promise<ComplianceStatus>; loadAudit?: () => Promise<AuditStatus>;
  analyzePortfolioRisk?: PortfolioRiskAnalyzer;
  loadWatchlistRisk?: WatchlistRiskLoader;
  loadPortfolioRisk?: PortfolioRiskLoader;
  savePortfolioPosition?: PortfolioPositionSaver;
  removePortfolioPosition?: PortfolioPositionRemover;
  complianceAction?: (source: string, action: "authorize" | "revoke" | "acknowledge", permissionReference?: string, asset?: "a_share" | "convertible_bond") => Promise<unknown>;
  loadBondDashboard?: () => Promise<BondDashboard>;
  loadBondDiagnosis?: (code: string) => Promise<BondDiagnosis>;
  loadCachedBondDiagnosis?: (code: string) => Promise<BondDiagnosis | null>;
  loadBondCandidates?: (filters?: Record<string, string>) => Promise<BondCandidates>;
  diagnoseBondBatch?: (limit?: number) => Promise<BondDiagnosisBatch>;
  loadNewsIntelligence?: () => Promise<NewsIntelligenceBundle>;
  loadEventImpact?: (eventId: string) => Promise<EventImpactReport>;
  syncNews?: (symbol?: string | null) => Promise<Record<string, number>>;
  syncHotspots?: () => Promise<Record<string, number>>;
  createNewsCorrection?: (input: CorrectionInput) => Promise<unknown>;
  loadOperationsStatus?: () => Promise<OperationsStatus>;
  loadOperationsDiagnostics?: () => Promise<OperationsDiagnostics>;
  loadObservability?: () => Promise<ObservabilitySnapshot>;
  setSchedulerPaused?: (paused: boolean) => Promise<OperationsStatus["scheduler"]>;
  createBackup?: () => Promise<BackupRecord>;
  verifyBackup?: (backupId: string) => Promise<BackupVerification>;
  runManualJob?: (phase: string, tradingDate: string) => Promise<{ report_id: string }>;
  cleanupCache?: (olderThanHours: number) => Promise<CacheCleanupResult>;
  loadAShareCandidates?: () => Promise<CandidateBoard>;
  loadAShareCandidateScores?: CandidateScoreLoader;
  loadAShareDiagnosis?: (symbol: string, asOf?: string) => Promise<AShareDiagnosis>;
  loadDecisionCurrent?: () => Promise<DecisionResponse>;
  loadDecisionDate?: (date: string) => Promise<DecisionResponse>;
  loadMarketSentiment?: () => Promise<MarketSentimentResponse>;
  refreshMarketSentiment?: () => Promise<MarketSentimentSnapshot>;
  loadCandidateSentiments?: CandidateSentimentLoader;
  refreshCandidateSentiments?: CandidateSentimentLoader;
  searchAShareInstruments?: (query: string) => Promise<InstrumentSearchResponse>;
  loadStockCockpit?: (symbol: string, asOf?: string, signal?: AbortSignal) => Promise<StockCockpitSnapshot>;
  loadStockCockpitAI?: (symbol: string, asOf?: string, signal?: AbortSignal) => Promise<StockCockpitSnapshot>;
  loadStockTimeline?: StockTimelineLoader;
  prepareStockData?: PreparationLoader;
  loadAISettings?: AISettingsLoader;
  saveAISettings?: AISettingsSaver;
  deleteAISettings?: AISettingsDeleter;
  loadLocalSourceSettings?: LocalSourceSettingsLoader;
  detectLocalSourceSettings?: LocalSourceSettingsWriter;
  saveLocalSourceSettings?: LocalSourceSettingsWriter;
  syncAShareUniverse?: AShareUniverseSyncLoader;
  loadSourceHealth?: SourceHealthLoader;
  loadHistorySync?: HistorySyncLoader;
  loadHistoryCoverage?: HistoryCoverageLoader;
  loadHistoryRepairCenter?: HistoryRepairCenterLoader;
  loadHistoryRepairAudits?: import("../data-settings/types").HistoryRepairAuditLoader;
  startHistoryBackfill?: HistorySyncStarter;
  pauseHistorySync?: HistorySyncController;
  resumeHistorySync?: HistorySyncController;
  retryFailedHistory?: HistorySyncController;
  restartCurrentHistory?: HistorySyncStarter;
  loadOfficialTdxInfo?: OfficialTdxInfoLoader;
  loadHistorySupplement?: HistorySupplementLoader;
  startOfficialTdxSupplement?: HistorySupplementStarter;
  loadTdxImport?: import("../data-settings/types").TdxImportLoader;
  scanTdxImport?: import("../data-settings/types").TdxImportScanner;
  startTdxImport?: import("../data-settings/types").TdxImportStarter;
  pauseTdxImport?: import("../data-settings/types").TdxImportController;
  resumeTdxImport?: import("../data-settings/types").TdxImportController;
  loadFirstLimitUp?: () => Promise<FirstLimitUpBoard>;
  refreshFirstLimitUp?: () => Promise<FirstLimitUpBoard>;
  loadLateSessionSelection?: LateSessionSelectionLoader;
  loadQuantTicks?: QuantTickLoader;
  loadKronosForecast?: QuantForecastLoader;
  loadWalkForward?: QuantWalkForwardLoader;
  loadQuantStrategy?: QuantStrategyLoader;
  loadQuantShadowDecisions?: QuantShadowLoader;
  loadQuantShadowAnalytics?: QuantShadowAnalyticsLoader;
  loadQuantCalibration?: QuantCalibrationLoader;
  loadDecisionJournal?: DecisionJournalLoader;
  createDecisionJournal?: DecisionJournalCreator;
  loadTdxFormula?: TdxFormulaLoader;
  loadMarketOverview?: MarketOverviewLoader;
  loadMarketIntervalReview?: MarketIntervalReviewLoader;
  loadBreakingNewsAlerts?: BreakingNewsAlertLoader;
  loadSpeechSettings?: SpeechSettingsLoader;
  loadSpeechVoices?: SpeechVoiceLoader;
  saveSpeechSettings?: SpeechSettingsSaver;
  synthesizeSpeech?: SpeechSynthesizer;
  loadCompanyResearch?: (symbol: string, asOf?: string, signal?: AbortSignal) => Promise<CompanyResearchResponse>;
  compareCompanyResearch?: (symbols: string[], asOf?: string) => Promise<CompanyResearchComparison>;
  previewStorageCleanup?: (olderThanHours: number) => Promise<CleanupPreview>;
  cleanupStorage?: (olderThanHours: number) => Promise<CacheCleanupResult>;
  loadPerformanceSummary?: () => Promise<PerformanceSummary>;
};

type ActiveView = BeginnerView;

export function preparationForSymbol(snapshot: StockCockpitSnapshot | null, symbol: string | null) {
  return snapshot?.symbol === symbol ? snapshot.preparation ?? null : null;
}

export function candidateSentimentForSymbol(
  batch: CandidateSentimentBatch | null,
  symbol: string | null,
): CandidateSentimentSnapshot | null {
  if (!batch || !symbol) return null;
  return batch.items.find((item) => item.symbol === symbol) ?? null;
}

function viewFromPath(path: string): ActiveView {
  if (path === "/" || path === "/market-overview") return "market_overview";
  if (path === "/today-decision") return "dashboard";
  if (path === "/a-shares") return "a_shares";
  if (path === "/company-research") return "company_research";
  if (path === "/first-limit-up/quant-analysis") return "quant_analysis";
  if (path === "/first-limit-up") return "first_limit_up";
  if (path === "/late-session-selection") return "late_session_selection";
  if (path === "/convertible-bonds") return "bonds";
  if (path === "/news-intelligence") return "news";
  if (path === "/risk") return "risk";
  if (path === "/history") return "history";
  if (path === "/settings") return "settings";
  if (path === "/operations") return "operations";
  return "market_overview";
}

const pathsForView: Record<ActiveView, string> = {
  market_overview: "/market-overview", dashboard: "/today-decision", a_shares: "/a-shares",
  company_research: "/company-research", first_limit_up: "/first-limit-up",
  late_session_selection: "/late-session-selection",
  quant_analysis: "/first-limit-up/quant-analysis", risk: "/risk", history: "/history",
  settings: "/settings", operations: "/operations", bonds: "/convertible-bonds", news: "/news-intelligence",
};

const sourceNames: Record<string, string> = { tencent: "腾讯行情" };

function formatObservedAt(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).format(new Date(value));
}

function ResearchPanel({ card }: { card: ResearchCard }) {
  const blocked = card.action === "blocked";
  const positive = Number(card.change_percent) >= 0;
  return (
    <section className={`research-panel ${blocked ? "is-blocked" : "is-ready"}`}>
      <div className="panel-heading">
        <div>
          <p className="eyebrow">A 股 / 实时快照</p>
          <div className="symbol-line">
            <h2>{card.symbol}</h2>
            <span className={`change ${positive ? "positive" : "negative"}`}>
              {positive ? "+" : ""}{card.change_percent}%
            </span>
          </div>
        </div>
        <div className={`decision-state ${blocked ? "blocked" : "ready"}`} role="status">
          {blocked ? <ShieldAlert size={16} /> : <ShieldCheck size={16} />}
          {blocked ? "仅观察" : "数据有效"}
        </div>
      </div>
      <div className="evidence-grid">
        {card.evidence.map((item) => (
          <article className="evidence-item" key={`${item.label}-${item.observed_at}`}>
            <p>{item.label}</p><strong>{item.value}</strong>
            <div className="evidence-meta">
              <span>{sourceNames[item.source] ?? item.source}</span>
              <span>数据截至 {formatObservedAt(item.observed_at)}</span>
            </div>
          </article>
        ))}
        <article className="evidence-item muted-item">
          <p>结论等级</p><strong>{blocked ? "信号拦截" : "行情观察"}</strong>
          <div className="evidence-meta"><span>不构成买卖建议</span></div>
        </article>
      </div>
      {card.invalid_reasons.length > 0 && (
        <div className="risk-notice">
          <ShieldAlert size={18} />
          <div><b>风险规则已拦截</b>{card.invalid_reasons.map((reason) => <p key={reason}>{reason}</p>)}</div>
        </div>
      )}
    </section>
  );
}

function SelectedNewsWorkspace({ loadBundle, loadEventImpact, syncNews, syncHotspots, createCorrection, openNewsCompliance }: {
  loadBundle: () => Promise<NewsIntelligenceBundle>; syncNews: (symbol?: string | null) => Promise<Record<string, number>>;
  loadEventImpact?: (eventId: string) => Promise<EventImpactReport>;
  syncHotspots?: () => Promise<Record<string, number>>;
  createCorrection: (input: CorrectionInput) => Promise<unknown>; openNewsCompliance: () => void;
}) {
  const { symbol } = useSelectedInstrument();
  return <NewsIntelligenceView selectedSymbol={symbol} loadBundle={loadBundle} syncNews={syncNews} syncHotspots={syncHotspots} createCorrection={createCorrection} loadEventImpact={loadEventImpact} openNewsCompliance={openNewsCompliance} />;
}

export function RouteLoadingFallback() {
  return (
    <main className="beginner-page route-loading-fallback" role="status" aria-label="页面准备状态" aria-busy="true">
      <span className="pulse-dot" aria-hidden="true" />
      <h1>页面准备中</h1>
      <p>数据请求已在后台启动。</p>
    </main>
  );
}

export function Dashboard({ loadSnapshot, syncHistory, runBacktest, loadRisk, analyzePortfolioRisk, loadWatchlistRisk, loadPortfolioRisk, savePortfolioPosition, removePortfolioPosition, loadCompliance, loadAudit, complianceAction, loadBondDashboard, loadBondDiagnosis, loadCachedBondDiagnosis, loadBondCandidates, diagnoseBondBatch, loadNewsIntelligence, loadEventImpact, syncNews, syncHotspots, createNewsCorrection, loadOperationsStatus, loadOperationsDiagnostics, loadObservability, setSchedulerPaused, createBackup, verifyBackup, runManualJob, cleanupCache, previewStorageCleanup, cleanupStorage, loadPerformanceSummary, loadAShareCandidates, loadAShareCandidateScores, loadAShareDiagnosis, loadDecisionCurrent, loadDecisionDate, loadMarketSentiment, refreshMarketSentiment, loadCandidateSentiments, refreshCandidateSentiments, searchAShareInstruments, loadStockCockpit, loadStockCockpitAI, loadStockTimeline, prepareStockData, loadAISettings, saveAISettings, deleteAISettings, loadLocalSourceSettings, detectLocalSourceSettings, saveLocalSourceSettings, syncAShareUniverse, loadSourceHealth, loadHistorySync, loadHistoryCoverage, loadHistoryRepairCenter, loadHistoryRepairAudits, startHistoryBackfill, pauseHistorySync, resumeHistorySync, retryFailedHistory, restartCurrentHistory, loadOfficialTdxInfo, loadHistorySupplement, startOfficialTdxSupplement, loadTdxImport, scanTdxImport, startTdxImport, pauseTdxImport, resumeTdxImport, loadFirstLimitUp, refreshFirstLimitUp, loadLateSessionSelection, loadQuantTicks, loadKronosForecast, loadWalkForward, loadQuantStrategy, loadQuantShadowDecisions, loadQuantShadowAnalytics, loadQuantCalibration, loadDecisionJournal, createDecisionJournal, loadTdxFormula, loadMarketOverview, loadMarketIntervalReview, loadBreakingNewsAlerts, loadSpeechSettings, loadSpeechVoices, saveSpeechSettings, synthesizeSpeech, loadCompanyResearch, compareCompanyResearch }: Props) {
  const selectedInstrument = useOptionalSelectedInstrument();
  const [state, setState] = useState<ViewState>({ kind: "idle" });
  const [symbol, setSymbol] = useState("600000");
  const [dataState, setDataState] = useState<DataStatusState>({ kind: "idle" });
  const [activeView, setActiveView] = useState<ActiveView>(() => {
    if (window.location.pathname === "/") {
      const restored = loadWorkspaceState();
      if (restored?.route) return viewFromPath(restored.route);
    }
    return viewFromPath(window.location.pathname);
  });
  const [cockpitRefreshToken, setCockpitRefreshToken] = useState(0);
  const [latestCockpit, setLatestCockpit] = useState<StockCockpitSnapshot | null>(null);
  const [candidateSentiments, setCandidateSentiments] = useState<CandidateSentimentBatch | null>(null);
  const selectedSymbol = selectedInstrument?.symbol ?? selectedInstrument?.lastSymbol ?? null;
  const selectedCandidateSentiment = candidateSentimentForSymbol(
    candidateSentiments,
    selectedSymbol,
  );
  useEffect(() => {
    if (window.location.pathname !== "/") return;
    const restored = loadWorkspaceState();
    if (!restored?.route || restored.route === "/" || restored.route === "/market-overview") return;
    const next = new URL(restored.route, window.location.origin);
    if (restored.symbol && restored.route !== "/convertible-bonds") next.searchParams.set("symbol", restored.symbol);
    window.history.replaceState({}, "", `${next.pathname}${next.search}`);
  }, []);
  useEffect(() => { if (latestCockpit && latestCockpit.symbol !== selectedSymbol) setLatestCockpit(null); }, [latestCockpit, selectedSymbol]);
  useEffect(() => {
    const syncPath = () => setActiveView(viewFromPath(window.location.pathname));
    window.addEventListener("popstate", syncPath);
    return () => window.removeEventListener("popstate", syncPath);
  }, []);
  useEffect(() => {
    if (import.meta.env.MODE === "test") return undefined;
    return scheduleRoutePreload(primaryRoutePreloaders);
  }, []);
  useEffect(() => {
    if (activeView !== "a_shares") setCandidateSentiments(null);
  }, [activeView]);
  useEffect(() => {
    const restored = loadWorkspaceState();
    if (import.meta.env.MODE !== "test" && restored?.route === pathsForView[activeView] && restored.scrollTop > 0) {
      window.requestAnimationFrame(() => window.scrollTo({ top: restored.scrollTop, behavior: "auto" }));
    }
    const saveScroll = () => saveWorkspaceState({
      route: pathsForView[activeView], menu: activeView,
      symbol: selectedSymbol, scrollTop: window.scrollY,
    });
    window.addEventListener("scroll", saveScroll, { passive: true });
    return () => window.removeEventListener("scroll", saveScroll);
  }, [activeView, selectedSymbol]);
  function navigate(view: ActiveView) {
    const next = new URL(pathsForView[view], window.location.origin);
    const selectedSymbol = new URL(window.location.href).searchParams.get("symbol") ?? selectedInstrument?.lastSymbol;
    if (view !== "bonds" && selectedSymbol) next.searchParams.set("symbol", selectedSymbol);
    commitLocation(`${next.pathname}${next.search}`);
    saveWorkspaceState({ route: next.pathname, menu: view, symbol: selectedSymbol ?? null, scrollTop: 0 });
    setActiveView(view);
  }

  function openOverviewStock(symbol: string) {
    commitLocation(`/a-shares?symbol=${encodeURIComponent(symbol)}`);
    saveWorkspaceState({ route: "/a-shares", menu: "a_shares", symbol, scrollTop: 0 });
    setActiveView("a_shares");
  }

  function openCompanyResearch(symbol: string) {
    commitLocation(`/company-research?symbol=${encodeURIComponent(symbol)}`);
    saveWorkspaceState({ route: "/company-research", menu: "company_research", symbol, scrollTop: 0 });
    setActiveView("company_research");
  }

  function openQuantAnalysis(symbol: string) {
    commitLocation(`/first-limit-up/quant-analysis?symbol=${encodeURIComponent(symbol)}`);
    saveWorkspaceState({ route: "/first-limit-up/quant-analysis", menu: "quant_analysis", symbol, scrollTop: 0 });
    setActiveView("quant_analysis");
  }

  async function inspect(requestedSymbol: string) {
    setState({ kind: "loading" });
    try {
      setState({ kind: "ready", card: await loadSnapshot(requestedSymbol) });
    } catch (error) {
      setState({ kind: "error", message: error instanceof Error ? error.message : "未知错误" });
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void inspect(symbol);
  }

  async function syncDailyBars() {
    if (!syncHistory) return;
    setDataState({ kind: "syncing" });
    try {
      const report = await syncHistory(symbol, 250);
      if (report.state === "ready") setDataState({ kind: "ready", report });
      else setDataState({ kind: "error", message: report.message });
    } catch (error) {
      setDataState({ kind: "error", message: error instanceof Error ? error.message : "未知错误" });
    }
  }

  return (
    <div className="app-shell">
      <BeginnerNavigation active={activeView} onNavigate={navigate} />

      {activeView === "market_overview" && loadMarketOverview && <MarketOverviewView load={loadMarketOverview} loadAlerts={loadBreakingNewsAlerts} onOpenAShare={openOverviewStock} onOpenCompanyResearch={openCompanyResearch} onOpenQuantAnalysis={openQuantAnalysis} synthesizeSpeech={synthesizeSpeech} loadIntervalReview={loadMarketIntervalReview} />}
      {activeView === "market_overview" && !loadMarketOverview && <main className="market-overview-page"><header className="overview-titlebar"><div><p>A-SHARE MARKET TERMINAL</p><h1>信息总览</h1></div></header><div className="overview-error"><ShieldAlert size={15} />信息总览服务暂不可用，请检查本地 API。</div></main>}

      {activeView === "risk" && <Suspense fallback={<RouteLoadingFallback />}><BeginnerRiskView load={loadRisk} analyzePortfolio={analyzePortfolioRisk} loadPortfolio={loadPortfolioRisk} savePortfolioPosition={savePortfolioPosition} removePortfolioPosition={removePortfolioPosition} selectedSymbol={selectedSymbol} loadWatchlistRisk={loadWatchlistRisk} /></Suspense>}

      {activeView === "a_shares" && <div className="stock-workbench-layout observation-workspace">
        {loadAShareCandidates && searchAShareInstruments && <StockSelector loadCandidates={loadAShareCandidates} loadWatchlistScores={loadAShareCandidateScores} prepare={prepareStockData} search={searchAShareInstruments} loadCandidateSentiments={loadCandidateSentiments} refreshCandidateSentiments={refreshCandidateSentiments} onCandidateSentiments={setCandidateSentiments} />}
        {loadStockCockpit ? <StockDecisionCockpit load={loadStockCockpit} loadAI={loadStockCockpitAI} loadTimeline={loadStockTimeline} loadAlerts={loadBreakingNewsAlerts} prepare={prepareStockData} refreshToken={cockpitRefreshToken} onSnapshot={setLatestCockpit} candidateSentiment={selectedCandidateSentiment} loadMarketSentiment={loadMarketSentiment} onOpenCompanyResearch={openCompanyResearch} /> : <main className="stock-cockpit empty-cockpit"><Radar size={24} /><h1>选择股票后查看行动卡</h1><p>可从候选、自选或搜索结果中选择任意已验证 A 股。</p></main>}
      </div>}

      {activeView === "company_research" && loadCompanyResearch && searchAShareInstruments && <Suspense fallback={<RouteLoadingFallback />}><CompanyResearchView load={loadCompanyResearch} search={searchAShareInstruments} compare={compareCompanyResearch} selectedSymbol={selectedSymbol} onSelectSymbol={(nextSymbol) => selectedInstrument?.select(nextSymbol, "search")} onOpenAShare={openOverviewStock} /></Suspense>}
      {activeView === "company_research" && (!loadCompanyResearch || !searchAShareInstruments) && <main className="company-research-page"><header className="research-hero"><div><p className="eyebrow">EVIDENCE-BASED RESEARCH</p><h1>公司研究</h1></div></header><section className="research-error"><ShieldAlert size={20} /><h2>公司研究服务暂不可用</h2><p>请检查本地 API、股票目录和财务数据源。</p></section></main>}

      {activeView === "first_limit_up" && loadFirstLimitUp && refreshFirstLimitUp && <Suspense fallback={<RouteLoadingFallback />}><FirstLimitUpView load={loadFirstLimitUp} refresh={refreshFirstLimitUp} /></Suspense>}
      {activeView === "first_limit_up" && (!loadFirstLimitUp || !refreshFirstLimitUp) && <main className="beginner-page"><header><p className="eyebrow">A 股 / 盘后筛选</p><h1>首次涨停</h1><p>首次涨停筛选服务暂不可用，请检查本地 API 和日线数据后重试。</p></header></main>}

      {activeView === "late_session_selection" && loadLateSessionSelection && <Suspense fallback={<RouteLoadingFallback />}><LateSessionSelectionView load={loadLateSessionSelection} /></Suspense>}
      {activeView === "late_session_selection" && !loadLateSessionSelection && <main className="beginner-page"><header><p className="eyebrow">A 股 / 尾盘筛选</p><h1>尾盘选股</h1><p>尾盘选股服务暂不可用，请检查本地行情和历史数据。</p></header></main>}

      {activeView === "quant_analysis" && loadFirstLimitUp && loadQuantTicks && runBacktest && <Suspense fallback={<RouteLoadingFallback />}><QuantAnalysisDashboard loadBoard={loadFirstLimitUp} refreshBoard={refreshFirstLimitUp} loadTicks={loadQuantTicks} runBacktest={runBacktest} loadKronosForecast={loadKronosForecast} loadWalkForward={loadWalkForward} loadQuantStrategy={loadQuantStrategy} loadQuantShadowDecisions={loadQuantShadowDecisions} loadQuantShadowAnalytics={loadQuantShadowAnalytics} loadQuantCalibration={loadQuantCalibration} loadDecisionJournal={loadDecisionJournal} createDecisionJournal={createDecisionJournal} loadTdxFormula={loadTdxFormula} loadTimeline={loadStockTimeline} selectedSymbol={selectedSymbol} searchInstruments={searchAShareInstruments} onSelectSymbol={(nextSymbol) => selectedInstrument?.select(nextSymbol, "search")} /></Suspense>}
      {activeView === "quant_analysis" && (!loadFirstLimitUp || !loadQuantTicks || !runBacktest) && <main className="quant-analysis-page"><header><p className="eyebrow">FIRST LIMIT-UP / QUANT LAB</p><h1>量化分析仪表盘</h1><p>量化证据链暂不完整，请检查首次涨停、盘中 TICK 与回测服务。</p></header></main>}

      {activeView === "bonds" && loadBondDashboard && loadBondDiagnosis && loadBondCandidates && <Suspense fallback={<RouteLoadingFallback />}><ConvertibleBondView loadDashboard={loadBondDashboard} loadDiagnosis={loadBondDiagnosis} loadCachedDiagnosis={loadCachedBondDiagnosis} loadCandidates={loadBondCandidates} diagnoseDiscovered={diagnoseBondBatch} openBondCompliance={() => navigate("settings")} /></Suspense>}

      {activeView === "news" && loadNewsIntelligence && syncNews && createNewsCorrection && <Suspense fallback={<RouteLoadingFallback />}><SelectedNewsWorkspace loadBundle={loadNewsIntelligence} loadEventImpact={loadEventImpact} syncNews={syncNews} syncHotspots={syncHotspots} createCorrection={createNewsCorrection} openNewsCompliance={() => navigate("settings")} /></Suspense>}

      {activeView === "history" && loadDecisionCurrent && <Suspense fallback={<RouteLoadingFallback />}><HistoryReview loadCurrent={loadDecisionCurrent} loadDate={loadDecisionDate} symbol={selectedInstrument?.symbol ?? selectedInstrument?.lastSymbol ?? null} runBacktest={runBacktest} /></Suspense>}

      {activeView === "settings" && loadAISettings && saveAISettings && deleteAISettings && <Suspense fallback={<RouteLoadingFallback />}><DataSettingsView loadAI={loadAISettings} saveAI={saveAISettings} deleteAI={deleteAISettings} loadLocalSources={loadLocalSourceSettings} detectLocalSources={detectLocalSourceSettings} saveLocalSources={saveLocalSourceSettings} loadSpeech={loadSpeechSettings} loadSpeechVoices={loadSpeechVoices} saveSpeech={saveSpeechSettings} synthesizeSpeech={synthesizeSpeech} symbol={selectedSymbol} prepare={prepareStockData} preparation={preparationForSymbol(latestCockpit, selectedSymbol)} loadCompliance={loadCompliance} complianceAction={complianceAction} syncAShareUniverse={syncAShareUniverse} loadSourceHealth={loadSourceHealth} onAIChanged={() => setCockpitRefreshToken((value) => value + 1)} /></Suspense>}
      {activeView === "settings" && (!loadAISettings || !saveAISettings || !deleteAISettings) && <main className="beginner-page"><header><p className="eyebrow">数据设置</p><h1>数据源与 AI</h1><p>设置服务暂不可用，请检查本地服务后重试。</p></header></main>}

      {activeView === "operations" && loadOperationsStatus && setSchedulerPaused && createBackup && verifyBackup && runManualJob && <Suspense fallback={<RouteLoadingFallback />}><OperationsView loadStatus={loadOperationsStatus} setSchedulerPaused={setSchedulerPaused} createBackup={createBackup} verifyBackup={verifyBackup} runManualJob={runManualJob} cleanupCache={cleanupCache} previewCleanup={previewStorageCleanup} cleanupStorage={cleanupStorage} loadPerformance={loadPerformanceSummary} loadDiagnostics={loadOperationsDiagnostics} loadObservability={loadObservability} loadHistoryRepairCenter={loadHistoryRepairCenter} loadHistoryRepairAudits={loadHistoryRepairAudits} startHistoryBackfill={startHistoryBackfill} pauseHistorySync={pauseHistorySync} resumeHistorySync={resumeHistorySync} loadOfficialTdxInfo={loadOfficialTdxInfo} loadHistorySupplement={loadHistorySupplement} startOfficialTdxSupplement={startOfficialTdxSupplement} loadTdxImport={loadTdxImport} scanTdxImport={scanTdxImport} startTdxImport={startTdxImport} pauseTdxImport={pauseTdxImport} resumeTdxImport={resumeTdxImport} /></Suspense>}
      {activeView === "operations" && (!loadOperationsStatus || !setSchedulerPaused || !createBackup || !verifyBackup || !runManualJob) && <main className="beginner-page"><header><p className="eyebrow">本地运维</p><h1>数据与运维中心</h1><p>运维服务暂不可用，请检查本地服务后重试。</p></header></main>}

      {activeView === "dashboard" && loadDecisionCurrent && <Suspense fallback={<RouteLoadingFallback />}><TodayDecisionView
        loadCurrent={loadDecisionCurrent}
        loadDate={loadDecisionDate}
        selectedSymbol={selectedSymbol}
        onOpenAShares={(alertSymbol) => alertSymbol ? openOverviewStock(alertSymbol) : navigate("a_shares")}
        loadSentiment={loadMarketSentiment}
        refreshSentiment={refreshMarketSentiment}
        loadAlerts={loadBreakingNewsAlerts}
      /></Suspense>}

      {activeView === "dashboard" && !loadDecisionCurrent && <main className="command-center beginner-fallback">
        <header className="topbar">
          <div><p className="eyebrow">今日研判</p><h1>个股观察</h1></div>
          <div className="system-state"><span className="pulse-dot" /><div><b>公开数据链路</b><small>等待选择股票</small></div></div>
        </header>
        <section className="mission-strip" aria-label="每日研究流程">
          <div className="mission active"><span>01</span><div><b>盘前研判</b><small>情报聚合 / 候选生成</small></div></div>
          <ChevronRight size={16} />
          <div className="mission"><span>02</span><div><b>盘中监测</b><small>量价异动 / 风险审查</small></div></div>
          <ChevronRight size={16} />
          <div className="mission"><span>03</span><div><b>盘后复核</b><small>信号归因 / 档案留存</small></div></div>
        </section>

        <div className="workspace-grid">
          <section className="primary-workspace">
            <div className="section-title">
              <div><p className="eyebrow">快速查询</p><h2>选择一只 A 股</h2></div>
            </div>
            <form className="symbol-search" onSubmit={submit}>
              <Search size={18} />
              <label className="visually-hidden" htmlFor="symbol">A 股代码</label>
              <input id="symbol" inputMode="numeric" maxLength={6} pattern="\d{6}" value={symbol} onChange={(event) => setSymbol(event.target.value.replace(/\D/g, ""))} />
              <span className="input-hint">输入六位 A 股代码</span>
              <button disabled={state.kind === "loading"} type="submit"><Radar size={16} />调取行情</button>
            </form>
            {state.kind === "idle" && <section className="empty-state"><Radar size={34} /><b>等待选择股票</b><p>输入 A 股代码后，系统会检查公开行情并给出观察结论。</p></section>}
            {state.kind === "loading" && <section className="loading-state" aria-busy="true"><span className="scanner" /><Activity size={20} />正在读取行情...</section>}
            {state.kind === "error" && <section className="error-state" role="alert"><ShieldAlert size={20} /><div><b>数据链路中断</b><p>{state.message}</p></div></section>}
            {state.kind === "ready" && <ResearchPanel card={state.card} />}
          </section>

          <aside className="right-rail">
            <section className="rail-section">
              <div className="rail-heading">
                <span>历史数据仓</span>
                <button className="rail-action" type="button" aria-label="同步历史日线" disabled={!syncHistory || dataState.kind === "syncing"} onClick={() => void syncDailyBars()}>
                  <RefreshCw size={14} />
                </button>
              </div>
              <DataStatusPanel state={dataState} />
            </section>
            <section className="rail-section">
              <div className="rail-heading"><span>处理进度</span><Archive size={15} /></div>
              <div className="event-line"><span className="event-node ready" /><div><b>行情</b><p>公开数据源待命</p></div><small>就绪</small></div>
              <div className="event-line"><span className="event-node" /><div><b>分析</b><p>等待选择股票</p></div><small>等待</small></div>
              <div className="event-line"><span className="event-node" /><div><b>风险</b><p>风险规则已加载</p></div><small>就绪</small></div>
            </section>
            <section className="rail-section protocol">
              <div className="rail-heading"><span>安全协议</span><ShieldCheck size={15} /></div>
              <ul><li>免费行情源可替换</li><li>超过三分钟自动拦截</li><li>所有快照进入审计库</li><li>不连接真实券商</li></ul>
            </section>
          </aside>
        </div>
      </main>}
    </div>
  );
}
