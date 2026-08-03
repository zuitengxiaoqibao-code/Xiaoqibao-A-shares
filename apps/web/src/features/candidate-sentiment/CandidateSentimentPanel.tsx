import {
  CircleDollarSign,
  Clock3,
  Flame,
  Lightbulb,
  Newspaper,
  ShieldAlert,
} from "lucide-react";

import type {
  CandidateSentimentBand,
  CandidateSentimentComponent,
  CandidateSentimentSnapshot,
} from "./types";


const bandNames: Record<CandidateSentimentBand, string> = {
  strongly_bearish: "显著偏空",
  cautious: "偏谨慎",
  neutral: "中性",
  positive: "偏积极",
  overheated: "情绪过热",
  unavailable: "暂不可评分",
};

const componentNames = {
  news: "新闻倾向",
  hotspot: "题材热度",
  fund_flow: "资金方向",
} as const;

function ComponentIcon({ name }: { name: CandidateSentimentComponent["name"] }) {
  if (name === "news") return <Newspaper size={16} />;
  if (name === "hotspot") return <Flame size={16} />;
  return <CircleDollarSign size={16} />;
}

function ComponentEvidence({ component }: { component: CandidateSentimentComponent }) {
  return (
    <section className={`candidate-sentiment-component ${component.status}`}>
      <header>
        <span><ComponentIcon name={component.name} />{componentNames[component.name]}</span>
        {component.score !== null
          ? <strong>{component.score}<small>分</small></strong>
          : <b>暂不可用</b>}
      </header>
      <p>{component.summary}</p>
      <div>
        <span>权重 {component.weight}%</span>
        <span>{component.observed_at
          ? `数据 ${new Date(component.observed_at).toLocaleString("zh-CN", { hour12: false })}`
          : "数据时间不可用"}</span>
      </div>
      <footer>
        <span>证据编号</span>
        {component.evidence_ids.length
          ? component.evidence_ids.map((id) => <code key={id}>{id}</code>)
          : <small>暂无可验证证据</small>}
      </footer>
    </section>
  );
}

export function CandidateSentimentPanel({
  sentiment,
}: {
  sentiment: CandidateSentimentSnapshot;
}) {
  const available = sentiment.score !== null;
  return (
    <section
      className={`candidate-sentiment-panel band-${sentiment.band}`}
      aria-label="个股情绪观察"
    >
      <header className="candidate-sentiment-panel-heading">
        <div>
          <p className="eyebrow">短线候选 / 独立观察</p>
          <h2>个股情绪观察</h2>
          <small>独立观察指标 · 不改变候选排序与行动结论</small>
        </div>
        <div className="candidate-sentiment-total">
          {available
            ? <strong>{sentiment.score}<small>分</small></strong>
            : <b>暂不可评分</b>}
          <span>{bandNames[sentiment.band]}</span>
          <small>覆盖率 {sentiment.coverage_percent}%{sentiment.quality === "partial" ? " · 部分可用" : ""}</small>
        </div>
      </header>

      <div className="candidate-sentiment-components">
        {sentiment.components.map((component) => (
          <ComponentEvidence component={component} key={component.name} />
        ))}
      </div>

      <div className="candidate-sentiment-guidance">
        <section><h3>主要原因</h3><p>{sentiment.primary_reason}</p></section>
        <section className="risk"><h3><ShieldAlert size={15} />主要风险</h3><p>{sentiment.primary_risk}</p></section>
        <section><h3><Lightbulb size={15} />新手提示</h3><p>{sentiment.beginner_guidance}</p></section>
      </div>

      <footer className="candidate-sentiment-panel-footer">
        <Clock3 size={14} />
        <span>数据时间 {new Date(sentiment.observed_at).toLocaleString("zh-CN", { hour12: false })}</span>
        <span>生成时间 {new Date(sentiment.generated_at).toLocaleString("zh-CN", { hour12: false })}</span>
        {sentiment.freshness === "stale" && <b>历史参考</b>}
      </footer>
    </section>
  );
}
