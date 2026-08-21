import type { DecisionJournalCreate, DecisionJournalEntry, IntradayTick, KronosForecastResponse, QuantCalibrationReport, QuantResearchSnapshot, QuantShadowAnalytics, QuantShadowDecisionRecord, QuantStrategyDashboard, TdxFormulaResponse, WalkForwardReport } from "./types";
import { coalescedFetch } from "../../shared/coalescedFetch";
import { requestLedger } from "../../shared/performance/requestLedger";

const FOCUS_TTL_SECONDS = 900;
const FOCUS_RENEW_AFTER_MS = 5 * 60 * 1000;
const FOCUS_RETRY_AFTER_MS = 30 * 1000;
const focusRegistrationState = new Map<string, {
  lastAttemptAt: number;
  registeredUntil: number;
}>();

export async function registerQuantFocus(symbol: string): Promise<void> {
  const now = Date.now();
  const current = focusRegistrationState.get(symbol);
  if (current?.registeredUntil && current.registeredUntil > now) return;
  if (current && now - current.lastAttemptAt < FOCUS_RETRY_AFTER_MS) return;
  focusRegistrationState.set(symbol, {
    lastAttemptAt: now,
    registeredUntil: current?.registeredUntil ?? 0,
  });
  const response = await fetch(
    `/api/v1/a-shares/${encodeURIComponent(symbol)}/intraday-focus`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source: "quant_analysis", ttl_seconds: FOCUS_TTL_SECONDS }),
    },
  );
  if (!response.ok) throw new Error(`盘中监测登记失败 (${response.status})`);
  focusRegistrationState.set(symbol, {
    lastAttemptAt: now,
    registeredUntil: now + FOCUS_RENEW_AFTER_MS,
  });
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
    const response = await fetch(`/api/v1/a-shares/${encodeURIComponent(symbol)}/walk-forward`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        backtest: { strategy: "sma_cross", fast_window: 5, slow_window: 20 },
        train_bars: 120,
        validation_bars: 60,
        test_bars: 60,
        step_bars: 60,
        minimum_closed_trades: 5,
      }),
      signal,
    });
    if (!response.ok) throw new Error(`样本外验证请求失败 (${response.status})`);
    return response.json() as Promise<WalkForwardReport>;
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
  const response = await fetch("/api/v1/a-shares/quant-strategy/journal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error(`个人复盘日志写入失败 (${response.status})`);
  return response.json() as Promise<DecisionJournalEntry>;
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
