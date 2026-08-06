import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TdxFormulaPanel } from "./TdxFormulaPanel";

describe("TdxFormulaPanel", () => {
  it("shows only explicit returned formula values", async () => {
    const load = vi.fn(async () => ({
      status: "ready" as const,
      points: [{
        symbol: "600000",
        name: "浦发银行",
        formula_name: "formula_process_mul_zb",
        values: { MACD: "0.25" },
        fetched_at: "2026-08-06T08:00:00Z",
        source: "tdx-local-rpc",
      }],
      fetched_at: "2026-08-06T08:00:00Z",
      source: "tdx-local-rpc",
      detail: null,
    }));

    render(<TdxFormulaPanel symbol="600000" load={load} />);

    await waitFor(() => expect(screen.getByText("0.25")).toBeInTheDocument());
    expect(screen.getByText("MACD")).toBeInTheDocument();
    expect(load).toHaveBeenCalledWith("formula_process_mul_zb", ["600000"]);
  });

  it("explains unavailable formula evidence instead of filling zero", async () => {
    render(<TdxFormulaPanel symbol="600000" load={async () => ({
      status: "unavailable" as const,
      points: [],
      fetched_at: null,
      source: "tdx-local-rpc",
      detail: "接口不可用",
    })} />);

    await waitFor(() => expect(screen.getByText("公式结果不可用")).toBeInTheDocument());
    expect(screen.getByText("接口不可用")).toBeInTheDocument();
  });
});
