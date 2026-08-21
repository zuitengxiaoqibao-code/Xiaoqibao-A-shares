import { useEffect, useState } from "react";

import type { BreakingNewsAlert, BreakingNewsAlertLoader } from "./types";
import { appendUniqueEntities } from "../../shared/incrementalResource";
import { useRealtimeFallbackTick, useRealtimeProviderAvailable, useRealtimeSubscription } from "../../shared/realtime/RealtimeProvider";


export function useBreakingNewsAlerts(
  load: BreakingNewsAlertLoader | undefined,
  symbol: string | null | undefined,
  limit: number,
) {
  const [alerts, setAlerts] = useState<BreakingNewsAlert[]>([]);
  const [loading, setLoading] = useState(Boolean(load));
  const [error, setError] = useState<string | null>(null);
  const fallbackTick = useRealtimeFallbackTick();
  const providerAvailable = useRealtimeProviderAvailable();

  useEffect(() => {
    if (!load) {
      setAlerts([]);
      setLoading(false);
      setError(null);
      return;
    }
    const controller = new AbortController();
    let inFlight = false;
    const refresh = async (initial = false) => {
      if (inFlight || controller.signal.aborted) return;
      inFlight = true;
      if (initial) setLoading(true);
      try {
        const response = await load(symbol, controller.signal, limit);
        if (controller.signal.aborted) return;
        setAlerts((current) => appendUniqueEntities(current, response.alerts, (item) => item.event_id));
        setError(null);
      } catch (reason) {
        if (controller.signal.aborted) return;
        setError(reason instanceof Error ? reason.message : "重要事件提醒暂不可用");
      } finally {
        inFlight = false;
        if (!controller.signal.aborted && initial) setLoading(false);
      }
    };
    const handleVisibility = () => {
      if (document.visibilityState !== "hidden") void refresh();
    };
    setError(null);
    void refresh(true);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      controller.abort();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [limit, load, symbol]);

  useRealtimeSubscription("news_events", () => {
    if (load && document.visibilityState !== "hidden") void load(symbol, undefined, limit).then((response) => {
      setAlerts((current) => appendUniqueEntities(current, response.alerts, (item) => item.event_id));
      setError(null);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "重要事件提醒暂不可用"));
  });

  useEffect(() => {
    if (!load || fallbackTick === 0 || document.visibilityState === "hidden") return;
    void load(symbol, undefined, limit).then((response) => {
      setAlerts((current) => appendUniqueEntities(current, response.alerts, (item) => item.event_id));
      setError(null);
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "重要事件提醒暂不可用"));
  }, [fallbackTick, limit, load, symbol]);

  useEffect(() => {
    if (providerAvailable || !load) return undefined;
    const timer = window.setInterval(() => {
      if (document.visibilityState !== "hidden") void load(symbol, undefined, limit).then((response) => {
        setAlerts((current) => appendUniqueEntities(current, response.alerts, (item) => item.event_id));
      }).catch((reason) => setError(reason instanceof Error ? reason.message : "重要事件提醒暂不可用"));
    }, 60_000);
    return () => window.clearInterval(timer);
  }, [limit, load, providerAvailable, symbol]);

  return { alerts, loading, error };
}
