import type { DecisionJournalCreate, DecisionJournalEntry, IntradayTick, KronosForecastResponse, QuantShadowAnalytics, QuantShadowDecisionRecord, QuantStrategyDashboard, TdxFormulaResponse } from "./types";
import { coalescedFetch } from "../../shared/coalescedFetch";
import { requestLedger } from "../../shared/performance/requestLedger";

export async function loadQuantTicks(
  symbol: string,
  tradingDate?: string,
): Promise<IntradayTick[]> {
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

export async function loadQuantShadowDecisions(limit = 50): Promise<QuantShadowDecisionRecord[]> {
  const response = await coalescedFetch(`/api/v1/a-shares/quant-strategy/shadow?limit=${encodeURIComponent(String(limit))}`);
  if (!response.ok) throw new Error(`策略影子账本请求失败 (${response.status})`);
  return response.json() as Promise<QuantShadowDecisionRecord[]>;
}

export async function loadQuantShadowAnalytics(horizon: 1 | 3 | 5 | 10 | 20 = 5): Promise<QuantShadowAnalytics> {
  const response = await coalescedFetch(`/api/v1/a-shares/quant-strategy/shadow/analytics?horizon=${horizon}`);
  if (!response.ok) throw new Error(`策略校准统计请求失败 (${response.status})`);
  return response.json() as Promise<QuantShadowAnalytics>;
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
