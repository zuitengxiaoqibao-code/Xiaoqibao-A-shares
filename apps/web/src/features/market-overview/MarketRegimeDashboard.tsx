import { Activity, Ban, CheckCircle2, Database, Flame, Repeat2, ShieldAlert } from "lucide-react";

import type { OverviewRegimeAssessment, OverviewRegimeMetrics } from "./types";

const factorRows: Array<{
  key: keyof OverviewRegimeMetrics;
  label: string;
  formula: string;
  format: "percent" | "ratio";
}> = [
  { key: "up_ratio", label: "上涨率", formula: "A 股上涨家数 / A 股有效家数", format: "percent" },
  { key: "zt_ratio", label: "涨停率", formula: "A 股当前涨停家数 / A 股有效家数", format: "percent" },
  { key: "dt_ratio", label: "跌停率", formula: "A 股当前跌停家数 / A 股有效家数", format: "percent" },
  { key: "median_ret", label: "中位涨幅", formula: "A 股涨跌幅横截面中位数", format: "percent" },
  { key: "amt_heat", label: "成交热度", formula: "当前成交额 / 同时点20日基准成交额", format: "ratio" },
  { key: "strong_close_ratio", label: "强收比例", formula: "ClosePos >= 75 的股票占比", format: "percent" },
  { key: "weak_close_ratio", label: "弱收比例", formula: "ClosePos <= 25 的股票占比", format: "percent" },
  { key: "limit_fail_ratio", label: "实时触板弱收率", formula: "触板后现价低于涨停价97%的股票 / 触板股票", format: "percent" },
  { key: "panic_ratio", label: "恐慌率", formula: "日内最低涨幅 <= -8%的股票占比", format: "percent" },
  { key: "amp_ratio", label: "高波动率", formula: "日内振幅 >= 10%的股票占比", format: "percent" },
  { key: "net_positive_ratio", label: "资金净流入率", formula: "真实净流入额 > 0 的股票占比", format: "percent" },
];

function valueLabel(value: string | null, format: "percent" | "ratio"): string {
  if (value === null) return "暂无可信数据";
  const number = Number(value);
  if (!Number.isFinite(number)) return "不可用";
  return format === "ratio" ? `${number.toFixed(2)}x` : `${number.toFixed(2)}%`;
}

function scoreTone(value: string | null, risk = false): string {
  const number = Number(value);
  if (!Number.isFinite(number)) return "neutral";
  if (risk) return number >= 65 ? "danger" : number >= 45 ? "warning" : "safe";
  return number >= 70 ? "safe" : number >= 45 ? "warning" : "danger";
}

function numericText(value: string | null, digits = 1): string {
  if (value === null) return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "--";
}

export function MarketRegimeDashboard({ metrics, regime }: {
  metrics: OverviewRegimeMetrics;
  regime: OverviewRegimeAssessment;
}) {
  const scores = [
    ["情绪分", regime.emotion_score, false, Activity],
    ["风险分", regime.risk_score, true, ShieldAlert],
    ["热度分", regime.heat_score, false, Flame],
    ["轮动分", regime.rotation_score, false, Repeat2],
  ] as const;
  return <section className="regime-dashboard" aria-label="A 股市场风格识别工作台">
    <header className="regime-hero">
      <div><span>A-SHARE REGIME ENGINE</span><h2>{regime.regime ? `${regime.regime}${regime.rule_matched ? "" : "（低置信近似）"}` : "风格待确认"}</h2><p>{regime.reasons.join("；") || "等待 A 股全市场有效行情"}</p></div>
      <div><small>建议市场系数</small><strong>{numericText(regime.market_coef)}</strong><b>{regime.coverage_percent === null ? "--" : `${regime.coverage_percent}%`} 因子权重可用</b></div>
    </header>

    <div className="regime-scores">
      {scores.map(([label, value, risk, Icon]) => <article key={label} className={scoreTone(value, risk)} data-state={value === null || !Number.isFinite(Number(value)) ? "unavailable" : "ready"}>
        <Icon size={17} /><span><small>{label}</small><b>{value === null ? "--" : Number(value).toFixed(2)}</b></span>
        <i><em style={{ width: `${Math.max(0, Math.min(100, Number(value) || 0))}%` }} /></i>
      </article>)}
    </div>

    <div className="regime-body">
      <section className="regime-factor-table" aria-label="市场风格原始因子">
        <header><b>A 股全市场实时因子</b><span>本地通达信 A 股横截面 · 不使用随机值</span></header>
        <table><thead><tr><th>因子</th><th>当前值</th><th>严格口径</th><th>状态</th></tr></thead>
          <tbody>{factorRows.map((row) => {
            const value = metrics[row.key] as string | null;
            return <tr key={row.key}><td>{row.label}</td><td>{valueLabel(value, row.format)}</td><td>{row.formula}</td><td className={value === null ? "missing" : "verified"}>{value === null ? "缺少专有数据源" : "已验证"}</td></tr>;
          })}</tbody>
        </table>
      </section>

      <aside className="regime-strategy-route" aria-label="风格策略路由">
        <header><b>策略模型路由</b><span>{regime.formula_version}</span></header>
        <section><CheckCircle2 size={16} /><div><b>当前适用</b>{regime.suitable_strategies.map((item) => <span key={item}>{item}</span>)}</div></section>
        <section><Ban size={16} /><div><b>当前禁用</b>{regime.avoid_strategies.map((item) => <span key={item}>{item}</span>)}</div></section>
        <section><Database size={16} /><div><b>证据边界</b><p>{regime.missing_factors.length ? `缺失：${regime.missing_factors.join("、")}。综合分按已有权重归一化，质量标记为部分可用。` : "本次公式所需因子完整。"}</p></div></section>
      </aside>
    </div>

    <footer className="regime-flow"><span>1 市场风格</span><i>→</i><span>2 策略模型</span><i>→</i><span>3 盘后候选</span><i>→</i><span>4 次日触发</span><i>→</i><span>5 风险退出</span></footer>
  </section>;
}
