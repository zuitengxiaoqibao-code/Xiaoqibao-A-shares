import { normalizeAShareSymbolSet } from "../instruments/instrumentDirectory";

export const WORKSPACE_STATE_KEY = "qibao-workspace-state-v1";
export const WORKSPACE_STATE_VERSION = 1 as const;

type FilterValue = string | number | boolean | null;
export type WorkspaceFilters = Record<string, Record<string, FilterValue>>;

export type WorkspaceState = {
  version: typeof WORKSPACE_STATE_VERSION;
  route: string;
  menu: string | null;
  symbol: string | null;
  asOf: string | null;
  filters: WorkspaceFilters;
  drilldownSymbols: Record<string, string[]>;
  scrollTop: number;
  scrollById: Record<string, number>;
  savedAt: string;
};

export type WorkspaceStatePatch = Partial<Omit<WorkspaceState, "version" | "savedAt">>;

const A_SHARE_SYMBOL = /^(?:(?:000|001|002|003|300|301|600|601|603|605|688|689|920)\d{3}|[48]\d{5})$/;
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function validDate(value: unknown): value is string {
  if (typeof value !== "string" || !ISO_DATE.test(value)) return false;
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value;
}

function finiteNonNegative(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
}

function cleanFilters(value: unknown): WorkspaceFilters {
  if (!isRecord(value)) return {};
  const result: WorkspaceFilters = {};
  for (const [scope, rawFields] of Object.entries(value).slice(0, 30)) {
    if (!scope || scope.length > 120 || !isRecord(rawFields)) continue;
    const fields: Record<string, FilterValue> = {};
    for (const [key, rawValue] of Object.entries(rawFields).slice(0, 30)) {
      if (!key || key.length > 80) continue;
      if (rawValue === null || typeof rawValue === "string" || typeof rawValue === "boolean") {
        fields[key] = typeof rawValue === "string" ? rawValue.slice(0, 200) : rawValue;
      } else if (typeof rawValue === "number" && Number.isFinite(rawValue)) {
        fields[key] = rawValue;
      }
    }
    result[scope] = fields;
  }
  return result;
}

function cleanDrilldowns(value: unknown): Record<string, string[]> {
  if (!isRecord(value)) return {};
  const result: Record<string, string[]> = {};
  for (const [key, rawSymbols] of Object.entries(value).slice(0, 50)) {
    if (!key || key.length > 120 || !Array.isArray(rawSymbols)) continue;
    const symbols = normalizeAShareSymbolSet(rawSymbols.filter((item): item is string => typeof item === "string")).slice(0, 500);
    if (symbols.length > 0) result[key] = symbols;
  }
  return result;
}

function cleanScrollById(value: unknown): Record<string, number> {
  if (!isRecord(value)) return {};
  const result: Record<string, number> = {};
  for (const [key, rawPosition] of Object.entries(value).slice(0, 50)) {
    const position = finiteNonNegative(rawPosition);
    if (key && key.length <= 120 && position !== null) result[key] = position;
  }
  return result;
}

export function validateWorkspaceState(
  value: unknown,
  allowedRoutes?: readonly string[],
): WorkspaceState | null {
  if (!isRecord(value) || value.version !== WORKSPACE_STATE_VERSION) return null;
  const route = typeof value.route === "string" ? value.route : "";
  if (!route.startsWith("/") || route.startsWith("//") || route.length > 240) return null;
  if (allowedRoutes && !allowedRoutes.includes(route)) return null;
  const symbol = value.symbol === null || value.symbol === undefined
    ? null
    : typeof value.symbol === "string" && A_SHARE_SYMBOL.test(value.symbol) ? value.symbol : null;
  if (value.symbol !== null && value.symbol !== undefined && symbol === null) return null;
  const asOf = value.asOf === null || value.asOf === undefined
    ? null
    : validDate(value.asOf) ? value.asOf : null;
  if (value.asOf !== null && value.asOf !== undefined && asOf === null) return null;
  const scrollTop = finiteNonNegative(value.scrollTop) ?? 0;
  return {
    version: WORKSPACE_STATE_VERSION,
    route,
    menu: typeof value.menu === "string" && value.menu.length <= 120 ? value.menu : null,
    symbol,
    asOf,
    filters: cleanFilters(value.filters),
    drilldownSymbols: cleanDrilldowns(value.drilldownSymbols),
    scrollTop,
    scrollById: cleanScrollById(value.scrollById),
    savedAt: typeof value.savedAt === "string" && Number.isFinite(Date.parse(value.savedAt))
      ? value.savedAt
      : new Date().toISOString(),
  };
}

export function loadWorkspaceState(allowedRoutes?: readonly string[]): WorkspaceState | null {
  try {
    const raw = window.localStorage.getItem(WORKSPACE_STATE_KEY);
    if (!raw) return null;
    const state = validateWorkspaceState(JSON.parse(raw), allowedRoutes);
    if (!state) window.localStorage.removeItem(WORKSPACE_STATE_KEY);
    return state;
  } catch {
    try { window.localStorage.removeItem(WORKSPACE_STATE_KEY); } catch { /* Storage may be disabled. */ }
    return null;
  }
}

export function saveWorkspaceState(patch: WorkspaceStatePatch): WorkspaceState | null {
  try {
    const previous = loadWorkspaceState();
    const candidate = {
      version: WORKSPACE_STATE_VERSION,
      route: patch.route ?? previous?.route ?? "/market-overview",
      menu: patch.menu === undefined ? previous?.menu ?? null : patch.menu,
      symbol: patch.symbol === undefined ? previous?.symbol ?? null : patch.symbol,
      asOf: patch.asOf === undefined ? previous?.asOf ?? null : patch.asOf,
      filters: patch.filters ?? previous?.filters ?? {},
      drilldownSymbols: patch.drilldownSymbols ?? previous?.drilldownSymbols ?? {},
      scrollTop: patch.scrollTop ?? previous?.scrollTop ?? 0,
      scrollById: patch.scrollById ?? previous?.scrollById ?? {},
      savedAt: new Date().toISOString(),
    };
    const state = validateWorkspaceState(candidate);
    if (!state) return null;
    window.localStorage.setItem(WORKSPACE_STATE_KEY, JSON.stringify(state));
    return state;
  } catch {
    return null;
  }
}

export function updateWorkspaceFilter(
  scope: string,
  values: Record<string, FilterValue>,
): WorkspaceState | null {
  const previous = loadWorkspaceState();
  return saveWorkspaceState({
    filters: {
      ...(previous?.filters ?? {}),
      [scope]: { ...(previous?.filters[scope] ?? {}), ...values },
    },
  });
}

export function rememberDrilldownSymbols(
  key: string,
  symbols: string[],
): WorkspaceState | null {
  const previous = loadWorkspaceState();
  return saveWorkspaceState({
    drilldownSymbols: {
      ...(previous?.drilldownSymbols ?? {}),
      [key]: symbols,
    },
  });
}

export function clearWorkspaceState(): void {
  try { window.localStorage.removeItem(WORKSPACE_STATE_KEY); } catch { /* Storage may be disabled. */ }
}
