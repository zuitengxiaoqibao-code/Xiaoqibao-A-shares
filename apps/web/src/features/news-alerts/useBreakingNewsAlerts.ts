import { useEffect, useState } from "react";

import type { BreakingNewsAlert, BreakingNewsAlertLoader } from "./types";


export function useBreakingNewsAlerts(
  load: BreakingNewsAlertLoader | undefined,
  symbol: string | null | undefined,
  limit: number,
) {
  const [alerts, setAlerts] = useState<BreakingNewsAlert[]>([]);
  const [loading, setLoading] = useState(Boolean(load));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!load) {
      setAlerts([]);
      setLoading(false);
      setError(null);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void load(symbol, controller.signal, limit).then((response) => {
      if (controller.signal.aborted) return;
      setAlerts(response.alerts);
    }).catch((reason) => {
      if (controller.signal.aborted) return;
      setError(reason instanceof Error ? reason.message : "重要事件提醒暂不可用");
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false);
    });
    return () => controller.abort();
  }, [limit, load, symbol]);

  return { alerts, loading, error };
}
