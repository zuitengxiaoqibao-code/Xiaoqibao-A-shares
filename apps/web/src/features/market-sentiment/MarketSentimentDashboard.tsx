import type { CSSProperties, ReactNode } from "react";
import { useEffect, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Clock3,
  Gauge,
  Info,
  RefreshCw,
  ShieldAlert,
  TrendingUp,
} from "lucide-react";

import type {
  MarketSentimentResponse,
  MarketSentimentSnapshot,
  SentimentBand,
  SentimentComponent,
  SentimentComponentName,
} from "./types";


type Props = {
  load: () => Promise<MarketSentimentResponse>;
  refresh?: () => Promise<MarketSentimentSnapshot>;
};

type State =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "ready"; response: MarketSentimentResponse };

type GaugeProperties = CSSProperties & { "--sentiment-score": string };

const bandNames: Record<SentimentBand, string> = {
  panic: "恐慌",
  cold: "低迷",
  neutral: "中性",
  active: "活跃",
  overheated: "过热",
  unavailable: "不可用",
};

const componentNames: Record<SentimentComponentName, string> = {
  volatility: "波动率情绪",
  activity: "成交活跃度",
  price_strength: "价格强度",
  risk_appetite: "风险偏好",
  breadth: "市场宽度",
  limit_ecology: "涨跌停情绪",
  money_making: "赚钱效应",
  sector_diffusion: "板块扩散情绪",
  style_risk_preference: "风格风险偏好",
  liquidity: "成交活跃度",
  hotspot: "热点持续度",
};

function numberValue(value: string | number | null | undefined): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function rounded(value: string | number | null | undefined): string {
  const parsed = numberValue(value);
  return parsed === null ? "--" : String(Math.round(parsed));
}

