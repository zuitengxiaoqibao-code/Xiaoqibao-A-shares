export type CoalescedFetchStats = {
  callers: number;
  networkRequests: number;
  coalescedCallers: number;
  activeRequests: number;
};

import { recordPerfEvent } from "./performance/perfLedger";

type InFlightRequest = {
  controller: AbortController;
  response: Promise<Response>;
  subscribers: number;
  settled: boolean;
};

const inFlight = new Map<string, InFlightRequest>();
const stats = { callers: 0, networkRequests: 0, coalescedCallers: 0 };

function abortError(): DOMException {
  return new DOMException("Aborted", "AbortError");
}

function normalizedHeaders(input: RequestInfo | URL, init?: RequestInit): string {
  const headers = new Headers(input instanceof Request ? input.headers : undefined);
  new Headers(init?.headers).forEach((value, name) => headers.set(name, value));
  return [...headers.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([name, value]) => `${name}:${value}`)
    .join("\n");
}

function requestMethod(input: RequestInfo | URL, init?: RequestInit): string {
  return (init?.method ?? (input instanceof Request ? input.method : "GET")).toUpperCase();
}

function requestKey(input: RequestInfo | URL, init?: RequestInit): string {
  const url = input instanceof Request ? input.url : String(input);
  const request = input instanceof Request ? input : null;
  return JSON.stringify({
    url,
    headers: normalizedHeaders(input, init),
    credentials: init?.credentials ?? request?.credentials ?? "same-origin",
    cache: init?.cache ?? request?.cache ?? "default",
    mode: init?.mode ?? request?.mode ?? "cors",
    redirect: init?.redirect ?? request?.redirect ?? "follow",
    referrer: init?.referrer ?? request?.referrer ?? "about:client",
    referrerPolicy: init?.referrerPolicy ?? request?.referrerPolicy ?? "",
    integrity: init?.integrity ?? request?.integrity ?? "",
  });
}

function requestDomain(input: RequestInfo | URL): string {
  const url = input instanceof Request ? input.url : String(input);
  try {
    return new URL(url, window.location.origin).pathname.replace(/^\/api\/v1\//, "").split("/").slice(0, 2).join("/") || "http";
  } catch {
    return "http";
  }
}

function releaseSubscriber(entry: InFlightRequest): void {
  entry.subscribers = Math.max(0, entry.subscribers - 1);
  if (entry.subscribers === 0 && !entry.settled) entry.controller.abort();
}

function subscribe(entry: InFlightRequest, signal?: AbortSignal | null): Promise<Response> {
  if (signal?.aborted) return Promise.reject(abortError());
  entry.subscribers += 1;
  return new Promise<Response>((resolve, reject) => {
    let released = false;
    const release = () => {
      if (released) return;
      released = true;
      signal?.removeEventListener("abort", onAbort);
      releaseSubscriber(entry);
    };
    const onAbort = () => {
      release();
      reject(abortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
    entry.response.then(
      (response) => {
        if (released) return;
        release();
        resolve(response.clone());
      },
      (error) => {
        if (released) return;
        release();
        reject(error);
      },
    );
  });
}

export function coalescedFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  stats.callers += 1;
  if (requestMethod(input, init) !== "GET") {
    stats.networkRequests += 1;
    return fetch(input, init);
  }
  if (init?.signal?.aborted || (input instanceof Request && input.signal.aborted)) {
    return Promise.reject(abortError());
  }

  const key = requestKey(input, init);
  let entry = inFlight.get(key);
  if (entry) {
    stats.coalescedCallers += 1;
  } else {
    const controller = new AbortController();
    stats.networkRequests += 1;
    entry = {
      controller,
      subscribers: 0,
      settled: false,
      response: Promise.resolve(new Response()),
    };
    const current = entry;
    const startedAt = typeof performance !== "undefined" ? performance.now() : Date.now();
    current.response = fetch(input, { ...init, signal: controller.signal });
    current.response.then(
      (response) => {
        recordPerfEvent({
          domain: requestDomain(input), phase: "fetch", durationMs: (typeof performance !== "undefined" ? performance.now() : Date.now()) - startedAt,
          cacheHit: false, status: response.ok ? "ready" : "error", observedAt: new Date().toISOString(),
        });
        current.settled = true;
        if (inFlight.get(key) === current) inFlight.delete(key);
      },
      () => {
        recordPerfEvent({
          domain: requestDomain(input), phase: "fetch", durationMs: (typeof performance !== "undefined" ? performance.now() : Date.now()) - startedAt,
          cacheHit: false, status: "error", observedAt: new Date().toISOString(),
        });
        current.settled = true;
        if (inFlight.get(key) === current) inFlight.delete(key);
      },
    );
    inFlight.set(key, current);
  }
  const callerSignal = init?.signal ?? (input instanceof Request ? input.signal : undefined);
  return subscribe(entry, callerSignal);
}

export function readCoalescedFetchStats(): CoalescedFetchStats {
  return { ...stats, activeRequests: inFlight.size };
}

export function resetCoalescedFetchForTests(): void {
  inFlight.forEach((entry) => entry.controller.abort());
  inFlight.clear();
  stats.callers = 0;
  stats.networkRequests = 0;
  stats.coalescedCallers = 0;
}
