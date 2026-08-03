import type { BondCandidates } from "./types";

export type BondTaskTone = "ready" | "pending" | "unavailable" | "excluded";

export type BondTaskCard = {
  code: string;
  name: string;
  linkedStockCode: string | null;
  stateLabel: string;
  reason: string | null;
  tone: BondTaskTone;
};

const taskPriority: Record<BondTaskTone, number> = {
  ready: 0,
  excluded: 1,
  unavailable: 2,
  pending: 3,
};

export function bondTaskPreview(cards: BondTaskCard[], limit = 7): {
  visible: BondTaskCard[];
  hiddenCount: number;
} {
  const visible = [...cards]
    .sort((left, right) => taskPriority[left.tone] - taskPriority[right.tone])
    .slice(0, limit);
  return { visible, hiddenCount: Math.max(0, cards.length - visible.length) };
}

export function bondTaskCards(candidates: BondCandidates | null): BondTaskCard[] {
  if (!candidates) return [];
  const eligibleCodes = new Set(candidates.items.map((item) => item.bond_code));
  const cards = new Map<string, BondTaskCard>();
  for (const item of candidates.discovered ?? []) {
    const eligible = eligibleCodes.has(item.bond_code);
    const state = eligible ? "diagnosed" : item.state;
    const presentation = state === "diagnosed"
      ? { stateLabel: "可观察", tone: "ready" as const }
      : state === "risk_excluded"
        ? { stateLabel: "风险排除", tone: "excluded" as const }
        : state === "unavailable"
          ? { stateLabel: "数据不可用", tone: "unavailable" as const }
          : { stateLabel: "未诊断", tone: "pending" as const };
    cards.set(item.bond_code, {
      code: item.bond_code,
      name: item.name,
      linkedStockCode: item.linked_stock_code,
      stateLabel: presentation.stateLabel,
      reason: item.reason,
      tone: presentation.tone,
    });
  }
  for (const item of candidates.items) {
    if (cards.has(item.bond_code)) continue;
    cards.set(item.bond_code, {
      code: item.bond_code,
      name: `转债 ${item.bond_code}`,
      linkedStockCode: null,
      stateLabel: "可观察",
      reason: null,
      tone: "ready",
    });
  }
  return [...cards.values()];
}
