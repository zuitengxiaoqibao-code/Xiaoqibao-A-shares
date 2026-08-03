import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/600.css";
import "@fontsource/orbitron/600.css";

import { Dashboard } from "../features/dashboard/Dashboard";
import { loadSnapshot } from "../features/dashboard/api";
import { syncHistory } from "../features/data-status/api";
import { runBacktest } from "../features/backtest/api";
import { complianceAction, loadAudit, loadCompliance, loadRisk } from "../features/governance/api";
import { diagnoseBondBatch, loadBondCandidates, loadBondDashboard, loadBondDiagnosis, loadCachedBondDiagnosis } from "../features/convertible-bonds/api";
import { createNewsCorrection, loadNewsIntelligence, syncHotspots, syncNews } from "../features/news-intelligence/api";
import { createBackup, loadOperationsStatus, runManualJob, setSchedulerPaused, verifyBackup } from "../features/operations/api";
import { loadAShareCandidateScores, loadAShareCandidates, loadAShareDiagnosis } from "../features/a-shares/api";
import { loadCurrentDecision, loadDecisionDate } from "../features/decision-workbench/api";
import { SelectedInstrumentProvider } from "../features/instrument-selection/SelectedInstrumentProvider";
import { loadStockCockpit, loadStockCockpitAI, prepareStockData, searchAShareInstruments } from "../features/stock-cockpit/api";
import {
  deleteAISettings,
  loadAISettings,
  loadHistoryCoverage,
  loadHistorySync,
  loadLocalSourceSettings,
  detectLocalSourceSettings,
  saveLocalSourceSettings,
  loadSourceHealth,
  pauseHistorySync,
  resumeHistorySync,
  saveAISettings,
  startHistoryBackfill,
  syncAShareUniverse,
} from "../features/data-settings/api";
import { loadCurrentMarketSentiment, refreshMarketSentiment } from "../features/market-sentiment/api";
import {
  loadCandidateSentiments,
  refreshCandidateSentiments,
} from "../features/candidate-sentiment/api";
import { loadFirstLimitUp, refreshFirstLimitUp } from "../features/first-limit-up/api";
import { loadKronosForecast, loadQuantStrategy, loadQuantTicks } from "../features/quant-analysis/api";
import { loadMarketOverview } from "../features/market-overview/api";
import { loadStockTimeline } from "../features/stock-timeline/api";
import { loadBreakingNewsAlerts } from "../features/news-alerts/api";
import {
  loadSpeechSettings,
  loadSpeechVoices,
  saveSpeechSettings,
  synthesizeSpeech,
} from "../features/speech/api";
import { loadCompanyResearch } from "../features/company-research/api";

export function App() {
  return <SelectedInstrumentProvider><Dashboard
    loadSnapshot={loadSnapshot}
    syncHistory={syncHistory}
    runBacktest={runBacktest}
    loadRisk={loadRisk} loadCompliance={loadCompliance} loadAudit={loadAudit} complianceAction={complianceAction}
    loadBondDashboard={loadBondDashboard} loadBondDiagnosis={loadBondDiagnosis} loadCachedBondDiagnosis={loadCachedBondDiagnosis} loadBondCandidates={loadBondCandidates} diagnoseBondBatch={diagnoseBondBatch}
    loadNewsIntelligence={loadNewsIntelligence} syncNews={syncNews} syncHotspots={syncHotspots} createNewsCorrection={createNewsCorrection}
    loadOperationsStatus={loadOperationsStatus} setSchedulerPaused={setSchedulerPaused} createBackup={createBackup} verifyBackup={verifyBackup} runManualJob={runManualJob}
    loadAShareCandidates={loadAShareCandidates} loadAShareCandidateScores={loadAShareCandidateScores} loadAShareDiagnosis={loadAShareDiagnosis}
    searchAShareInstruments={searchAShareInstruments}
    loadStockCockpit={loadStockCockpit}
    loadStockCockpitAI={loadStockCockpitAI}
    loadCompanyResearch={loadCompanyResearch}
    loadStockTimeline={loadStockTimeline}
    prepareStockData={prepareStockData}
    loadAISettings={loadAISettings} saveAISettings={saveAISettings} deleteAISettings={deleteAISettings}
    loadLocalSourceSettings={loadLocalSourceSettings} detectLocalSourceSettings={detectLocalSourceSettings} saveLocalSourceSettings={saveLocalSourceSettings}
    syncAShareUniverse={syncAShareUniverse} loadSourceHealth={loadSourceHealth}
    loadHistorySync={loadHistorySync} loadHistoryCoverage={loadHistoryCoverage} startHistoryBackfill={startHistoryBackfill} pauseHistorySync={pauseHistorySync} resumeHistorySync={resumeHistorySync}
    loadDecisionCurrent={loadCurrentDecision} loadDecisionDate={loadDecisionDate}
    loadMarketSentiment={loadCurrentMarketSentiment} refreshMarketSentiment={refreshMarketSentiment}
    loadCandidateSentiments={loadCandidateSentiments} refreshCandidateSentiments={refreshCandidateSentiments}
    loadFirstLimitUp={loadFirstLimitUp} refreshFirstLimitUp={refreshFirstLimitUp}
    loadQuantTicks={loadQuantTicks}
    loadKronosForecast={loadKronosForecast}
    loadQuantStrategy={loadQuantStrategy}
    loadMarketOverview={loadMarketOverview}
    loadBreakingNewsAlerts={loadBreakingNewsAlerts}
    loadSpeechSettings={loadSpeechSettings}
    loadSpeechVoices={loadSpeechVoices}
    saveSpeechSettings={saveSpeechSettings}
    synthesizeSpeech={synthesizeSpeech}
  /></SelectedInstrumentProvider>;
}
