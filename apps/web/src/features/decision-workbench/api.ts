import type { DecisionPhase, DecisionResponse } from "./types";
import { apiClient } from "../../shared/apiClient";

async function read(url: string, init?: RequestInit): Promise<DecisionResponse> {
  return (await apiClient.request<DecisionResponse>(url, { ...init, context: "决策" })).data;
}

export const loadCurrentDecision = () => read("/api/v1/decisions/current");
export const loadDecisionDate = (tradingDate: string) => read(`/api/v1/decisions/${tradingDate}`);
export const runDecisionPhase = (phase: DecisionPhase, tradingDate: string) =>
  read(`/api/v1/decisions/${phase}/${tradingDate}/run`, { method: "POST" });
