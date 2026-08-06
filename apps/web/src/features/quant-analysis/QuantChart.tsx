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
  const optionRef = useRef(option);
  const chartRef = useRef<ReturnType<typeof echarts.init> | null>(null);
  optionRef.current = option;

  useEffect(() => {
    if (!element.current) return;
    const container = element.current;
    let disposed = false;
    const renderChart = () => {
      if (disposed || container.clientWidth <= 0 || container.clientHeight <= 0) return;
      if (!chartRef.current) chartRef.current = echarts.init(container, undefined, { renderer: "svg" });
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
      observer?.disconnect();
      window.removeEventListener("resize", renderChart);
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    chartRef.current?.setOption(option, { notMerge: true });
  }, [option]);

  return <div className="quant-chart" role="img" aria-label={ariaLabel} ref={element} />;
}
