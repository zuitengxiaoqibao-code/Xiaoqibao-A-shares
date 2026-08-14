export type IncrementalSnapshotOptions<T> = {
  tradeDate: (value: T) => string | null | undefined;
  observedAt: (value: T) => string | null | undefined;
  isEmpty?: (value: T) => boolean;
  merge?: (current: T, incoming: T) => T;
};

export function mergeEntitySnapshot<T>(
  current: T[], incoming: T[], identity: (value: T) => string,
): T[] {
  const merged = new Map(current.map((item) => [identity(item), item]));
  incoming.forEach((item) => merged.set(identity(item), item));
  return [...merged.values()];
}

export function appendUniqueEntities<T>(
  current: T[], incoming: T[], identity: (value: T) => string,
): T[] {
  const known = new Set(current.map(identity));
  return [...current, ...incoming.filter((item) => !known.has(identity(item)))];
}

export function resolveIncrementalResponse<T>(
  current: T | null,
  incoming: T,
  options: IncrementalSnapshotOptions<T>,
): T {
  if (!current) return incoming;
  const currentDate = options.tradeDate(current);
  const incomingDate = options.tradeDate(incoming);
  if (currentDate && incomingDate && currentDate !== incomingDate) {
    const currentDay = Date.parse(`${currentDate}T00:00:00Z`);
    const incomingDay = Date.parse(`${incomingDate}T00:00:00Z`);
    if (Number.isFinite(currentDay) && Number.isFinite(incomingDay)) return incomingDay > currentDay ? incoming : current;
    return incoming;
  }
  const currentObservedAt = Date.parse(options.observedAt(current) ?? "");
  const incomingObservedAt = Date.parse(options.observedAt(incoming) ?? "");
  if (Number.isFinite(currentObservedAt) && Number.isFinite(incomingObservedAt) && incomingObservedAt < currentObservedAt) {
    return current;
  }
  if (options.isEmpty?.(incoming) && !options.isEmpty(current)) return current;
  return options.merge?.(current, incoming) ?? incoming;
}
