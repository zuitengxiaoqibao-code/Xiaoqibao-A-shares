import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { setOption, resize, dispose, init } = vi.hoisted(() => {
  const setOption = vi.fn();
  const resize = vi.fn();
  const dispose = vi.fn();
  const init = vi.fn(() => ({ setOption, resize, dispose }));
  return { setOption, resize, dispose, init };
});

vi.mock("echarts", () => ({ init }));

import { QuantChart } from "./QuantChart";

describe("QuantChart", () => {
  let width = 0;
  let height = 0;
  let notifyResize: (() => void) | null = null;

  beforeEach(() => {
    width = 0;
    height = 0;
    notifyResize = null;
    vi.clearAllMocks();
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => width });
    Object.defineProperty(HTMLElement.prototype, "clientHeight", { configurable: true, get: () => height });
    vi.stubGlobal("ResizeObserver", class {
      constructor(callback: () => void) { notifyResize = callback; }
      observe() {}
      disconnect() {}
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("waits for a measurable container, then initializes and disposes ECharts", () => {
    const { unmount } = render(<QuantChart option={{ series: [] }} ariaLabel="测试图表" />);
    expect(init).not.toHaveBeenCalled();

    width = 640;
    height = 320;
    act(() => notifyResize?.());

    expect(init).toHaveBeenCalledTimes(1);
    expect(setOption).toHaveBeenCalledWith({ series: [] }, { notMerge: true });
    unmount();
    expect(dispose).toHaveBeenCalledTimes(1);
  });

  it("reuses the chart instance when the option changes", () => {
    const { rerender } = render(<QuantChart option={{ series: [{ data: [1] }] }} ariaLabel="测试图表" />);

    width = 640;
    height = 320;
    act(() => notifyResize?.());
    rerender(<QuantChart option={{ series: [{ data: [2] }] }} ariaLabel="测试图表" />);

    expect(init).toHaveBeenCalledTimes(1);
    expect(dispose).not.toHaveBeenCalled();
    expect(setOption).toHaveBeenLastCalledWith({ series: [{ data: [2] }] }, { notMerge: true });
  });
});
