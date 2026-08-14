import { Building2, CircleDot, Factory, Network, Tags } from "lucide-react";
import { useMemo } from "react";

import type { Interpretation, NewsEvent, UnifiedDecisionEvent, UnifiedEventCategory } from "./types";

type DirectionState = "positive" | "negative" | "pending";

const directionLabels: Record<DirectionState, string> = {
  positive: "正向证据",
  negative: "负向证据",
  pending: "方向待核验",
};
const categoryLabels: Record<UnifiedEventCategory, string> = {
  policy_macro: "政策宏观", industry_sector: "行业板块", company_announcement: "公司公告",
  earnings_financial: "业绩财务", capital_dragon_tiger: "资金龙虎榜", price_volume_anomaly: "价格成交异动",
  risk_event: "风险事件", rumor_unverified: "传闻待核验",
};

function verifiedDirection(event: NewsEvent, interpretation?: Interpretation): DirectionState {
  if (
    event.review_state === "verified"
    && interpretation
    && !interpretation.degraded
    && Number(interpretation.confidence) >= 0.7
    && (interpretation.impact_direction === "positive" || interpretation.impact_direction === "negative")
  ) return interpretation.impact_direction;
  return "pending";
}

function hasVerifiedAssociations(event: NewsEvent) {
  const verified = event.review_state === "verified"
    && Number(event.association_confidence) >= 0.7
    && Boolean(event.association_kind);
  if (!verified || event.association_kind === "macro") return verified;
  const hasRelationship = event.affected_instruments.length > 0 || event.industries.length > 0 || event.themes.length > 0;
  return hasRelationship && Boolean(event.association_reasons?.some((reason) => reason.trim()));
}

export function NewsEventGraph({ events, interpretations, unifiedEvents = [], onSelect }: {
  events: NewsEvent[];
  interpretations: Interpretation[];
  unifiedEvents?: UnifiedDecisionEvent[];
  onSelect: (event: NewsEvent) => void;
}) {
  const uniqueEvents = useMemo(() => {
    const seen = new Map<string, NewsEvent>();
    for (const event of events) if (!seen.has(event.event_id)) seen.set(event.event_id, event);
    return [...seen.values()];
  }, [events]);
  const interpretationByEvent = useMemo(() => new Map(interpretations.map((item) => [item.event_id, item])), [interpretations]);
  const unifiedByEvent = useMemo(() => new Map(unifiedEvents.map((item) => [item.event_id, item])), [unifiedEvents]);

  return <section className="news-event-graph" role="region" aria-label="新闻事件关系图">
    <header className="news-event-graph__header">
      <div><Network size={17}/><h2>事件关系</h2></div>
      <span>{uniqueEvents.length} 个去重事件 · 颜色表示事件归属，不表示涨跌</span>
    </header>
    <div className="news-event-graph__list">
      {uniqueEvents.map((event) => {
        const direction = verifiedDirection(event, interpretationByEvent.get(event.event_id));
        const publishers = new Set(event.citations.map((citation) => citation.publisher.trim()).filter(Boolean));
        const verifiedAssociations = hasVerifiedAssociations(event);
        const unified = unifiedByEvent.get(event.event_id);
        return <button
          className="news-event-graph__event"
          data-direction={direction}
          data-event-id={event.event_id}
          data-category={unified?.category}
          key={event.event_id}
          onClick={() => onSelect(event)}
          type="button"
        >
          <span className="news-event-graph__event-copy">
            <span className="news-event-graph__meta">
              <span>{directionLabels[direction]}</span>
              {unified && <span className="event-category">{categoryLabels[unified.category]}</span>}
              <span>{publishers.size > 0 ? `${publishers.size} 个来源` : "来源待补齐"}</span>
            </span>
            <strong>{event.headline}</strong>
          </span>
          <span className="news-event-graph__links" aria-label="已核验关联">
            {verifiedAssociations ? <>
              {event.affected_instruments.map(([asset, code]) => <span className="stock" key={`${asset}-${code}`}><Building2 size={13}/>{code}</span>)}
              {event.industries.map((industry) => <span key={`industry-${industry}`}><Factory size={13}/>{industry}</span>)}
              {event.themes.map((theme) => <span key={`theme-${theme}`}><Tags size={13}/>{theme}</span>)}
              {event.affected_instruments.length === 0 && event.industries.length === 0 && event.themes.length === 0 && <span><CircleDot size={13}/>全市场</span>}
            </> : <span className="pending"><CircleDot size={13}/>关联待核验</span>}
          </span>
          {unified?.follow_up_indicators[0] && <small className="news-event-graph__follow-up">后续：{unified.follow_up_indicators[0]}</small>}
        </button>;
      })}
    </div>
  </section>;
}
