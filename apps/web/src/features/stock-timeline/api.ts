import type { StockTimelineResponse } from "./types";
import { updateTaskActivity } from "../../shared/taskActivity";
import { apiClient } from "../../shared/apiClient";
import { registerStockObservationFocus } from "../quant-analysis/api";


export async function loadStockTimeline(
  symbol: string,
  asOf?: string,
  signal?: AbortSignal,
): Promise<StockTimelineResponse> {
  void registerStockObservationFocus(symbol).catch(() => undefined);
  const query = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  const taskId = `timeline:${symbol}:${asOf ?? "current"}`;
  updateTaskActivity({ id: taskId, label: `个股事件 K 线 ${symbol}`, stage: "正在读取日线与事件", state: "running", percent: 8 });
  try {
    updateTaskActivity({ id: taskId, label: `个股事件 K 线 ${symbol}`, stage: "正在解析 K 线与事件", state: "running", percent: 72 });
    const result = await apiClient.get<StockTimelineResponse>(
      `/api/v1/a-shares/${symbol}/timeline${query}`,
      { signal, context: "事件 K 线" },
    );
    updateTaskActivity({ id: taskId, label: `个股事件 K 线 ${symbol}`, stage: "事件 K 线已完成", state: "succeeded", percent: 100 });
    return result;
  } catch (error) {
    const aborted = error instanceof DOMException && error.name === "AbortError";
    updateTaskActivity({
      id: taskId,
      label: `个股事件 K 线 ${symbol}`,
      stage: aborted ? "事件 K 线已取消" : "事件 K 线失败",
      state: "failed",
      error: aborted ? "已取消本次请求" : error instanceof Error ? error.message : "网络或数据解析失败",
    });
    throw error;
  }
}
