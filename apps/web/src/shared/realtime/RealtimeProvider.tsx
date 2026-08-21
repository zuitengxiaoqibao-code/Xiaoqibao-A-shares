import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import {
  consumeRealtimeStream,
  type RealtimeStreamEvent,
  type RealtimeStreamState,
} from "../realtimeStream";
import { RealtimeStore } from "./realtimeStore";

export type RealtimeConsumer = typeof consumeRealtimeStream;

type RealtimeContextValue = {
  store: RealtimeStore;
  state: RealtimeStreamState | "idle";
  fallback: boolean;
  fallbackTick: number;
  provided: boolean;
};

const fallbackStore = new RealtimeStore();
const RealtimeContext = createContext<RealtimeContextValue>({ store: fallbackStore, state: "idle", fallback: false, fallbackTick: 0, provided: false });

const DEFAULT_RECONNECT_DELAYS = [1_000, 2_000, 5_000, 10_000, 30_000];

export function RealtimeProvider({
  children,
  topics,
  consume = consumeRealtimeStream,
  reconnectDelaysMs = DEFAULT_RECONNECT_DELAYS,
  fallbackIntervalMs = 15_000,
}: {
  children: ReactNode;
  topics: readonly string[];
  consume?: RealtimeConsumer;
  reconnectDelaysMs?: readonly number[];
  fallbackIntervalMs?: number;
}) {
  const normalizedTopics = useMemo(
    () => [...new Set(topics.map((topic) => topic.trim()).filter(Boolean))].sort(),
    [topics],
  );
  const storeRef = useRef<RealtimeStore | null>(null);
  if (!storeRef.current) storeRef.current = new RealtimeStore();
  const store = storeRef.current;
  const [state, setState] = useState<RealtimeStreamState | "idle">("idle");
  const [fallback, setFallback] = useState(false);
  const [fallbackTick, setFallbackTick] = useState(0);

  useEffect(() => {
    const onVisibility = () => store.setVisible(document.visibilityState !== "hidden");
    onVisibility();
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [store]);

  useEffect(() => {
    if (normalizedTopics.length === 0) {
      setState("idle");
      return undefined;
    }
    let disposed = false;
    let attempt = 0;
    let reconnectTimer: number | undefined;
    let activeController: AbortController | undefined;

    const schedule = () => {
      if (disposed || reconnectTimer !== undefined) return;
      setFallback(true);
      const delay = reconnectDelaysMs[Math.min(attempt, Math.max(0, reconnectDelaysMs.length - 1))] ?? 30_000;
      attempt += 1;
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = undefined;
        void connect();
      }, Math.max(0, delay));
    };

    const connect = async (): Promise<void> => {
      if (disposed) return;
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;
      try {
        await consume(
          normalizedTopics,
          (event: RealtimeStreamEvent) => store.publish(event),
          controller.signal,
          (nextState) => {
            if (disposed || controller.signal.aborted) return;
            setState(nextState);
            if (nextState === "connected") {
              attempt = 0;
              setFallback(false);
            } else if (nextState === "error" || nextState === "closed") {
              schedule();
            }
          },
        );
        if (!disposed && !controller.signal.aborted) schedule();
      } catch {
        if (!disposed && !controller.signal.aborted) {
          setState("error");
          schedule();
        }
      }
    };

    void connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer);
      activeController?.abort();
    };
  }, [consume, normalizedTopics, reconnectDelaysMs, store]);

  useEffect(() => {
    if (!fallback) return undefined;
    const timer = window.setInterval(() => setFallbackTick((current) => current + 1), Math.max(1, fallbackIntervalMs));
    return () => window.clearInterval(timer);
  }, [fallback, fallbackIntervalMs]);

  const value = useMemo(() => ({ store, state, fallback, fallbackTick, provided: true }), [fallback, fallbackTick, state, store]);
  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

function useRealtimeContext(): RealtimeContextValue {
  return useContext(RealtimeContext);
}

export function useRealtimeTopic<T = unknown>(topic: string): RealtimeStreamEvent<T> | undefined {
  const { store } = useRealtimeContext();
  const [latest, setLatest] = useState<RealtimeStreamEvent<T> | undefined>(() => store.getLatest<T>(topic));
  useEffect(() => {
    setLatest(store.getLatest<T>(topic));
    return store.subscribe(topic, (event) => setLatest(event as RealtimeStreamEvent<T>));
  }, [store, topic]);
  return latest;
}

export function useRealtimeSubscription<T = unknown>(
  topic: string,
  listener: (event: RealtimeStreamEvent<T>) => void,
  options: { fallbackToNetwork?: boolean } = {},
): void {
  const { store } = useRealtimeContext();
  const providerAvailable = useRealtimeProviderAvailable();
  const listenerRef = useRef(listener);
  listenerRef.current = listener;
  useEffect(() => {
    if (providerAvailable) return store.subscribe(topic, (event) => listenerRef.current(event as RealtimeStreamEvent<T>));
    if (options.fallbackToNetwork === false) return undefined;
    const controller = new AbortController();
    void consumeRealtimeStream<T>([topic], (event) => listenerRef.current(event), controller.signal).catch(() => undefined);
    return () => controller.abort();
  }, [options.fallbackToNetwork, providerAvailable, store, topic]);
}

export function useRealtimeProviderAvailable(): boolean {
  return useRealtimeContext().provided;
}

export function useRealtimeState(): RealtimeStreamState | "idle" {
  return useRealtimeContext().state;
}

export function useRealtimeFallback(): 0 | 1 {
  return useRealtimeContext().fallback ? 1 : 0;
}

export function useRealtimeFallbackTick(): number {
  return useRealtimeContext().fallbackTick;
}
