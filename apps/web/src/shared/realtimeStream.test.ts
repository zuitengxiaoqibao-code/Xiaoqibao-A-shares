import { describe, expect, it, vi } from "vitest";
import { consumeRealtimeStream, parseRealtimeSseBuffer } from "./realtimeStream";

describe("generic realtime SSE stream", () => {
  it("parses complete frames and keeps a partial frame", () => {
    const parsed = parseRealtimeSseBuffer<{ value: number }>(
      'id: q-1\nevent: quant_strategy\ndata: {"kind":"quant_strategy","payload":{"value":1}}\n\n' +
      'data: {"kind":"company_research","payload":{"value":2}}',
    );
    expect(parsed.events).toHaveLength(1);
    expect(parsed.events[0].kind).toBe("quant_strategy");
    expect(parsed.events[0].payload.value).toBe(1);
    expect(parsed.rest).toContain("company_research");
  });

  it("reports connection state and forwards streamed events", async () => {
    const encoder = new TextEncoder();
    const response = new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"kind":"quant_strategy","payload":{"value":3}}\n\n'));
        controller.close();
      },
    }), { status: 200 });
    vi.stubGlobal("fetch", vi.fn(async () => response));
    const states: string[] = [];
    const values: number[] = [];
    await consumeRealtimeStream<{ value: number }>(["quant_strategy"], (event) => values.push(event.payload.value), new AbortController().signal, (state) => states.push(state));
    expect(values).toEqual([3]);
    expect(states).toEqual(["connected", "closed"]);
    vi.unstubAllGlobals();
  });
});
