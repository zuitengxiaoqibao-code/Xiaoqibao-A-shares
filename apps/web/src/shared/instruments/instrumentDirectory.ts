import type { AShareInstrument } from "../../features/stock-cockpit/types";

export type InstrumentDirectory = {
  search: (query: string, limit?: number) => AShareInstrument[];
  resolve: (symbol: string) => AShareInstrument | undefined;
};

const A_SHARE_SYMBOL = /^(?:(?:000|001|002|003|300|301|600|601|603|605|688|689|920)\d{3}|[48]\d{5})$/;

export function normalizeAShareSymbolSet(symbols: Iterable<string>): string[] {
  return [...new Set([...symbols].filter((symbol) => symbol !== "000300" && A_SHARE_SYMBOL.test(symbol)))];
}

function terms(item: AShareInstrument): string[] {
  return [
    item.symbol, item.name, item.short_name ?? "", ...(item.historical_names ?? []),
    ...(item.search_aliases ?? []),
  ].filter(Boolean).map((value) => value.toLocaleLowerCase("zh-CN"));
}

export function createInstrumentDirectory(items: AShareInstrument[]): InstrumentDirectory {
  const unique = [...new Map(items.map((item) => [item.symbol, item])).values()];
  const bySymbol = new Map(unique.map((item) => [item.symbol, item]));
  return {
    resolve: (symbol) => bySymbol.get(symbol),
    search(query, limit = 10) {
      const normalized = query.trim().toLocaleLowerCase("zh-CN");
      if (!normalized) return [];
      return unique.filter((item) => terms(item).some((term) => term.includes(normalized)))
        .sort((left, right) => {
          const leftRank = left.symbol === normalized ? 0 : left.name.toLocaleLowerCase("zh-CN") === normalized ? 1 : left.name.toLocaleLowerCase("zh-CN").startsWith(normalized) ? 2 : 3;
          const rightRank = right.symbol === normalized ? 0 : right.name.toLocaleLowerCase("zh-CN") === normalized ? 1 : right.name.toLocaleLowerCase("zh-CN").startsWith(normalized) ? 2 : 3;
          return leftRank - rightRank || left.symbol.localeCompare(right.symbol);
        }).slice(0, limit);
    },
  };
}
