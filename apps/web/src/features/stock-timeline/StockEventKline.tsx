import type { EChartsOption } from "echarts";
import { AlertTriangle, CheckCircle2, ExternalLink, Newspaper, RefreshCw } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { QuantChart } from "../quant-analysis/QuantChart";
import { chartTheme } from "../../shared/visualization/chartTheme";
import { loadStockTimeline } from "./api";
import type {
  StockTimelineEvent,
  StockTimelineLoader,
  StockTimelineResponse,
} from "./types";


const UP_COLOR = chartTheme.upColor;
const DOWN_COLOR = chartTheme.downColor;
const NEUTRAL_COLOR = chartTheme.warningColor;
const UNCERTAIN_COLOR = chartTheme.unavailableColor;
const SELECTED_COLOR = "#f8fafc";
const MAX_CHART_EVENTS = 15;
const MAX_COMPACT_CHART_EVENTS = 3;
const MIN_EVENT_BAR_GAP = 5;
const cache = new Map<string, StockTimelineResponse>();

const directionNames: Record<StockTimelineEvent["direction"], string> = {
  positive: "正向",
  negative: "负向",
  neutral: "中性",
  uncertain: "影响待核验",
};
const urgencyNames = { breaking: "突发", tracking: "跟踪", normal: "常规" } as const;
const verificationNames = {
  multi_source_confirmed: "多源确认",
  verified: "已核验",
  pending: "待核验",
  unverified: "未核验",
} as const;
const associationNames = {
  direct: "直接关联",
  context: "上下文关联",
  theme: "题材关联",
  macro: "宏观",
} as const;

function directionColor(direction: StockTimelineEvent["direction"]): string {
  if (direction === "positive") return UP_COLOR;
  if (direction === "negative") return DOWN_COLOR;
  if (direction === "neutral") return NEUTRAL_COLOR;
  return UNCERTAIN_COLOR;
}

function numericConfidence(value: string | null): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function selectTimelineChartEvents(
  data: StockTimelineResponse,
  selectedEventId: string | null,
  maxEvents = MAX_CHART_EVENTS,
): StockTimelineEvent[] {
  const dateIndex = new Map(data.bars.map((item, index) => [item.trade_date, index]));
  const mapped = data.events
    .filter((event) => event.mapped_trade_date && dateIndex.has(event.mapped_trade_date))
    .sort((left, right) => left.occurred_at.localeCompare(right.occurred_at));
  if (mapped.length <= maxEvents) return mapped;

  const ranked = [...mapped].sort((left, right) => {
    const selectedDifference = Number(right.event_id === selectedEventId) - Number(left.event_id === selectedEventId);
    if (selectedDifference) return selectedDifference;
    const associationDifference = numericConfidence(right.association_confidence) - numericConfidence(left.association_confidence);
    if (associationDifference) return associationDifference;
    const directionDifference = Number(right.direction !== "uncertain") - Number(left.direction !== "uncertain");
    if (directionDifference) return directionDifference;
    const confidenceDifference = numericConfidence(right.confidence) - numericConfidence(left.confidence);
    if (confidenceDifference) return confidenceDifference;
    return right.occurred_at.localeCompare(left.occurred_at);
  });
  const selected: StockTimelineEvent[] = [];
  for (const event of ranked) {
    if (selected.length >= maxEvents) break;
    const index = dateIndex.get(event.mapped_trade_date as string) as number;
    const nearbyCount = selected.filter((current) => {
      const currentIndex = dateIndex.get(current.mapped_trade_date as string) as number;
      return Math.abs(currentIndex - index) < MIN_EVENT_BAR_GAP;
    }).length;
    if (nearbyCount < 3) selected.push(event);
  }
  return selected.sort((left, right) => left.occurred_at.localeCompare(right.occurred_at));
}

type Marker = {
  name: string;
  xAxis: string;
  lineStyle: { color: string; width: number; type: "solid" | "dashed" };
  label: {
    show: true;
    formatter: string;
    color: string;
    fontSize: number;
    fontWeight: number;
    rotate: 0;
    position: "insideEndTop";
    offset: [number, number];
    lineHeight: number;
  };
};

type NumberedTimelineEvent = {
  event: StockTimelineEvent;
  number: string;
};

function numberTimelineEvents(events: StockTimelineEvent[]): NumberedTimelineEvent[] {
  return events.map((event, index) => ({
    event,
    number: String(index + 1).padStart(2, "0"),
  }));
}

