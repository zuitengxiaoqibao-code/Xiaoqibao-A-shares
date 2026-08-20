import { shanghaiDay } from "../../shared/tradingDayContext";
import type { RiskStatus } from "../governance/GovernanceViews";

const PREFIX = "qibao.risk-snapshot.v1.";

export type RiskSnapshotHit = { value: RiskStatus; cachedAt: string };

function key(day: string): string {
  return `${PREFIX}${day}`;
}

export function readRiskSnapshot(now = new Date()): RiskSnapshotHit | null {
  const day = shanghaiDay(now);
  try {
    const raw = window.localStorage.getItem(key(day));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { day?: string; cachedAt?: string; value?: RiskStatus };
    if (parsed.day !== day || !parsed.cachedAt || !parsed.value) return null;
    return { value: parsed.value, cachedAt: parsed.cachedAt };
  } catch {
    return null;
  }
}

export function writeRiskSnapshot(value: RiskStatus, now = new Date()): RiskSnapshotHit {
  const day = shanghaiDay(now);
  const hit = { value, cachedAt: now.toISOString() };
  try {
    for (let index = window.localStorage.length - 1; index >= 0; index -= 1) {
      const storedKey = window.localStorage.key(index);
      if (storedKey?.startsWith(PREFIX) && storedKey !== key(day)) window.localStorage.removeItem(storedKey);
    }
    window.localStorage.setItem(key(day), JSON.stringify({ day, ...hit }));
  } catch {
    // A cache failure must never hide a real risk response.
  }
  return hit;
}
