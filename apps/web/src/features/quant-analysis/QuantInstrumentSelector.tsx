import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LoaderCircle, Search, ShieldAlert } from "lucide-react";

import { friendlyError } from "../../shared/friendlyError";
import type { FirstLimitUpCandidate } from "../first-limit-up/types";
import type { AShareInstrument, InstrumentSearchResponse } from "../stock-cockpit/types";
import { createInstrumentDirectory } from "../../shared/instruments/instrumentDirectory";

type Props = {
  symbol: string | null;
  name: string | null;
  candidates: FirstLimitUpCandidate[];
  candidate: FirstLimitUpCandidate | null;
  boardAsOf?: string;
  search?: (query: string) => Promise<InstrumentSearchResponse>;
  directoryItems?: AShareInstrument[];
  onSelect: (symbol: string, instrument?: AShareInstrument) => void;
};

const EMPTY_DIRECTORY_ITEMS: AShareInstrument[] = [];

export function QuantInstrumentSelector({
  symbol, name, candidates, candidate, boardAsOf, search, directoryItems = EMPTY_DIRECTORY_ITEMS, onSelect,
}: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AShareInstrument[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [sourceUnavailable, setSourceUnavailable] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef(0);
  const localDirectory = useMemo(() => createInstrumentDirectory(directoryItems), [directoryItems]);

  const executeSearch = useCallback((value: string, request = ++requestRef.current) => {
    if (!search) return;
    setState("loading");
    setError("");
    void search(value).then((response) => {
      if (request !== requestRef.current) return;
      setResults(response.items);
      setSourceUnavailable(response.source_status === "unavailable");
      setState("ready");
    }).catch((reason) => {
      if (request !== requestRef.current) return;
      setError(friendlyError(reason, "股票搜索"));
      setState("error");
    });
  }, [search]);

  useEffect(() => {
    const request = ++requestRef.current;
    const normalized = query.trim();
    if (!normalized || !search) {
      setResults([]);
      setSourceUnavailable(false);
      setState("idle");
      return;
    }
    const localResults = localDirectory.search(normalized);
    if (localResults.length) {
      setResults(localResults); setSourceUnavailable(false); setState("ready");
      return;
    }
    setState("loading");
    setError("");
    const timer = window.setTimeout(
      () => executeSearch(normalized, request),
      /^\d{6}$/.test(normalized) ? 0 : 250,
    );
    return () => window.clearTimeout(timer);
  }, [executeSearch, localDirectory, query, search]);

  const selectResult = (item: AShareInstrument) => {
    onSelect(item.symbol, item);
    setQuery("");
  };

  return <section className="quant-instrument-control" aria-label="当前量化分析标的">
    <div className="quant-instrument-layout split">
      <div className="quant-instrument-primary">
        <header className="quant-instrument-heading stacked">
          <span>分析标的</span>
          <b className={candidate ? "candidate" : "custom"}>{candidate ? "候选池标的" : "自定义标的"}</b>
        </header>
        <div className="quant-selected-instrument quant-selected-row">
          <strong className="quant-selected-symbol">{symbol ?? "------"}</strong>
          <span className="quant-selected-name">{name ?? (symbol ? "名称待验证" : "尚未选择")}</span>
        </div>
        <div className="quant-instrument-state" role="status">
          <span><i aria-hidden="true" />{symbol ? "标的已锁定" : "等待选择标的"}</span>
          <small>{candidate ? "已关联首次涨停规则池" : symbol ? "自定义标的 · 等待规则核验" : "输入代码或名称开始分析"}</small>
        </div>
        <label className="quant-symbol-search quant-search-row">
          <Search size={16} />
          <span className="visually-hidden">查询量化分析标的</span>
          <input
            role="searchbox"
            aria-label="查询量化分析标的"
            placeholder="输入六位代码或中文名称"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            disabled={!search}
          />
        </label>
        {state === "loading" && <p className="quant-symbol-message" role="status" aria-busy="true"><LoaderCircle className="spin" size={15} />正在查询已验证 A 股...</p>}
        {query.trim() && state === "error" && <div className="quant-symbol-message error" role="alert"><ShieldAlert size={15} /><span>{error}</span><button type="button" onClick={() => executeSearch(query.trim())}>重试</button></div>}
        {query.trim() && state === "ready" && <div className="quant-symbol-results" role="listbox" aria-label="量化分析股票搜索结果">
          {results.length ? results.map((item) => <button
            key={item.symbol}
            type="button"
            role="option"
            aria-selected={symbol === item.symbol}
            aria-label={`${item.symbol} ${item.name}`}
            onClick={() => selectResult(item)}
          ><b>{item.symbol}</b><span>{item.name}</span><small>{item.exchange.toUpperCase()} · {item.quote_quality === "ready" ? "行情可用" : item.quote_quality === "stale" ? "行情已陈旧" : "行情不可用"}</small></button>) : <p>{sourceUnavailable ? "股票验证源暂不可用" : "没有找到已验证的 A 股"}</p>}
        </div>}
      </div>
      <div className="quant-instrument-secondary">
        <div className="quant-candidate-context stacked">
          <span>快速切换</span>
          <b>首次涨停候选快速切换</b>
        </div>
        <label className="quant-candidate-switch quant-candidate-row">
          <span>候选池标的</span>
          <select
            aria-label="量化分析股票"
            value={candidate ? candidate.symbol : symbol ?? ""}
            onChange={(event) => {
              const next = candidates.find((item) => item.symbol === event.target.value);
              if (next) onSelect(next.symbol);
            }}
            disabled={!candidates.length}
          >
            {!candidate && symbol && <option value={symbol}>{symbol} · 当前自定义标的</option>}
            {!candidates.length && <option value="">暂无候选</option>}
            {candidates.map((item) => <option value={item.symbol} key={item.symbol}>{item.symbol} · {item.name}</option>)}
          </select>
        </label>
        <small className="quant-rule-snapshot"><span>规则快照</span><strong>{boardAsOf ?? "正在读取"}</strong></small>
      </div>
    </div>
  </section>;
}