function eventMarkers(
  data: StockTimelineResponse,
  selectedEventId: string | null,
  maxEvents: number,
): Marker[] {
  const dateIndex = new Map(data.bars.map((item, index) => [item.trade_date, index]));
  const mapped = numberTimelineEvents(selectTimelineChartEvents(data, selectedEventId, maxEvents));
  const sameDateCounts = new Map<string, number>();
  let previousIndex = Number.NEGATIVE_INFINITY;
  let previousLane = 2;
  return mapped.map(({ event, number }) => {
    const tradeDate = event.mapped_trade_date as string;
    const index = dateIndex.get(tradeDate) as number;
    const lane = index - previousIndex < MIN_EVENT_BAR_GAP ? (previousLane + 1) % 3 : 0;
    previousIndex = index;
    previousLane = lane;
    const dateCount = sameDateCounts.get(tradeDate) ?? 0;
    sameDateCounts.set(tradeDate, dateCount + 1);
    const selected = selectedEventId === event.event_id;
    const color = directionColor(event.direction);
    return {
      name: event.event_id,
      xAxis: tradeDate,
      lineStyle: {
        color,
        width: selected ? 2 : 1,
        type: selected ? "solid" : "dashed",
      },
      label: {
        show: true,
        formatter: number,
        color: selected ? SELECTED_COLOR : color,
        fontSize: 12,
        fontWeight: selected ? 800 : 650,
        rotate: 0,
        position: "insideEndTop",
        offset: [dateCount * 22, lane * 20] as [number, number],
        lineHeight: 13,
      },
    };
  });
}

export function stockTimelineOption(
  data: StockTimelineResponse,
  selectedEventId: string | null,
  maxEvents = MAX_CHART_EVENTS,
): EChartsOption {
  const dates = data.bars.map((item) => item.trade_date);
  const markers = eventMarkers(data, selectedEventId, maxEvents);
  const mappedEvents = new Map(data.events.map((event) => [event.event_id, event]));
  const barsByDate = new Map(data.bars.map((item) => [item.trade_date, item]));
  return {
    animation: false,
    backgroundColor: "transparent",
    grid: [
      { left: 58, right: 18, top: 72, bottom: 102 },
      { left: 58, right: 18, height: 54, bottom: 34 },
    ],
    tooltip: {
      trigger: "axis",
      confine: true,
      backgroundColor: "rgba(8,15,25,.96)",
      borderColor: "#334155",
      textStyle: { color: "#e2e8f0", fontFamily: "JetBrains Mono" },
    },
    axisPointer: { link: [{ xAxisIndex: "all" }] },
    xAxis: [
      {
        type: "category",
        data: dates,
        boundaryGap: true,
        axisLabel: { color: "#8290a3", fontSize: 12, hideOverlap: true },
        axisLine: { lineStyle: { color: "#344255" } },
        axisTick: { show: false },
      },
      {
        type: "category",
        data: dates,
        boundaryGap: true,
        gridIndex: 1,
        axisLabel: { show: false },
        axisLine: { show: false },
        axisTick: { show: false },
      },
    ],
    yAxis: [
      {
        type: "value",
        scale: true,
        axisLabel: { color: "#8290a3", fontSize: 12 },
        splitLine: { lineStyle: { color: "rgba(85,104,128,.18)" } },
      },
      {
        type: "value",
        gridIndex: 1,
        axisLabel: { show: false },
        splitLine: { show: false },
      },
    ],
    dataZoom: [
      { type: "inside", xAxisIndex: [0, 1], start: 0, end: 100 },
      {
        type: "slider",
        xAxisIndex: [0, 1],
        height: 14,
        bottom: 8,
        borderColor: "#334155",
        fillerColor: "rgba(234,179,8,.12)",
        handleStyle: { color: "#eab308" },
        textStyle: { color: "#8290a3" },
      },
    ],
    series: [
      {
        name: "日 K",
        type: "candlestick",
        data: data.bars.map((item) => [
          Number(item.open), Number(item.close), Number(item.low), Number(item.high),
        ]),
        itemStyle: {
          color: UP_COLOR,
          color0: DOWN_COLOR,
          borderColor: UP_COLOR,
          borderColor0: DOWN_COLOR,
        },
        markLine: {
          symbol: ["none", "none"],
          silent: true,
          data: markers,
        },
        markPoint: {
          symbol: "circle",
          silent: true,
          label: { show: false },
          data: markers.map((marker) => {
            const event = mappedEvents.get(marker.name) as StockTimelineEvent;
            const bar = barsByDate.get(marker.xAxis);
            const selected = event.event_id === selectedEventId;
            return {
              name: event.event_id,
              coord: [marker.xAxis, Number(bar?.high ?? 0)],
              symbolSize: selected ? 10 : 7,
              itemStyle: {
                color: "#07111d",
                borderColor: directionColor(event.direction),
                borderWidth: selected ? 3 : 2,
              },
            };
          }),
        },
      },
      {
        name: "成交量",
        type: "bar",
        xAxisIndex: 1,
        yAxisIndex: 1,
        data: data.bars.map((item) => ({
          value: item.volume,
          itemStyle: {
            color: Number(item.close) >= Number(item.open)
              ? "rgba(239,68,68,.42)"
              : "rgba(34,197,94,.42)",
          },
        })),
      },
    ],
  };
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Shanghai",
  }).format(new Date(value));
}

