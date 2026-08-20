import { ArrowDownRight, ArrowUpRight, BookOpen, Scale, ShieldAlert } from "lucide-react";
import { useMemo, useState } from "react";

import type { Interpretation, NewsEvent } from "./types";

export type NewsCategory = "all" | "policy" | "announcement" | "industry" | "capital" | "macro" | "risk" | "other";

const categoryLabels: Record<NewsCategory, string> = {
  all: "全部",
  policy: "政策监管",
  announcement: "公司公告",
  industry: "产业题材",
  capital: "资金交易",
  macro: "宏观流动性",
  risk: "风险事件",
  other: "其他已核验",
};

const eventTypeLabels: Record<string, string> = {
  market_hotspot: "题材热点",
  industrial_policy: "产业政策",
  company_announcement: "公司公告",
  regulatory_notice: "监管信息",
  capital_flow: "资金动向",
  macro_event: "宏观事件",
  risk_event: "风险事件",
};

const directionLabels = { positive: "偏正面", negative: "偏负面", neutral: "中性", uncertain: "方向待核验" };
const percent = (value: string) => `${(Number(value) * 100).toFixed(0)}%`;

export function newsCategory(event: NewsEvent): NewsCategory {
  const text = `${event.event_type} ${event.headline} ${event.industries.join(" ")} ${event.themes.join(" ")}`.toLowerCase();
  if (/(risk|风险|立案|处罚|退市|减持|违约|诉讼|爆雷)/.test(text)) return "risk";
  if (/(announcement|公告|业绩|回购|增持|中报|年报|季报)/.test(text)) return "announcement";
  if (/(policy|regulat|政策|监管|国务院|证监会|发改委|财政部)/.test(text)) return "policy";
  if (/(capital|fund|资金|龙虎榜|主力|北向|融资|成交)/.test(text)) return "capital";
  if (/(macro|宏观|流动性|利率|汇率|央行|社融|cpi|pmi)/.test(text)) return "macro";
  if (/(hotspot|industry|题材|产业|概念|板块)/.test(text) || event.industries.length > 0 || event.themes.length > 0) return "industry";
  return "other";
}

function DirectionIcon({ direction }: { direction: Interpretation["impact_direction"] }) {
  if (direction === "positive") return <ArrowUpRight size={17} />;
  if (direction === "negative") return <ArrowDownRight size={17} />;
  return <Scale size={16} />;
}

export function NewsEventGrid({ events, interpretationByEvent, onSelect }: {
  events: NewsEvent[];
  interpretationByEvent: Map<string, Interpretation>;
  onSelect: (event: NewsEvent) => void;
}) {
  const [category, setCategory] = useState<NewsCategory>("all");
  const categorized = useMemo(() => events.map((event) => ({ event, category: newsCategory(event) })), [events]);
  const counts = useMemo(() => categorized.reduce<Record<NewsCategory, number>>((result, item) => {
    result[item.category] += 1;
    result.all += 1;
    return result;
  }, { all: 0, policy: 0, announcement: 0, industry: 0, capital: 0, macro: 0, risk: 0, other: 0 }), [categorized]);
  const filtered = categorized.filter((item) => category === "all" || item.category === category).sort((a, b) => b.event.occurred_at.localeCompare(a.event.occurred_at));

  return <section className="news-flow-workspace">
    <div className="news-category-filter" aria-label="新闻分类">
      {(Object.keys(categoryLabels) as NewsCategory[]).map((key) => <button key={key} type="button" aria-pressed={category === key} onClick={() => setCategory(key)} disabled={key !== "all" && counts[key] === 0}>
        <span>{categoryLabels[key]}</span><b>{counts[key]}</b>
      </button>)}
    </div>
    {filtered.length === 0 ? <div className="news-empty"><b>该分类暂无已归档事件</b></div> : <div className="news-card-grid" role="region" aria-label="新闻卡片流">
      {filtered.map(({ event, category: eventCategory }) => {
        const interpretation = interpretationByEvent.get(event.event_id);
        const direction = interpretation?.impact_direction ?? "uncertain";
        const uncertain = !interpretation || interpretation.degraded || direction === "uncertain" || Number(interpretation.confidence) < .6;
        const source = event.citations[0];
        const statements = interpretation?.statements.slice(0, 2) ?? [];
        return <article className="news-event-card" data-direction={direction} data-category={eventCategory} key={event.event_id}>
          <header>
            <div className="news-event-card__badges"><span>{categoryLabels[eventCategory]}</span><span className={event.review_state}>{event.review_state === "verified" ? "已复核" : "待复核"}</span></div>
            <div className={`news-event-card__direction ${direction}`}><DirectionIcon direction={direction}/><span>{directionLabels[direction]}</span><b>{percent(interpretation?.confidence ?? "0")}</b></div>
          </header>
          <p className="news-event-card__type">{eventTypeLabels[event.event_type] ?? "已归档事件"} · {event.review_state === "verified" ? "已复核" : "待复核"}</p>
          <h2>{event.headline}</h2>
          <div className="news-event-card__tags">
            {event.affected_instruments.map(([asset, code]) => <span className="instrument" key={`${asset}-${code}`}>{asset === "a_share" ? "A股" : "转债"} {code}</span>)}
            {event.industries.map((item) => <span key={`industry-${item}`}>{item}</span>)}
            {event.themes.map((item) => <span key={`theme-${item}`}>{item}</span>)}
            {event.affected_instruments.length === 0 && event.industries.length === 0 && event.themes.length === 0 && <span>全市场</span>}
          </div>
          {statements.length > 0 && <div className="news-event-card__summary">{statements.map((statement) => <p key={statement.statement_id}><b>{statement.kind === "fact" ? "已核验事实" : "模型解释"}</b><span>{statement.text}</span></p>)}</div>}
          {uncertain && <div className="news-event-card__uncertain"><ShieldAlert size={15}/><div><b>不确定性较高</b><span>{interpretation?.degraded ? "解释已降级" : "关联或方向仍需复核"}</span></div></div>}
          <footer>
            <button type="button" onClick={() => onSelect(event)}><BookOpen size={14}/>查看 {event.citations.length} 条证据</button>
            <span>{`事件发生 ${new Date(event.occurred_at).toLocaleString("zh-CN", { hour12: false })}`}</span>
            <span>{source ? `${event.event_type === "market_hotspot" ? "同花顺热点" : source.publisher} · 来源时间 ${new Date(source.published_at).toLocaleString("zh-CN", { hour12: false })}` : "来源待补齐"}</span>
          </footer>
        </article>;
      })}
    </div>}
  </section>;
}
