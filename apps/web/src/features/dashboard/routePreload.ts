type IdleHost = {
  requestIdleCallback?: (callback: () => void) => number;
  cancelIdleCallback?: (id: number) => void;
};

export function scheduleRoutePreload(
  loaders: Array<() => Promise<unknown>>,
  host: IdleHost = window,
): () => void {
  let cancelled = false;
  const run = () => {
    if (cancelled) return;
    for (const loader of loaders) {
      void loader().catch(() => undefined);
    }
  };

  if (host.requestIdleCallback) {
    const id = host.requestIdleCallback(run);
    return () => {
      cancelled = true;
      host.cancelIdleCallback?.(id);
    };
  }

  const id = window.setTimeout(run, 350);
  return () => {
    cancelled = true;
    window.clearTimeout(id);
  };
}
