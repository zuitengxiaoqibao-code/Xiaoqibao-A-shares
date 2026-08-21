from __future__ import annotations

from qibao_api.contracts.quant_research import OpportunityDefinition


class OpportunityRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, OpportunityDefinition] = {}

    def register(self, definition: OpportunityDefinition) -> None:
        if definition.opportunity_id in self._definitions:
            raise ValueError(
                f"opportunity id already registered: {definition.opportunity_id}"
            )
        self._definitions[definition.opportunity_id] = definition

    def definitions(self) -> tuple[OpportunityDefinition, ...]:
        return tuple(
            self._definitions[item] for item in sorted(self._definitions)
        )


def build_default_opportunity_registry() -> OpportunityRegistry:
    registry = OpportunityRegistry()
    for definition in _DEFAULT_DEFINITIONS:
        registry.register(definition)
    return registry


_DEFAULT_DEFINITIONS = (
    OpportunityDefinition(
        opportunity_id="trend_continuation",
        name="趋势延续",
        applicable_regimes=("情绪主升", "指数权重进攻"),
        required_evidence=("20日趋势", "量价确认", "流动性"),
        score_components=("trend", "momentum", "liquidity"),
        trigger_rules=("回踩关键均线后重新转强",),
        invalidation_rules=("收盘有效跌破20日均线",),
        unavailable_when=("历史日线不足60日",),
    ),
    OpportunityDefinition(
        opportunity_id="volume_breakout",
        name="放量突破",
        applicable_regimes=("情绪主升", "轮动震荡"),
        required_evidence=("前高位置", "成交量", "收盘位置"),
        score_components=("breakout", "volume_price", "close_position"),
        trigger_rules=("放量突破前高且不回落至突破位下方",),
        invalidation_rules=("突破后放量跌回前高下方",),
        unavailable_when=("缺少前高窗口或成交量",),
    ),
    OpportunityDefinition(
        opportunity_id="oversold_recovery",
        name="超跌修复",
        applicable_regimes=("冰点修复", "高位退潮"),
        required_evidence=("60日回撤", "低点修复", "市场风险"),
        score_components=("drawdown", "recovery", "regime_match"),
        trigger_rules=("低点修复并重新站上盘中均价",),
        invalidation_rules=("再次跌破修复低点",),
        unavailable_when=("缺少60日回撤或盘中触发证据",),
    ),
    OpportunityDefinition(
        opportunity_id="quality_improvement",
        name="质量改善",
        applicable_regimes=("指数权重进攻", "轮动震荡"),
        required_evidence=("营收质量", "利润率", "经营现金流"),
        score_components=("quality", "cash_flow", "margin"),
        trigger_rules=("最新财报确认质量指标同比改善",),
        invalidation_rules=("经营现金流与利润再次背离",),
        unavailable_when=("财务证据字段不完整",),
    ),
    OpportunityDefinition(
        opportunity_id="valuation_recovery",
        name="估值修复",
        applicable_regimes=("指数权重进攻", "冰点修复"),
        required_evidence=("当前估值", "历史分位", "盈利证据"),
        score_components=("valuation", "earnings", "regime_match"),
        trigger_rules=("估值处于低分位且盈利预期未恶化",),
        invalidation_rules=("盈利预期下修抵消估值折价",),
        unavailable_when=("缺少可比估值或盈利证据",),
    ),
    OpportunityDefinition(
        opportunity_id="event_driven",
        name="事件驱动",
        applicable_regimes=("情绪主升", "轮动震荡", "冰点修复"),
        required_evidence=("已核验事件", "股票关联", "事件时效"),
        score_components=("event_relevance", "freshness", "market_response"),
        trigger_rules=("已核验事件与量价反应方向一致",),
        invalidation_rules=("事件被否认或价格反应完全逆转",),
        unavailable_when=("没有已核验且可关联的事件",),
    ),
    OpportunityDefinition(
        opportunity_id="defensive_low_volatility",
        name="防守低波",
        applicable_regimes=("高位退潮", "缩量混沌"),
        required_evidence=("20日波动", "60日回撤", "流动性"),
        score_components=("volatility", "drawdown", "liquidity"),
        trigger_rules=("市场风险高企且个股波动与回撤受控",),
        invalidation_rules=("波动率和回撤同步突破防守阈值",),
        unavailable_when=("缺少20日波动或60日回撤",),
    ),
)
