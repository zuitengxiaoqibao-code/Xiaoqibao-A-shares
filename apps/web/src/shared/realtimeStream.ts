export type RealtimeStreamEvent<T = unknown> = {
  event_id: string;
  kind: string;
  sequence: number;
  observed_at: string;
  source: string;
  freshness: string;
  payload: T;
};

export type RealtimeStreamState = "connected" | "closed" | "error";

export function parseRealtimeSseBuffer<T>(buffer: string): { events: RealtimeStreamEvent<T>[]; rest: string } {
  const events: RealtimeStreamEvent<T>[] = [];
  const frames = buffer.split("\n\n");
  const rest = frames.pop() ?? "";
  for (const frame of frames) {
    const data = frame.split("\n")
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) continue;
    try {
      const parsed = JSON.parse(data) as RealtimeStreamEvent<T>;
      if (parsed.kind && parsed.payload !== undefined) events.push(parsed);
    } catch {
      // Keep incomplete or malformed frames out of the UI; the next frame may recover.
    }
  }
  return { events, rest };
}

export async function consumeRealtimeStream<T>(
  topics: string[],
  onEvent: (event: RealtimeStreamEvent<T>) => void,
  signal: AbortSignal,
  onState?: (state: RealtimeStreamState) => void,
): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/operations/realtime-stream?topics=${encodeURIComponent(topics.join(","))}`, {
      signal,
      headers: { Accept: "text/event-stream" },
    });
  } catch (error) {
    if (!(error instanceof DOMException && error.name === "AbortError")) onState?.("error");
    throw error;
  }
  if (!response.ok || !response.body) {
    onState?.("error");
    throw new Error(`实时推送不可用 (${response.status})`);
  }
  onState?.("connected");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (!signal.aborted) {
      const chunk = await reader.read();
      if (chunk.done) break;
      buffer += decoder.decode(chunk.value, { stream: true });
      const parsed = parseRealtimeSseBuffer<T>(buffer);
      buffer = parsed.rest;
      parsed.events.forEach(onEvent);
    }
  } finally {
    reader.releaseLock();
    if (!signal.aborted) onState?.("closed");
  }
}
