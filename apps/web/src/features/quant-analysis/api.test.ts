import { afterEach, describe, expect, it, vi } from "vitest";

import { loadKronosForecast, loadQuantCalibration, loadQuantStrategy, loadTdxFormula } from "./api";

describe("loadKronosForecast", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the selected symbol, evidence date and forecast horizon", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ status: "unavailable" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await loadKronosForecast("600000", "2026-07-24", 10);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/a-shares/first-limit-up/quant-forecast?symbol=600000&horizon=10&as_of=2026-07-24",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });

  it("rejects a non-success response instead of returning fabricated evidence", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("down", { status: 503 })));

    await expect(loadKronosForecast("600000")).rejects.toThrow("Kronos 预测请求失败 (503)");
  });
});

describe("loadQuantStrategy", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("requests the requested recommendation limit", async () => {
    const payload = { status: "partial", candidates: [] };
    const fetchMock = vi.fn(async () => new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(loadQuantStrategy(8)).resolves.toEqual(payload);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/a-shares/quant-strategy?limit=8",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });
});

describe("loadQuantCalibration", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads the append-only calibration report without translating unavailable values", async () => {
    const payload = { status: "partial", horizon: 5, total_sample_count: 4, mature_sample_count: 4, splits: [], integrity: { future_function_check: "passed", survivorship_check: "unavailable", duplicate_decision_check: "passed", limitations: ["样本不足"] }, generated_at: "2026-08-14T08:00:00Z", limitations: ["样本不足"] };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(payload), { status: 200 })));
    await expect(loadQuantCalibration(5)).resolves.toEqual(payload);
  });
});

describe("loadTdxFormula", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("sends a read-only formula name and each selected code", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ status: "unavailable" }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await loadTdxFormula("formula_process_mul_zb", ["600000", "000001"]);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/tdx/local/formula?formula_name=formula_process_mul_zb&stock_codes=600000&stock_codes=000001",
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    );
  });
});
