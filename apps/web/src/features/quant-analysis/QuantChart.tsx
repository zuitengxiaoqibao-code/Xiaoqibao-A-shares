import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import type { EChartsOption } from "echarts";

export function QuantChart({
  option,
  ariaLabel,
}: {
  option: EChartsOption;
  ariaLabel: string;
}) {
  const element = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!element.current) return;
    const container = element.current;
    let chart: ReturnType<typeof echarts.init> | null = null;
    let disposed = false;
    const renderChart = () => {
      if (disposed || container.clientWidth <= 0 || container.clientHeight <= 0) return;
      if (!chart) chart = echarts.init(container, undefined, { renderer: "svg" });
      chart.setOption(option, { notMerge: true });
      chart.resize();
    };
    const observer = typeof ResizeObserver === "undefined"
      ? null
      : new ResizeObserver(renderChart);
    observer?.observe(container);
    window.addEventListener("resize", renderChart);
    renderChart();
    return () => {
      disposed = true;
      observer?.disconnect();
      window.removeEventListener("resize", renderChart);
      chart?.dispose();
    };
  }, [option]);

  return <div className="quant-chart" role="img" aria-label={ariaLabel} ref={element} />;
}