function formatTime(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function BandIcon({ band }: { band: SentimentBand }) {
  if (band === "active") return <Activity size={20} />;
  if (band === "neutral") return <Gauge size={20} />;
  if (band === "panic") return <ShieldAlert size={20} />;
  return <AlertTriangle size={20} />;
}

function metricSummary(component: SentimentComponent): string {
  const metric = component.metrics;
  if (component.name === "volatility" && metric.current_volatility_percent !== undefined) {
    return `近 20 日波动率 ${rounded(metric.current_volatility_percent)}% · 越低越稳定`;
  }
  if (component.name === "activity" && metric.relative_amount !== undefined) {
    const ratio = numberValue(metric.relative_amount);
    return ratio === null ? "20 日成交基线暂不可用" : `今日成交额为 20 日均值的 ${Math.round(ratio * 100)}%`;
  }
  if (component.name === "price_strength" && metric.new_high_252_count !== undefined) {
    return `252 日新高 ${metric.new_high_252_count} / 有效股票 ${metric.effective_count ?? "--"}`;
  }
  if (component.name === "risk_appetite" && metric.benchmark_return_20d_percent !== undefined) {
    return `沪深 300 ${rounded(metric.benchmark_return_20d_percent)}% · 国债 ETF ${rounded(metric.bond_etf_return_20d_percent)}%`;
  }
  if (component.name === "breadth" && metric.rising_count !== undefined) {
    return `上涨占比 ${metric.valid_count ? Math.round(Number(metric.rising_count) / Number(metric.valid_count) * 100) : "--"}% · MA20 / MA60 同步观察`;
  }
  if (component.name === "limit_ecology" && metric.limit_up_count !== undefined) {
    return `涨停 ${metric.limit_up_count} / 跌停 ${metric.limit_down_count ?? "--"} / 炸板 ${metric.broken_limit_up_count ?? "--"}`;
  }
  if (component.name === "money_making" && metric.five_day_rising_count !== undefined) {
    return `近 5 日上涨 ${metric.five_day_rising_count} · 60 日新低 ${metric.sixty_day_new_low_count ?? "--"}`;
  }
  if (component.name === "sector_diffusion" && metric.rising_industry_count !== undefined) {
    return `上涨行业 ${metric.rising_industry_count} / 有效行业 ${metric.effective_industry_count ?? "--"}`;
  }
  if (component.name === "style_risk_preference" && metric.small_cap_return_5d_percent !== undefined) {
    return `中证 1000 ${rounded(metric.small_cap_return_5d_percent)}% · 沪深 300 ${rounded(metric.large_cap_return_5d_percent)}%`;
  }
  if (component.name === "liquidity" && metric.relative_amount !== undefined) {
    const ratio = numberValue(metric.relative_amount);
    return ratio === null ? "同阶段成交基线暂不可用" : `同阶段成交基线的 ${Math.round(ratio * 100)}%`;
  }
  if (component.name === "hotspot" && metric.unique_theme_count !== undefined) {
    return `核验题材 ${metric.unique_theme_count} 个 / 延续 ${metric.persistent_theme_count ?? 0} 个`;
  }
  return "该分项暂不可用";
}

function InsightSection({
  icon,
  title,
  items,
  fallback,
}: {
  icon: ReactNode;
  title: string;
  items: string[];
  fallback: string;
}) {
  return <section className="sentiment-insight">
    <h3>{icon}{title}</h3>
    {items.length
      ? <ul>{items.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul>
      : <p>{fallback}</p>}
  </section>;
}

function SentimentContent({
  response,
  refreshing,
  refreshError,
  onRefresh,
  canRefresh,
}: {
  response: MarketSentimentResponse;
  refreshing: boolean;
  refreshError: string | null;
  onRefresh: () => void;
  canRefresh: boolean;
}) {
  const item = response.current ?? response.previous_close;
  const unavailable = !item || item.score === null || item.band === "unavailable";
  const score = item ? numberValue(item.score) : null;
  const scoreLabel = score === null ? null : Math.round(score);
  const phaseLabel = response.display_mode === "previous_close_baseline"
    ? "昨收基线"
    : response.phase === "postclose" ? "盘后定稿" : "盘中观测";
  const band = item?.band ?? "unavailable";
  const gaugeStyle: GaugeProperties = {
    "--sentiment-score": `${score ?? 0}%`,
  };
  const quality = item?.quality === "partial"
    ? `覆盖率 ${rounded(item.coverage_percent)}% · 部分可用`
    : item?.quality === "ready"
      ? `覆盖率 ${rounded(item.coverage_percent)}% · 数据完整`
      : `覆盖率 ${rounded(item?.coverage_percent)}% · 暂不可评分`;

  const guidanceTitle = band === "neutral" ? "等待条件" : "新手观察建议";
  const blocks = {
    drivers: <InsightSection
      key="drivers"
      icon={<TrendingUp size={16} />}
      title="为什么是这个分数"
      items={item?.drivers ?? []}
      fallback="当前没有已冻结的正向驱动。"
    />,
    risks: <InsightSection
      key="risks"
      icon={<ShieldAlert size={16} />}
      title="主要风险"
      items={item?.risks ?? []}
      fallback="当前快照没有新增风险描述。"
    />,
    guidance: <InsightSection
      key="guidance"
      icon={<Info size={16} />}
      title={guidanceTitle}
      items={item ? [item.beginner_guidance] : []}
      fallback="等待核心行情来源恢复后再判断。"
    />,
  };
  const order = band === "active"
    ? [blocks.drivers, blocks.risks, blocks.guidance]
    : band === "neutral"
      ? [blocks.guidance, blocks.risks, blocks.drivers]
      : [blocks.risks, blocks.guidance, blocks.drivers];
  const trajectory = [response.previous_close, ...response.trajectory]
    .filter((entry): entry is MarketSentimentSnapshot => Boolean(entry))
    .filter((entry, index, values) => (
      values.findIndex((candidate) => candidate.snapshot_id === entry.snapshot_id) === index
    ));

  return <>
    <header className="sentiment-heading">
      <div>
        <span className="sentiment-kicker"><Activity size={15} />A 股市场温度</span>
        <h2>市场情绪仪表盘</h2>
        <p>用九个可追溯因子判断市场温度：波动、成交、价格、风险、广度、涨跌停、赚钱效应、板块扩散和风格。</p>
      </div>
      {canRefresh && <button
        type="button"
        className="sentiment-refresh"
        aria-label="刷新市场情绪"
        title="刷新市场情绪"
        disabled={refreshing || response.phase === "premarket"}
        onClick={onRefresh}
      >
        <RefreshCw className={refreshing ? "spin" : ""} size={17} />
      </button>}
    </header>

    <div className="sentiment-status-line">
      <span>{phaseLabel}</span>
      <span>{quality}</span>
      {item?.freshness === "stale" && <strong>历史参考 · 不是当前结果</strong>}
      {item && <time dateTime={item.observed_at}>数据截至 {formatTime(item.observed_at)}</time>}
    </div>
    {response.phase === "premarket" && <p className="sentiment-premarket-note">
      盘前不生成虚假实时分数，当前仅展示上一交易日盘后定稿。
    </p>}
    {refreshError && <p className="sentiment-refresh-error" role="status">{refreshError}</p>}

    <div className={`sentiment-core sentiment-band-${band}`}>
      <div className="sentiment-score-zone">
        <div
          className={`sentiment-gauge ${unavailable ? "is-unavailable" : ""}`}
          style={gaugeStyle}
          role="img"
          aria-label={unavailable
            ? "A 股市场情绪暂不可用"
            : `A 股市场情绪 ${scoreLabel} 分，${bandNames[band]}`}
        >
          <div className="sentiment-gauge-inner">
            {unavailable
              ? <><AlertTriangle size={24} /><span>暂不可用</span></>
              : <><strong className="sentiment-score-value">{scoreLabel}</strong><span>/ 100</span></>}
          </div>
        </div>
        <div className="sentiment-band-label">
          <BandIcon band={band} />
          <span><b>{bandNames[band]}</b><small>{unavailable ? "核心数据不足" : phaseLabel}</small></span>
        </div>
      </div>

      <div className="sentiment-components" aria-label="情绪分项">
        {(item?.components ?? []).map((component) => {
          const componentScore = numberValue(component.score);
          const componentStyle: GaugeProperties = {
            "--sentiment-score": `${componentScore ?? 0}%`,
          };
          return <div className="sentiment-component" key={component.name}>
            <div className="sentiment-component-heading">
              <span>{componentNames[component.name]} <small>权重 {rounded(component.weight)}%</small></span>
              <b>{componentScore === null ? "--" : Math.round(componentScore)}</b>
            </div>
            <div className="sentiment-track" style={componentStyle} aria-hidden="true"><i /></div>
            <p>{metricSummary(component)}</p>
          </div>;
        })}
        {item && item.components.length === 0 && <p className="sentiment-components-empty">
          分项明细尚未生成。
        </p>}
      </div>
    </div>

    <div className="sentiment-insights">{order}</div>

    <div className="sentiment-trajectory" aria-label="情绪阶段轨迹">
      <h3><Clock3 size={16} />阶段轨迹</h3>
      <div>
        {trajectory.length > 0 ? trajectory.map((entry) => <span key={entry.snapshot_id}>
          <i />
          <small>{entry.trading_date !== response.trading_date ? "昨收" : entry.phase === "postclose" ? "盘后" : "盘中"}</small>
          <b>{entry.score === null ? "--" : rounded(entry.score)}</b>
          <time dateTime={entry.observed_at}>{formatTime(entry.observed_at)}</time>
        </span>) : <p>当日还没有可验证轨迹。</p>}
      </div>
    </div>

    <details className="sentiment-method">
      <summary><Info size={15} />这个分数怎么来的</summary>
      <p>九因子合成：波动率情绪 15%、成交活跃度 15%、价格强度 10%、风险偏好 10%、市场广度 15%、涨跌停情绪 15%、赚钱效应 10%、板块扩散情绪 5%、风格风险偏好 5%。覆盖率不足 70% 时不打分，高分也不代表低风险。</p>
    </details>
  </>;
}

export function MarketSentimentDashboard({ load, refresh }: Props) {
  const [state, setState] = useState<State>({ kind: "loading" });
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    load()
      .then((response) => { if (active) setState({ kind: "ready", response }); })
      .catch(() => { if (active) setState({ kind: "error", message: "市场情绪暂不可用，请稍后重试。" }); });
    return () => { active = false; };
  }, [load]);

  async function handleRefresh() {
    if (!refresh) return;
    setRefreshing(true);
    setRefreshError(null);
    try {
      await refresh();
      setState({ kind: "ready", response: await load() });
    } catch {
      setRefreshError("刷新失败，已保留最近一次可验证结果。");
    } finally {
      setRefreshing(false);
    }
  }

  return <section className="market-sentiment-dashboard" role="region" aria-label="A 股市场情绪">
    {state.kind === "loading" && <div className="sentiment-loading" role="status" aria-busy="true">
      <Activity size={20} /><span>正在读取市场情绪</span>
    </div>}
    {state.kind === "error" && <div className="sentiment-load-error" role="status">
      <AlertTriangle size={20} /><div><b>市场情绪暂不可用</b><p>{state.message}</p></div>
    </div>}
    {state.kind === "ready" && <SentimentContent
      response={state.response}
      refreshing={refreshing}
      refreshError={refreshError}
      onRefresh={() => void handleRefresh()}
      canRefresh={Boolean(refresh)}
    />}
  </section>;
}
