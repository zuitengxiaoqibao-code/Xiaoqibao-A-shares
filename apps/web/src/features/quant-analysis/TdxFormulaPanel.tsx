import { useEffect, useRef, useState } from "react";

import type { TdxFormulaLoader, TdxFormulaResponse } from "./types";
import { useRealtimeFallbackTick, useRealtimeSubscription } from "../../shared/realtime/RealtimeProvider";

type Props = { symbol: string | null; load?: TdxFormulaLoader };

export function TdxFormulaPanel({ symbol, load }: Props) {
  const [response, setResponse] = useState<TdxFormulaResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const fallbackTick = useRealtimeFallbackTick();
  const refreshRef = useRef<(() => void) | null>(null);
  useEffect(() => {
    if (!symbol || !load) {
      setResponse(null);
      setLoading(false);
      refreshRef.current = null;
      return;
    }
    let active = true;
    setLoading(true);
    const refresh = () => {
      void load("formula_process_mul_zb", [symbol])
        .then((value) => { if (active) setResponse(value); })
        .catch(() => { if (active) setResponse(null); })
        .finally(() => { if (active) setLoading(false); });
    };
    refreshRef.current = refresh;
    refresh();
    return () => { active = false; if (refreshRef.current === refresh) refreshRef.current = null; };
  }, [load, symbol]);
  useRealtimeSubscription("market_overview", () => {
    if (document.visibilityState !== "hidden") refreshRef.current?.();
  }, { fallbackToNetwork: false });
  useEffect(() => {
    const refreshIfVisible = () => {
      if (document.visibilityState === "visible") refreshRef.current?.();
    };
    document.addEventListener("visibilitychange", refreshIfVisible);
    if (fallbackTick > 0) refreshIfVisible();
    return () => document.removeEventListener("visibilitychange", refreshIfVisible);
  }, [fallbackTick]);
  if (!load) return null;
  const point = response?.points.find((item) => item.symbol === symbol);
  const values = point ? Object.entries(point.values) : [];
  return <section className="quant-panel quant-formula-panel" role="region" aria-label="通达信公式证据">
    <header><div><span>TDX / READ-ONLY FORMULA</span><h2>通达信公式证据</h2></div><small>{loading ? "正在读取" : response?.status === "ready" ? "已返回" : "不可用"}</small></header>
    {values.length > 0 ? <div className="quant-formula-grid">{values.map(([key, value]) => <div key={key}><span>{key}</span><strong>{value}</strong></div>)}</div> : <div className="quant-empty"><b>{loading ? "正在读取本地公式结果" : "公式结果不可用"}</b><p>{response?.detail ?? "仅展示通达信明确返回的字段，不用 0 或其他指标代替。"}</p></div>}
    {point && <footer className="quant-panel-note">公式：{point.formula_name} · 观察时间：{new Date(point.fetched_at).toLocaleString("zh-CN")} · 来源：{point.source}</footer>}
  </section>;
}