function formatEventDate(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    timeZone: "Asia/Shanghai",
  }).format(new Date(value)).replace("/", "-");
}

function eventTitle(event: StockTimelineEvent): string {
  const source = event.headline.trim() || event.label.trim() || event.themes[0]?.trim() || "事件标题待补充";
  return source.replace(/\s+/g, " ");
}

function percent(value: string | null): string {
  if (value === null) return "--";
  return `${Math.round(Number(value) * 100)}%`;
}

export function StockEventKline({
  symbol,
  asOf,
  refreshToken,
  load = loadStockTimeline,
}: {
  symbol: string;
  asOf?: string;
  refreshToken?: string | number | null;
  load?: StockTimelineLoader;
}) {
  const cacheKey = `${symbol}:${asOf ?? "current"}`;
  const [data, setData] = useState<StockTimelineResponse | null>(() => cache.get(cacheKey) ?? null);
  const [loading, setLoading] = useState(!data);
  const [error, setError] = useState("");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [chartEventLimit, setChartEventLimit] = useState(() => (
    typeof window !== "undefined"
      && typeof window.matchMedia === "function"
      && window.matchMedia("(max-width: 700px)").matches
      ? MAX_COMPACT_CHART_EVENTS
      : MAX_CHART_EVENTS
  ));

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(max-width: 700px)");
    const updateLimit = () => setChartEventLimit(query.matches ? MAX_COMPACT_CHART_EVENTS : MAX_CHART_EVENTS);
    updateLimit();
    query.addEventListener("change", updateLimit);
    return () => query.removeEventListener("change", updateLimit);
  }, []);

  useEffect(() => {
    setSelectedEventId(null);
  }, [cacheKey]);

  useEffect(() => {
    const controller = new AbortController();
    const cached = cache.get(cacheKey) ?? null;
    setData(cached);
    setLoading(!cached);
    setError("");
    void load(symbol, asOf, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        cache.set(cacheKey, result);
        setData(result);
      })
      .catch((caught) => {
        if (controller.signal.aborted) return;
        setError(caught instanceof Error ? caught.message : "事件 K 线暂不可用");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [asOf, cacheKey, load, refreshToken, symbol]);

  const option = useMemo(
    () => data && data.bars.length ? stockTimelineOption(data, selectedEventId, chartEventLimit) : null,
    [chartEventLimit, data, selectedEventId],
  );
  const chartEvents = useMemo(
    () => data ? selectTimelineChartEvents(data, selectedEventId, chartEventLimit) : [],
    [chartEventLimit, data, selectedEventId],
  );
  const chartEventIds = useMemo(
    () => new Set(chartEvents.map((event) => event.event_id)),
    [chartEvents],
  );
  const numberedChartEvents = useMemo(
    () => numberTimelineEvents(chartEvents),
    [chartEvents],
  );
  const selectedEvent = useMemo(
    () => data?.events.find((event) => event.event_id === selectedEventId) ?? null,
    [data, selectedEventId],
  );

  useEffect(() => {
    if (!data) return;
    setSelectedEventId((current) => {
      if (current && data.events.some((event) => event.event_id === current)) return current;
      return chartEvents.at(-1)?.event_id ?? null;
    });
  }, [chartEvents, data]);

  return <section className="terminal-panel stock-event-kline" aria-label="个股新闻与热点事件 K 线">
    <header className="stock-event-kline-header">
      <div><span className="event-kline-icon"><Newspaper size={18} /></span><div><p>NEWS / PRICE EVIDENCE</p><h2>事件 K 线</h2></div></div>
      <div className="event-kline-legend"><span className="up">红涨</span><span className="down">绿跌</span><span className="uncertain">灰色·影响待核验</span>{loading && <RefreshCw className="spin" size={14} />}</div>
    </header>
    {error && !data ? <div className="stock-timeline-state error" role="alert"><AlertTriangle size={18} /><b>事件 K 线暂不可用</b><span>{error}</span></div> : !data || data.status === "unavailable" || !option ? <div className="stock-timeline-state"><AlertTriangle size={18} /><b>本地日线尚未就绪</b><span>不会使用示例行情补位</span></div> : <>
      {numberedChartEvents.length > 0 && <nav className="stock-event-index" aria-label="K 线事件索引">
        {numberedChartEvents.map(({ event, number }) => {
          const selected = selectedEventId === event.event_id;
          const title = eventTitle(event);
          return <button
            key={event.event_id}
            type="button"
            data-testid="stock-event-index-item"
            className={`stock-event-index-item direction-${event.direction}`}
            aria-label={`${number} ${formatEventDate(event.occurred_at)} ${title} ${directionNames[event.direction]} ${urgencyNames[event.urgency]} ${verificationNames[event.verification_state]} ${associationNames[event.association_kind]}`}
            aria-pressed={selected}
            onClick={() => setSelectedEventId(event.event_id)}
          >
            <span className="event-index-number">{number}</span>
            <span className="event-index-date">{formatEventDate(event.occurred_at)}</span>
            <strong title={title}>{title}</strong>
            <span className="event-index-status"><b>{urgencyNames[event.urgency]} · {associationNames[event.association_kind]}</b><small>{verificationNames[event.verification_state]}</small></span>
          </button>;
        })}
      </nav>}
      {selectedEvent && <section
        className={`stock-event-detail direction-${selectedEvent.direction}`}
        aria-label="当前事件详情"
      >
        <div className="stock-event-detail-heading">
          <div className="stock-event-detail-badges">
            <span>{directionNames[selectedEvent.direction]}</span>
            <span>{urgencyNames[selectedEvent.urgency]}</span>
            <span>{verificationNames[selectedEvent.verification_state]}</span>
            <span>{associationNames[selectedEvent.association_kind]}</span>
          </div>
          <strong>{selectedEvent.headline}</strong>
        </div>
        <div className="stock-event-detail-meta">
          <span>{formatTime(selectedEvent.occurred_at)}</span>
          <span>{selectedEvent.publisher}</span>
          <span>{selectedEvent.source_count} 个来源</span>
          <span>关联 {percent(selectedEvent.association_confidence)}</span>
          <span>AI {percent(selectedEvent.confidence)}</span>
        </div>
        <div className="stock-event-detail-tags">
          {selectedEvent.themes.length
            ? selectedEvent.themes.slice(0, 3).map((theme) => <em key={theme}>{theme}</em>)
            : <em>无题材标签</em>}
        </div>
        <a href={selectedEvent.source_url} target="_blank" rel="noreferrer">原始来源<ExternalLink size={13} /></a>
      </section>}
      <div className="stock-event-layout">
      <div className="stock-event-chart"><QuantChart option={option} ariaLabel={`${symbol} 事件日 K 线`} /></div>
      <aside className="stock-event-log" aria-label="事件记录">
        <header><div><b>事件记录</b><small>已落图 {chartEvents.length} / 全部 {data.events.length} 条已核验证据</small></div><CheckCircle2 size={16} /></header>
        {data.events.length === 0 ? <div className="stock-event-empty">当前 K 线区间没有已核验的个股新闻</div> : <div className="stock-event-items">{data.events.map((event) => {
          const selected = selectedEventId === event.event_id;
          const pinned = chartEventIds.has(event.event_id);
          return <article
            key={event.event_id}
            className={`stock-event-item direction-${event.direction}${selected ? " selected" : ""}`}
          >
            <button
              type="button"
              className="stock-event-select"
              aria-pressed={selected}
              onClick={() => setSelectedEventId(event.event_id)}
            >
              <span className="event-time">{formatTime(event.occurred_at)}</span>
              <span className="event-direction">{directionNames[event.direction]}</span>
              <strong>{event.headline}</strong>
              <span className="event-tags">{event.themes.length ? event.themes.slice(0, 3).map((theme) => <em key={theme}>{theme}</em>) : <em>无题材标签</em>}</span>
              <span className="event-meta"><i>{event.publisher}</i><i>关联 {percent(event.association_confidence)}</i><i>AI {percent(event.confidence)}</i></span>
              <span className={`event-pin-state ${pinned ? "mapped" : "unmapped"}`}>{pinned ? `已定位 ${event.mapped_trade_date}` : event.mapped_trade_date ? "已收录·点击后定位" : "非交易日·未落图"}</span>
            </button>
            <a href={event.source_url} target="_blank" rel="noreferrer">查看来源<ExternalLink size={12} /></a>
          </article>;
        })}</div>}
      </aside>
      </div>
    </>}
    {error && data && <div className="stock-timeline-stale"><AlertTriangle size={14} />更新失败，当前保留上次的本地快照</div>}
    <footer className="stock-event-kline-footer"><span>日线：本地历史库</span><span>事件：已核验个股新闻原始发布时间</span><span>批量热点采集时间不落图</span></footer>
  </section>;
}
