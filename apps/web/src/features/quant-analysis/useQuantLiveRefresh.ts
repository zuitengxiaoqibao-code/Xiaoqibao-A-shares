import { useCallback, useEffect, useRef, useState } from "react";

export type QuantLiveStatus = "loading" | "live" | "delayed" | "paused" | "error";

type Options<T> = {
  loader: () => Promise<T>;
  intervalMs: number;
  enabled?: boolean;
  errorMessage: string;
  mergeData?: (previous: T | null, incoming: T) => T;
};

export type QuantLiveResource<T> = {
  data: T | null;
  status: QuantLiveStatus;
  error: string;
  refreshing: boolean;
  lastAttemptAt: Date | null;
  lastSuccessAt: Date | null;
  refreshNow: () => Promise<void>;
  acceptExternal: (value: T) => void;
};

export function useQuantLiveResource<T>({
  loader,
  intervalMs,
  enabled = true,
  errorMessage,
  mergeData,
}: Options<T>): QuantLiveResource<T> {
  const [data, setData] = useState<T | null>(null);
  const [status, setStatus] = useState<QuantLiveStatus>(
    enabled && !document.hidden ? "loading" : "paused",
  );
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [lastAttemptAt, setLastAttemptAt] = useState<Date | null>(null);
  const [lastSuccessAt, setLastSuccessAt] = useState<Date | null>(null);
  const loaderRef = useRef(loader);
  const previousLoaderRef = useRef(loader);
  const loaderVersionRef = useRef(0);
  const errorMessageRef = useRef(errorMessage);
  const mergeDataRef = useRef(mergeData);
  const dataRef = useRef<T | null>(null);
  const inFlightRef = useRef<{
    version: number;
    token: symbol;
    promise: Promise<void>;
  } | null>(null);
  const mountedRef = useRef(true);

  if (previousLoaderRef.current !== loader) {
    previousLoaderRef.current = loader;
    loaderVersionRef.current += 1;
  }
  loaderRef.current = loader;
  errorMessageRef.current = errorMessage;
  mergeDataRef.current = mergeData;

  useEffect(() => () => {
    mountedRef.current = false;
  }, []);

  const refreshNow = useCallback(async () => {
    const version = loaderVersionRef.current;
    if (inFlightRef.current?.version === version) {
      return inFlightRef.current.promise;
    }
    const token = Symbol("quant-live-request");
    const request = (async () => {
      if (!mountedRef.current) return;
      setRefreshing(true);
      setLastAttemptAt(new Date());
      try {
        const value = await loaderRef.current();
        if (!mountedRef.current || version !== loaderVersionRef.current) return;
        const resolvedValue = mergeDataRef.current?.(dataRef.current, value) ?? value;
        if (resolvedValue === null || resolvedValue === undefined) {
          throw new Error("empty quant resource response");
        }
        dataRef.current = resolvedValue;
        setData(resolvedValue);
        setError("");
        setLastSuccessAt(new Date());
        setStatus(document.hidden ? "paused" : "live");
      } catch {
        if (!mountedRef.current || version !== loaderVersionRef.current) return;
        setError(errorMessageRef.current);
        setStatus(dataRef.current === null ? "error" : "delayed");
      } finally {
        if (mountedRef.current && version === loaderVersionRef.current) {
          setRefreshing(false);
        }
        if (inFlightRef.current?.token === token) inFlightRef.current = null;
      }
    })();
    inFlightRef.current = { version, token, promise: request };
    return request;
  }, []);

  const acceptExternal = useCallback((value: T) => {
    if (!mountedRef.current || value === null || value === undefined) return;
    const resolvedValue = mergeDataRef.current?.(dataRef.current, value) ?? value;
    if (resolvedValue === null || resolvedValue === undefined) return;
    dataRef.current = resolvedValue;
    setData(resolvedValue);
    setError("");
    setLastSuccessAt(new Date());
    setStatus(document.hidden ? "paused" : "live");
  }, []);

  useEffect(() => {
    if (!enabled) {
      setStatus("paused");
      return undefined;
    }
    let timer: number | undefined;
    const stopTimer = () => {
      if (timer !== undefined) window.clearInterval(timer);
      timer = undefined;
    };
    const startTimer = () => {
      stopTimer();
      if (!document.hidden) {
        timer = window.setInterval(() => { void refreshNow(); }, intervalMs);
      }
    };
    const handleVisibility = () => {
      if (document.hidden) {
        stopTimer();
        setStatus("paused");
        return;
      }
      setStatus(dataRef.current === null ? "loading" : "live");
      void refreshNow();
      startTimer();
    };

    document.addEventListener("visibilitychange", handleVisibility);
    if (document.hidden) {
      setStatus("paused");
    } else {
      void refreshNow();
      startTimer();
    }
    return () => {
      stopTimer();
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [enabled, intervalMs, loader, refreshNow]);

  return {
    data,
    status,
    error,
    refreshing,
    lastAttemptAt,
    lastSuccessAt,
    refreshNow,
    acceptExternal,
  };
}
