import type { DecisionJournalCreate, DecisionJournalEntry, IntradayTick, KronosForecastResponse, QuantCalibrationReport, QuantResearchSnapshot, QuantShadowAnalytics, QuantShadowDecisionRecord, QuantStrategyDashboard, TdxFormulaResponse, WalkForwardReport } from "./types";
import { coalescedFetch } from "../../shared/coalescedFetch";
import { requestLedger } from "../../shared/performance/requestLedger";
import { apiClient } from "../../shared/apiClient";

const FOCUS_TTL_SECONDS = 900;
const FOCUS_RENEW_AFTER_MS = 5 * 60 * 1000;
const FOCUS_RETRY_AFTER_MS = 30 * 1000;
const focusRegistrationState = new Map<string, {
  lastAttemptAt: number;
  registeredUntil: number;
}>();

type FocusSource = "quant_analysis" | "watchlist";

async function registerFocus(symbol: string, source: FocusSource): Promise<void> {
  const now = Date.now();
  const key = `${source}:${symbol}`;
  const current = focusRegistrationState.get(key);
  if (current?.registeredUntil && current.registeredUntil > now) return;
  if (current && now - current.lastAttemptAt < FOCUS_RETRY_AFTER_MS) return;
  focusRegistrationState.set(key, {
    lastAttemptAt: now,
    registeredUntil: current?.registeredUntil ?? 0,
  });
  await apiClient.post(
    `/api/v1/a-shares/${encodeURIComponent(symbol)}/intraday-focus`,
    { source, ttl_seconds: FOCUS_TTL_SECONDS },
    { context: "盘中监测登记" },
  );
  focusRegistrationState.set(key, {
    lastAttemptAt: now,
    registeredUntil: now + FOCUS_RENEW_AFTER_MS,
  });
}

export async function registerQuantFocus(symbol: string): Promise<void> {
  return registerFocus(symbol, "quant_analysis");
}

export async function registerWatchlistFocus(symbol: string): Promise<void> {
  return registerFocus(symbol, "watchlist");
}

export async function loadQuantTicks(
  symbol: string,
  tradingDate?: string,
): Promise<IntradayTick[]> {
  await registerQuantFocus(symbol).catch(() => undefined);
  const query = tradingDate
    ? `?trading_date=${encodeURIComponent(tradingDate)}`
    : "";
  const response = await coalescedFetch(
    `/api/v1/a-shares/${encodeURIComponent(symbol)}/intraday-ticks${query}`,
  );
  if (!response.ok) {
    throw new Error(`盘中 TICK 请求失败 (${response.status})`);
  }
  return response.json() as Promise<IntradayTick[]>;
}

export async function loadKronosForecast(
  symbol: string,
  asOf?: string,
  horizon = 20,
): Promise<KronosForecastResponse> {
  const params = new URLSearchParams({ symbol, horizon: String(horizon) });
  if (asOf) params.set("as_of", asOf);
  const response = await coalescedFetch(
    `/api/v1/a-shares/first-limit-up/quant-forecast?${params.toString()}`,
  );
  if (!response.ok) {
    throw new Error(`Kronos 预测请求失败 (${response.status})`);
  }
  return response.json() as Promise<KronosForecastResponse>;
}

export async function loadWalkForward(
  symbol: string,
  signal?: AbortSignal,
): Promise<WalkForwardReport> {
  return requestLedger.run(`walk-forward:${symbol}`, async () => {
    return apiClient.post<WalkForwardReport>(`/api/v1/a-shares/${encodeURIComponent(symbol)}/walk-forward`, {
        backtest: { strategy: "sma_cross", fast_window: 5, slow_window: 20 },
        train_bars: 120,
        validation_bars: 60,
        test_bars: 60,
        step_bars: 60,
        minimum_closed_trades: 5,
      }, { context: "样本外验证", signal });
  }, { domain: "walk-forward" });
}

export async function loadQuantStrategy(limit = 12): Promise<QuantStrategyDashboard> {
  return requestLedger.run(`quant-strategy:${limit}`, async () => {
    const response = await coalescedFetch(
      `/api/v1/a-shares/quant-strategy?limit=${encodeURIComponent(String(limit))}`,
    );
    if (!response.ok) {
      throw new Error(`短线策略请求失败 (${response.status})`);
    }
    return response.json() as Promise<QuantStrategyDashboard>;
  }, { domain: "quant-strategy" });
}

export async function loadQuantResearch(): Promise<QuantResearchSnapshot> {
  return requestLedger.run("quant-research", async () => {
    const response = await coalescedFetch("/api/v1/a-shares/quant-research");
    if (!response.ok) throw new Error(`量化研究快照请求失败 (${response.status})`);
    return response.json() as Promise<QuantResearchSnapshot>;
  }, { domain: "quant-research" });
}

export async function loadQuantShadowDecisions(limit = 50): Promise<QuantShadowDecisionRecord[]> {
  const response = await coalescedFetch(`/api/v1/a-shares/quant-strategy/shadow?limit=${encodeURIComponent(String(limit))}`);
  if (!response.ok) throw new Error(`策略影子账本请求失败 (${response.status})`);
  return response.json() as Promise<QuantShadowDecisionRecord[]>;
}

export async function loadQuantShadowAnalytics(horizon: 1 | 3 | 5 | 10 | 20 | 60 = 5): Promise<QuantShadowAnalytics> {
  const response = await coalescedFetch(`/api/v1/a-shares/quant-strategy/shadow/analytics?horizon=${horizon}`);
  if (!response.ok) throw new Error(`策略校准统计请求失败 (${response.status})`);
  return response.json() as Promise<QuantShadowAnalytics>;
}

export async function loadQuantCalibration(horizon: 1 | 3 | 5 | 10 | 20 | 60 = 5): Promise<QuantCalibrationReport> {
  const response = await coalescedFetch(`/api/v1/a-shares/quant-strategy/shadow/calibration?horizon=${horizon}`);
  if (!response.ok) throw new Error(`量化校准报告请求失败 (${response.status})`);
  return response.json() as Promise<QuantCalibrationReport>;
}

export async function loadDecisionJournal(limit = 50): Promise<DecisionJournalEntry[]> {
  const response = await coalescedFetch(`/api/v1/a-shares/quant-strategy/journal?limit=${encodeURIComponent(String(limit))}`);
  if (!response.ok) throw new Error(`个人复盘日志请求失败 (${response.status})`);
  return response.json() as Promise<DecisionJournalEntry[]>;
}

export async function createDecisionJournal(request: DecisionJournalCreate): Promise<DecisionJournalEntry> {
  return apiClient.post("/api/v1/a-shares/quant-strategy/journal", request, { context: "个人复盘日志写入" });
}

export async function loadTdxFormula(
  formulaName: string,
  stockCodes: string[],
): Promise<TdxFormulaResponse> {
  const params = new URLSearchParams({ formula_name: formulaName });
  stockCodes.forEach((code) => params.append("stock_codes", code));
  const response = await coalescedFetch(`/api/v1/tdx/local/formula?${params.toString()}`);
  if (!response.ok) throw new Error(`通达信公式请求失败 (${response.status})`);
  return response.json() as Promise<TdxFormulaResponse>;
}
