import { useCallback, useEffect, useRef, useState } from "react";

import { shanghaiDay } from "../../shared/tradingDayContext";

export type QuantLiveStatus = "loading" | "live" | "delayed" | "paused" | "error";

type Options<T> = {
  loader: (signal?: AbortSignal) => Promise<T>;
  intervalMs: number;
  enabled?: boolean;
  errorMessage: string;
  mergeData?: (previous: T | null, incoming: T) => T;
  initialDelayMs?: number;
  cache?: {
    key: string;
    day: string;
    validate: (value: unknown) => value is T;
  };
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

type QuantCacheEnvelope<T> = {
  schemaVersion: 1;
  day: string;
  observedAt: string;
  cachedAt: string;
  value: T;
};

const QUANT_CACHE_PREFIX = "qibao.quant-live.v1";

function quantCachePrefix(key: string): string {
  return `${QUANT_CACHE_PREFIX}.${encodeURIComponent(key)}.`;
}

function quantCacheKey(key: string, day: string): string {
  return `${quantCachePrefix(key)}${day}`;
}

function readQuantCache<T>(cache: Options<T>["cache"]): { value: T; observedAt: Date } | null {
  if (!cache) return null;
  const day = cache.day;
  const prefix = quantCachePrefix(cache.key);
  try {
    for (let index = localStorage.length - 1; index >= 0; index -= 1) {
      const key = localStorage.key(index);
      if (key?.startsWith(prefix) && key !== quantCacheKey(cache.key, day)) localStorage.removeItem(key);
    }
    const key = quantCacheKey(cache.key, day);
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as QuantCacheEnvelope<unknown>;
    const observedAt = new Date(parsed.observedAt);
    const cachedAt = new Date(parsed.cachedAt);
    if (
      parsed.schemaVersion !== 1
      || parsed.day !== day
      || Number.isNaN(observedAt.getTime())
      || Number.isNaN(cachedAt.getTime())
      || !cache.validate(parsed.value)
    ) {
      localStorage.removeItem(key);
      return null;
    }
    return { value: parsed.value, observedAt };
  } catch {
    localStorage.removeItem(quantCacheKey(cache.key, day));
    return null;
  }
}

function writeQuantCache<T>(cache: Options<T>["cache"], value: T, now = new Date()): void {
  if (!cache || !cache.validate(value)) return;
  const day = cache.day;
  try {
    localStorage.setItem(quantCacheKey(cache.key, day), JSON.stringify({
      schemaVersion: 1,
      day,
      observedAt: now.toISOString(),
      cachedAt: now.toISOString(),
      value,
    } satisfies QuantCacheEnvelope<T>));
  } catch {
    // A cache write must never make verified live data unavailable.
  }
}

export function useQuantLiveResource<T>({
  loader,
  intervalMs,
  enabled = true,
  errorMessage,
  mergeData,
  initialDelayMs = 0,
  cache,
}: Options<T>): QuantLiveResource<T> {
  const [activeDay, setActiveDay] = useState(cache?.day ?? shanghaiDay(new Date()));
  const activeCache = cache ? { ...cache, day: activeDay } : undefined;
  const initialCacheRef = useRef<{ value: T; cachedAt: Date } | null | undefined>(undefined);
  if (initialCacheRef.current === undefined) {
    const restored = readQuantCache(activeCache);
    initialCacheRef.current = restored
      ? { value: restored.value, cachedAt: restored.observedAt }
      : null;
  }
  const initialCache = initialCacheRef.current;
  const [data, setData] = useState<T | null>(initialCache?.value ?? null);
  const [status, setStatus] = useState<QuantLiveStatus>(
    enabled && !document.hidden ? initialCache ? "delayed" : "loading" : "paused",
  );
  const [error, setError] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [lastAttemptAt, setLastAttemptAt] = useState<Date | null>(null);
  const [lastSuccessAt, setLastSuccessAt] = useState<Date | null>(initialCache?.cachedAt ?? null);
  const loaderRef = useRef(loader);
  const previousLoaderRef = useRef(loader);
  const loaderVersionRef = useRef(0);
  const errorMessageRef = useRef(errorMessage);
  const mergeDataRef = useRef(mergeData);
  const cacheRef = useRef(activeCache);
  const cacheIdentityRef = useRef(activeCache ? `${activeCache.key}:${activeCache.day}` : undefined);
  const cacheDayPropRef = useRef(cache?.day);
  const dataRef = useRef<T | null>(initialCache?.value ?? null);
  const inFlightRef = useRef<{
    version: number;
    token: symbol;
    controller: AbortController;
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
  cacheRef.current = activeCache;

  useEffect(() => () => {
    mountedRef.current = false;
    inFlightRef.current?.controller.abort();
  }, []);

  const refreshNow = useCallback(async () => {
    const version = loaderVersionRef.current;
    if (inFlightRef.current?.version === version) {
      return inFlightRef.current.promise;
    }
    const token = Symbol("quant-live-request");
    const controller = new AbortController();
    const request = (async () => {
      if (!mountedRef.current) return;
      setRefreshing(true);
      setLastAttemptAt(new Date());
      try {
        const value = await loaderRef.current(controller.signal);
        if (!mountedRef.current || version !== loaderVersionRef.current) return;
        const resolvedValue = mergeDataRef.current?.(dataRef.current, value) ?? value;
        if (resolvedValue === null || resolvedValue === undefined) {
          throw new Error("empty quant resource response");
        }
        dataRef.current = resolvedValue;
        setData(resolvedValue);
        writeQuantCache(cacheRef.current, resolvedValue);
        setError("");
        setLastSuccessAt(new Date());
        setStatus(document.hidden ? "paused" : "live");
      } catch {
        if (controller.signal.aborted) return;
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
    inFlightRef.current = { version, token, controller, promise: request };
    return request;
  }, []);

  const acceptExternal = useCallback((value: T) => {
    if (!mountedRef.current || value === null || value === undefined) return;
    const resolvedValue = mergeDataRef.current?.(dataRef.current, value) ?? value;
    if (resolvedValue === null || resolvedValue === undefined) return;
    dataRef.current = resolvedValue;
    setData(resolvedValue);
    writeQuantCache(cacheRef.current, resolvedValue);
    setError("");
    setLastSuccessAt(new Date());
    setStatus(document.hidden ? "paused" : "live");
  }, []);

  useEffect(() => {
    if (cacheDayPropRef.current === cache?.day) return;
    cacheDayPropRef.current = cache?.day;
    setActiveDay(cache?.day ?? shanghaiDay(new Date()));
  }, [cache?.day]);

  useEffect(() => {
    if (!cache) return undefined;
    const boundary = Date.parse(`${activeDay}T16:00:00Z`);
    const delay = Math.max(1, boundary - Date.now());
    const timer = window.setTimeout(() => setActiveDay(shanghaiDay(new Date())), delay);
    return () => window.clearTimeout(timer);
  }, [activeDay, cache?.key]);

  useEffect(() => {
    const identity = activeCache ? `${activeCache.key}:${activeCache.day}` : undefined;
    if (cacheIdentityRef.current === identity) return;
    cacheIdentityRef.current = identity;
    loaderVersionRef.current += 1;
    inFlightRef.current?.controller.abort();
    inFlightRef.current = null;
    const restored = readQuantCache(activeCache);
    dataRef.current = restored?.value ?? null;
    setData(restored?.value ?? null);
    setLastSuccessAt(restored?.observedAt ?? null);
    setError("");
    setStatus(document.hidden ? "paused" : restored ? "delayed" : enabled ? "loading" : "paused");
  }, [activeCache?.day, activeCache?.key, enabled]);

  useEffect(() => {
    if (!enabled) {
      setStatus("paused");
      return undefined;
    }
    let timer: number | undefined;
    let initialTimer: number | undefined;
    const stopTimer = () => {
      if (timer !== undefined) window.clearInterval(timer);
      timer = undefined;
      if (initialTimer !== undefined) window.clearTimeout(initialTimer);
      initialTimer = undefined;
    };
    const startTimer = () => {
      stopTimer();
      if (!document.hidden) {
        timer = window.setInterval(() => { void refreshNow(); }, intervalMs);
      }
    };
    const startInitial = () => {
      const begin = () => {
        initialTimer = undefined;
        void refreshNow();
        startTimer();
      };
      if (initialDelayMs > 0) initialTimer = window.setTimeout(begin, initialDelayMs);
      else begin();
    };
    const handleVisibility = () => {
      if (document.hidden) {
        stopTimer();
        inFlightRef.current?.controller.abort();
        inFlightRef.current = null;
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
      startInitial();
    }
    return () => {
      stopTimer();
      inFlightRef.current?.controller.abort();
      inFlightRef.current = null;
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [activeDay, enabled, initialDelayMs, intervalMs, loader, refreshNow]);

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
