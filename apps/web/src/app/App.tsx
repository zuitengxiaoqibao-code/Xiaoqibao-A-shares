import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "@fontsource/orbitron/600.css";

import { Dashboard } from "../features/dashboard/Dashboard";
import { loadSnapshot } from "../features/dashboard/api";
import { syncHistory } from "../features/data-status/api";
import { runBacktest } from "../features/backtest/api";
import { complianceAction, loadAudit, loadCompliance, loadRisk } from "../features/governance/api";
import { diagnoseBondBatch, loadBondCandidates, loadBondDashboard, loadBondDiagnosis, loadCachedBondDiagnosis } from "../features/convertible-bonds/api";
import { createNewsCorrection, loadEventImpact, loadNewsIntelligence, syncHotspots, syncNews } from "../features/news-intelligence/api";
import { cleanupCache, cleanupStorage, createBackup, loadObservability, loadOperationsDiagnostics, loadOperationsStatus, loadPerformanceSummary, previewStorageCleanup, runManualJob, setSchedulerPaused, verifyBackup } from "../features/operations/api";
import { loadAShareCandidateScores, loadAShareCandidates, loadAShareDiagnosis } from "../features/a-shares/api";
import { loadCurrentDecision, loadDecisionDate } from "../features/decision-workbench/api";
import { SelectedInstrumentProvider } from "../features/instrument-selection/SelectedInstrumentProvider";
import { loadAShareInstrumentDirectory, loadStockCockpit, loadStockCockpitAI, loadStockQuotePulse, prepareStockData, searchAShareInstruments } from "../features/stock-cockpit/api";
import { useEffect } from "react";
import {
  deleteAISettings,
  loadAISettings,
  loadHistoryCoverage,
  loadHistoryRepairCenter,
  loadHistoryRepairAudits,
  loadHistorySync,
  loadLocalSourceSettings,
  detectLocalSourceSettings,
  saveLocalSourceSettings,
  loadSourceHealth,
  pauseHistorySync,
  resumeHistorySync,
  retryFailedHistory,
  restartCurrentHistory,
  loadOfficialTdxInfo,
  loadHistorySupplement,
  startOfficialTdxSupplement,
  saveAISettings,
  startHistoryBackfill,
  syncAShareUniverse,
  loadTdxImport,
  scanTdxImport,
  startTdxImport,
  pauseTdxImport,
  resumeTdxImport,
  loadExternalDataSources,
  saveExternalDataSource,
  clearExternalDataSource,
  testExternalDataSource,
} from "../features/data-settings/api";
import { loadCurrentMarketSentiment, refreshMarketSentiment } from "../features/market-sentiment/api";
import {
  loadCandidateSentiments,
  refreshCandidateSentiments,
} from "../features/candidate-sentiment/api";
import { loadFirstLimitUp, refreshFirstLimitUp } from "../features/first-limit-up/api";
import { loadLateSessionSelection } from "../features/late-session-selection/api";
import { createDecisionJournal, loadDecisionJournal, loadKronosForecast, loadQuantCalibration, loadQuantResearch, loadQuantShadowAnalytics, loadQuantShadowDecisions, loadQuantStrategy, loadQuantTicks, loadTdxFormula, loadWalkForward, registerWatchlistFocus } from "../features/quant-analysis/api";
import { loadMarketIntervalReview, loadMarketOverview } from "../features/market-overview/api";
import { loadStockTimeline } from "../features/stock-timeline/api";
import { loadBreakingNewsAlerts } from "../features/news-alerts/api";
import {
  loadSpeechSettings,
  loadSpeechVoices,
  saveSpeechSettings,
  synthesizeSpeech,
} from "../features/speech/api";
import { loadCompanyResearch, loadCompanyResearchComparison } from "../features/company-research/api";
import { analyzePortfolioRisk, loadPortfolioRisk, loadWatchlistRisk, removePortfolioPosition, savePortfolioPosition } from "../features/portfolio-risk/api";
import { A_SHARE_WATCHLIST_CHANGED_EVENT, hydrateAShareWatchlist, readAShareWatchlist } from "../features/stock-cockpit/watchlist";
import { updateTaskActivity } from "../shared/taskActivity";
import { MonitorTtsAnnouncer } from "../features/monitor-center/MonitorTtsAnnouncer";
import { RealtimeProvider } from "../shared/realtime/RealtimeProvider";

