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
const DEFAULT_DOMAIN_CONCURRENCY = 6;
let domainConcurrency = DEFAULT_DOMAIN_CONCURRENCY;

type QueuedNetworkRequest = {
  run: () => Promise<Response>;
  resolve: (response: Response) => void;
  reject: (error: unknown) => void;
};

type DomainQueue = {
  active: number;
  pending: QueuedNetworkRequest[];
};

const domainQueues = new Map<string, DomainQueue>();

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

function normalizedUrl(input: RequestInfo | URL): string {
  const raw = input instanceof Request ? input.url : String(input);
  try {
    const parsed = new URL(raw, window.location.origin);
    const entries = [...parsed.searchParams.entries()].sort(([leftKey, leftValue], [rightKey, rightValue]) => (
      leftKey.localeCompare(rightKey) || leftValue.localeCompare(rightValue)
    ));
    parsed.search = "";
    for (const [key, value] of entries) parsed.searchParams.append(key, value);
    parsed.hash = "";
    return parsed.toString();
  } catch {
    return raw.split("#", 1)[0];
  }
}

function requestKey(input: RequestInfo | URL, init?: RequestInit): string {
  const request = input instanceof Request ? input : null;
  return JSON.stringify({
    url: normalizedUrl(input),
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

function requestDomainGroup(input: RequestInfo | URL): string {
  const url = input instanceof Request ? input.url : String(input);
  try {
    return new URL(url, window.location.origin).pathname.replace(/^\/api\/v1\//, "").split("/")[0] || "http";
  } catch {
    return "http";
  }
}

function drainDomainQueue(domain: string): void {
  const queue = domainQueues.get(domain);
  if (!queue) return;
  while (queue.active < domainConcurrency && queue.pending.length > 0) {
    const item = queue.pending.shift();
    if (!item) break;
    queue.active += 1;
    let request: Promise<Response>;
    try {
      request = item.run();
    } catch (error) {
      request = Promise.reject(error);
    }
    request.then(item.resolve, item.reject)
      .finally(() => {
        queue.active = Math.max(0, queue.active - 1);
        if (queue.active === 0 && queue.pending.length === 0) domainQueues.delete(domain);
        else drainDomainQueue(domain);
      });
  }
}

function scheduleNetworkRequest(domain: string, run: () => Promise<Response>): Promise<Response> {
  return new Promise<Response>((resolve, reject) => {
    const queue = domainQueues.get(domain) ?? { active: 0, pending: [] };
    domainQueues.set(domain, queue);
    queue.pending.push({ run, resolve, reject });
    drainDomainQueue(domain);
  });
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
        resolve(typeof response.clone === "function" ? response.clone() : response);
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
    current.response = scheduleNetworkRequest(
      requestDomainGroup(input),
      () => fetch(input, { ...init, signal: controller.signal }),
    );
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
  domainQueues.forEach((queue) => {
    queue.pending.splice(0).forEach((item) => item.reject(abortError()));
  });
  domainQueues.clear();
  domainConcurrency = DEFAULT_DOMAIN_CONCURRENCY;
  stats.callers = 0;
  stats.networkRequests = 0;
  stats.coalescedCallers = 0;
}

export function setCoalescedFetchConcurrencyForTests(limit: number): void {
  domainConcurrency = Math.max(1, Math.floor(limit));
}
