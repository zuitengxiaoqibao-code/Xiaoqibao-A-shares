import type { RealtimeStreamEvent } from "../realtimeStream";

type Listener = (event: RealtimeStreamEvent) => void;

/** In-memory fan-out for the single application realtime connection. */
export class RealtimeStore {
  private readonly latest = new Map<string, RealtimeStreamEvent>();
  private readonly listeners = new Map<string, Set<Listener>>();
  private visible = true;
  private readonly pending = new Map<string, RealtimeStreamEvent>();

  get subscriberCount(): number {
    let count = 0;
    this.listeners.forEach((items) => { count += items.size; });
    return count;
  }

  subscribe(topic: string, listener: Listener): () => void {
    const listeners = this.listeners.get(topic) ?? new Set<Listener>();
    listeners.add(listener);
    this.listeners.set(topic, listeners);
    return () => {
      listeners.delete(listener);
      if (listeners.size === 0) this.listeners.delete(topic);
    };
  }

  getLatest<T = unknown>(topic: string): RealtimeStreamEvent<T> | undefined {
    return this.latest.get(topic) as RealtimeStreamEvent<T> | undefined;
  }

  publish(event: RealtimeStreamEvent): void {
    this.latest.set(event.kind, event);
    if (!this.visible) {
      this.pending.set(event.kind, event);
      return;
    }
    this.notify(event);
  }

  setVisible(visible: boolean): void {
    if (this.visible === visible) return;
    this.visible = visible;
    if (!visible) return;
    const pending = [...this.pending.values()].sort((a, b) => a.sequence - b.sequence);
    this.pending.clear();
    pending.forEach((event) => this.notify(event));
  }

  private notify(event: RealtimeStreamEvent): void {
    this.listeners.get(event.kind)?.forEach((listener) => listener(event));
  }
}
