import { beforeEach, describe, expect, it, vi } from "vitest";
import { readRequestLedger, requestLedger, resetRequestLedgerForTests } from "./requestLedger";

describe("requestLedger", () => {
  beforeEach(() => resetRequestLedgerForTests());

  it("shares an in-flight operation for the same key", async () => {
    let resolveOperation!: (value: string) => void;
    const operation = vi.fn(() => new Promise<string>((resolve) => { resolveOperation = resolve; }));

    const first = requestLedger.run("overview:latest", operation, { domain: "overview" });
    const second = requestLedger.run("overview:latest", operation, { domain: "overview" });
    resolveOperation("ready");

    await expect(first).resolves.toBe("ready");
    await expect(second).resolves.toBe("ready");
    expect(operation).toHaveBeenCalledTimes(1);
    expect(readRequestLedger("overview")).toMatchObject({ count: 1, failures: 0, inFlight: 0 });
  });

  it("removes failed operations so a later call can retry", async () => {
    const operation = vi.fn()
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce("recovered");

    await expect(requestLedger.run("company:600519", operation, { domain: "company" })).rejects.toThrow("offline");
    await expect(requestLedger.run("company:600519", operation, { domain: "company" })).resolves.toBe("recovered");
    expect(operation).toHaveBeenCalledTimes(2);
    expect(readRequestLedger("company")).toMatchObject({ count: 2, failures: 1, inFlight: 0 });
  });

  it("lets a new caller take over when the shared operation was cancelled", async () => {
    let rejectOriginal!: (reason: unknown) => void;
    const original = vi.fn(() => new Promise<string>((_resolve, reject) => { rejectOriginal = reject; }));
    const replacement = vi.fn(async () => "fresh");

    const first = requestLedger.run("company:301526", original, { domain: "company" });
    const second = requestLedger.run("company:301526", replacement, { domain: "company" });
    rejectOriginal(new DOMException("signal is aborted without reason", "AbortError"));

    await expect(first).rejects.toMatchObject({ name: "AbortError" });
    await expect(second).resolves.toBe("fresh");
    expect(replacement).toHaveBeenCalledTimes(1);
    expect(readRequestLedger("company")).toMatchObject({ count: 2, failures: 0, inFlight: 0 });
  });

  it("reports bounded latency percentiles and cache reuse", async () => {
    requestLedger.record({ key: "a", domain: "overview", durationMs: 10, status: "ready", cacheHit: true });
    requestLedger.record({ key: "b", domain: "overview", durationMs: 30, status: "ready", cacheHit: false });
    requestLedger.record({ key: "c", domain: "overview", durationMs: 50, status: "error", cacheHit: false });

    expect(readRequestLedger("overview")).toMatchObject({ count: 3, failures: 1, p50Ms: 30, p95Ms: 50, cacheHitRate: 33.3 });
  });
});