const REALTIME_TOPICS = [
  "ai_analysis",
  "company_research",
  "late_session_candidates",
  "market_overview",
  "news_events",
  "sector_fund_flow",
  "quant_strategy",
  "stock_quotes",
] as const;

export function App() {
  useEffect(() => { void loadAShareInstrumentDirectory().catch(() => undefined); }, []);
  useEffect(() => {
    let active = true;
    const marketState = () => {
      const parts = new Intl.DateTimeFormat("zh-CN", { timeZone: "Asia/Shanghai", weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false }).formatToParts(new Date());
      const weekday = parts.find((part) => part.type === "weekday")?.value ?? "";
      const hour = Number(parts.find((part) => part.type === "hour")?.value ?? 0);
      const minute = Number(parts.find((part) => part.type === "minute")?.value ?? 0);
      const value = hour * 60 + minute;
      const weekdayOpen = !weekday.includes("六") && !weekday.includes("日");
      const morning = value >= 570 && value <= 690;
      const afternoon = value >= 780 && value <= 900;
      if (!weekdayOpen) return "休市";
      if (value > 690 && value < 780) return "已暂停";
      return morning || afternoon ? "正在更新" : "休市";
    };
    const registerWatchlist = async () => {
      const symbols = readAShareWatchlist();
      const stage = marketState();
      if (!symbols.length) {
        updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage, state: "succeeded", detail: symbols.length ? `已保存 ${symbols.length} 只` : "尚未添加自选股", percent: 100 });
        return;
      }
      updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: stage === "正在更新" ? "正在更新" : "正在加载", state: "running", detail: `${symbols.length} 只`, percent: 25 });
      const results = await Promise.allSettled(symbols.map((symbol) => registerWatchlistFocus(symbol)));
      if (!active) return;
      const failed = results.filter((result) => result.status === "rejected").length;
      updateTaskActivity({ id: "a-share-watchlist-monitor", label: "个股自选", stage: failed ? "部分更新失败" : stage === "正在更新" ? "实时监控中" : stage, state: failed === symbols.length ? "failed" : "succeeded", detail: failed ? `${symbols.length - failed}/${symbols.length} 只已更新` : `已保存 ${symbols.length} 只`, percent: 100, error: failed ? "部分自选股行情注册失败，稍后自动重试" : null });
    };
    const initialKey = readAShareWatchlist().join(",");
    void registerWatchlist();
    void hydrateAShareWatchlist().then((symbols) => {
      if (symbols.join(",") !== initialKey) void registerWatchlist();
    });
    const onWatchlistChange = () => { void registerWatchlist(); };
    window.addEventListener(A_SHARE_WATCHLIST_CHANGED_EVENT, onWatchlistChange);
    const timer = window.setInterval(onWatchlistChange, 5 * 60 * 1000);
    return () => {
      active = false;
      window.removeEventListener(A_SHARE_WATCHLIST_CHANGED_EVENT, onWatchlistChange);
      window.clearInterval(timer);
    };
  }, []);
  return <RealtimeProvider topics={REALTIME_TOPICS}><SelectedInstrumentProvider><MonitorTtsAnnouncer synthesize={synthesizeSpeech} /><Dashboard
    loadSnapshot={loadSnapshot}
    syncHistory={syncHistory}
    runBacktest={runBacktest}
    loadRisk={loadRisk} loadCompliance={loadCompliance} loadAudit={loadAudit} complianceAction={complianceAction}
    analyzePortfolioRisk={analyzePortfolioRisk}
    loadWatchlistRisk={loadWatchlistRisk}
    loadPortfolioRisk={loadPortfolioRisk}
    savePortfolioPosition={savePortfolioPosition}
    removePortfolioPosition={removePortfolioPosition}
    loadBondDashboard={loadBondDashboard} loadBondDiagnosis={loadBondDiagnosis} loadCachedBondDiagnosis={loadCachedBondDiagnosis} loadBondCandidates={loadBondCandidates} diagnoseBondBatch={diagnoseBondBatch}
    loadNewsIntelligence={loadNewsIntelligence} loadEventImpact={loadEventImpact} syncNews={syncNews} syncHotspots={syncHotspots} createNewsCorrection={createNewsCorrection}
    loadOperationsStatus={loadOperationsStatus} loadOperationsDiagnostics={loadOperationsDiagnostics} loadObservability={loadObservability} setSchedulerPaused={setSchedulerPaused} createBackup={createBackup} verifyBackup={verifyBackup} runManualJob={runManualJob} cleanupCache={cleanupCache} previewStorageCleanup={previewStorageCleanup} cleanupStorage={cleanupStorage} loadPerformanceSummary={loadPerformanceSummary}
    loadAShareCandidates={loadAShareCandidates} loadAShareCandidateScores={loadAShareCandidateScores} loadAShareDiagnosis={loadAShareDiagnosis}
    searchAShareInstruments={searchAShareInstruments}
    loadStockCockpit={loadStockCockpit}
    loadStockCockpitAI={loadStockCockpitAI}
    loadStockQuotePulse={loadStockQuotePulse}
    loadCompanyResearch={loadCompanyResearch}
    compareCompanyResearch={loadCompanyResearchComparison}
    loadStockTimeline={loadStockTimeline}
    prepareStockData={prepareStockData}
    loadAISettings={loadAISettings} saveAISettings={saveAISettings} deleteAISettings={deleteAISettings}
    loadLocalSourceSettings={loadLocalSourceSettings} detectLocalSourceSettings={detectLocalSourceSettings} saveLocalSourceSettings={saveLocalSourceSettings}
    syncAShareUniverse={syncAShareUniverse} loadSourceHealth={loadSourceHealth}
    loadExternalDataSources={loadExternalDataSources} saveExternalDataSource={saveExternalDataSource} clearExternalDataSource={clearExternalDataSource} testExternalDataSource={testExternalDataSource}
    loadHistorySync={loadHistorySync} loadHistoryCoverage={loadHistoryCoverage} loadHistoryRepairCenter={loadHistoryRepairCenter} loadHistoryRepairAudits={loadHistoryRepairAudits} startHistoryBackfill={startHistoryBackfill} pauseHistorySync={pauseHistorySync} resumeHistorySync={resumeHistorySync} retryFailedHistory={retryFailedHistory} restartCurrentHistory={restartCurrentHistory} loadOfficialTdxInfo={loadOfficialTdxInfo} loadHistorySupplement={loadHistorySupplement} startOfficialTdxSupplement={startOfficialTdxSupplement}
    loadTdxImport={loadTdxImport} scanTdxImport={scanTdxImport} startTdxImport={startTdxImport} pauseTdxImport={pauseTdxImport} resumeTdxImport={resumeTdxImport}
    loadDecisionCurrent={loadCurrentDecision} loadDecisionDate={loadDecisionDate}
    loadMarketSentiment={loadCurrentMarketSentiment} refreshMarketSentiment={refreshMarketSentiment}
    loadCandidateSentiments={loadCandidateSentiments} refreshCandidateSentiments={refreshCandidateSentiments}
    loadFirstLimitUp={loadFirstLimitUp} refreshFirstLimitUp={refreshFirstLimitUp}
    loadLateSessionSelection={loadLateSessionSelection}
    loadQuantTicks={loadQuantTicks}
    loadKronosForecast={loadKronosForecast}
    loadWalkForward={loadWalkForward}
    loadQuantStrategy={loadQuantStrategy}
    loadQuantResearch={loadQuantResearch}
    loadQuantShadowDecisions={loadQuantShadowDecisions}
    loadQuantShadowAnalytics={loadQuantShadowAnalytics}
    loadQuantCalibration={loadQuantCalibration}
    loadDecisionJournal={loadDecisionJournal}
    createDecisionJournal={createDecisionJournal}
    loadTdxFormula={loadTdxFormula}
    loadMarketOverview={loadMarketOverview}
    loadMarketIntervalReview={loadMarketIntervalReview}
    loadBreakingNewsAlerts={loadBreakingNewsAlerts}
    loadSpeechSettings={loadSpeechSettings}
    loadSpeechVoices={loadSpeechVoices}
    saveSpeechSettings={saveSpeechSettings}
    synthesizeSpeech={synthesizeSpeech}
  /></SelectedInstrumentProvider></RealtimeProvider>;
}
