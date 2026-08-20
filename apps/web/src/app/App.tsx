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
import { loadAShareInstrumentDirectory, loadStockCockpit, loadStockCockpitAI, prepareStockData, searchAShareInstruments } from "../features/stock-cockpit/api";
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
} from "../features/data-settings/api";
import { loadCurrentMarketSentiment, refreshMarketSentiment } from "../features/market-sentiment/api";
import {
  loadCandidateSentiments,
  refreshCandidateSentiments,
} from "../features/candidate-sentiment/api";
import { loadFirstLimitUp, refreshFirstLimitUp } from "../features/first-limit-up/api";
import { loadLateSessionSelection } from "../features/late-session-selection/api";
import { createDecisionJournal, loadDecisionJournal, loadKronosForecast, loadQuantCalibration, loadQuantShadowAnalytics, loadQuantShadowDecisions, loadQuantStrategy, loadQuantTicks, loadTdxFormula, loadWalkForward } from "../features/quant-analysis/api";
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

export function App() {
  useEffect(() => { void loadAShareInstrumentDirectory().catch(() => undefined); }, []);
  return <SelectedInstrumentProvider><Dashboard
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
    loadCompanyResearch={loadCompanyResearch}
    compareCompanyResearch={loadCompanyResearchComparison}
    loadStockTimeline={loadStockTimeline}
    prepareStockData={prepareStockData}
    loadAISettings={loadAISettings} saveAISettings={saveAISettings} deleteAISettings={deleteAISettings}
    loadLocalSourceSettings={loadLocalSourceSettings} detectLocalSourceSettings={detectLocalSourceSettings} saveLocalSourceSettings={saveLocalSourceSettings}
    syncAShareUniverse={syncAShareUniverse} loadSourceHealth={loadSourceHealth}
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
  /></SelectedInstrumentProvider>;
}
