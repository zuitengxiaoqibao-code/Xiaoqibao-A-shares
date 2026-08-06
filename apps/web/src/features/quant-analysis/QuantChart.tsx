import { useEffect, useRef } from "react";
import type { ECharts, EChartsOption } from "echarts";

export function QuantChart({
  option,
  ariaLabel,
}: {
  option: EChartsOption;
  ariaLabel: string;
}) {
  const element = useRef<HTMLDivElement>(null);
  const optionRef = useRef(option);
  const chartRef = useRef<ECharts | null>(null);
  optionRef.current = option;

  useEffect(() => {
    if (!element.current) return;
    const container = element.current;
    let disposed = false;
    let loading = false;
    const renderChart = () => {
      if (disposed || container.clientWidth <= 0 || container.clientHeight <= 0 || loading) return;
      if (!chartRef.current) {
        loading = true;
        container.dataset.chartState = "loading";
        void import("echarts").then(({ init }) => {
          if (disposed) return;
          chartRef.current = init(container, undefined, { renderer: "svg" });
          container.dataset.chartState = "ready";
          chartRef.current.setOption(optionRef.current, { notMerge: true });
          chartRef.current.resize();
        }).catch(() => {
          if (!disposed) container.dataset.chartState = "unavailable";
        }).finally(() => {
          loading = false;
        });
        return;
      }
      chartRef.current.setOption(optionRef.current, { notMerge: true });
      chartRef.current.resize();
    };
    const observer = typeof ResizeObserver === "undefined"
      ? null
      : new ResizeObserver(renderChart);
    observer?.observe(container);
    window.addEventListener("resize", renderChart);
    renderChart();
    return () => {
      disposed = true;
      container.dataset.chartState = "disposed";
      observer?.disconnect();
      window.removeEventListener("resize", renderChart);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div className="quant-chart" data-chart-state="idle" role="img" aria-label={ariaLabel} ref={element} />;
}
