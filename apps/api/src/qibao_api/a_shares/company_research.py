import asyncio
import hashlib
from collections.abc import Callable
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from qibao_api.a_shares.diagnosis import AShareDiagnosis
from qibao_api.contracts.company_research import (
    CompanyProfileEvidence,
    CompanyResearchDimension,
    CompanyResearchResponse,
    CounterCaseItem,
    FinancialHistory,
    ResearchSourceEvidence,
    ValuationObservation,
)


DIMENSION_WEIGHTS = {
    "industry_space": 10,
    "business_model": 10,
    "growth": 15,
    "profitability": 10,
    "cash_flow": 15,
    "balance_sheet": 10,
    "moat": 10,
    "valuation": 15,
    "catalysts": 5,
}


def summarize_latest_tips(items: tuple[Any, ...]) -> str:
    if not items:
        return "无可核验催化证据"
    positive = sum(1 for item in items if item.tone == "positive")
    risk = sum(1 for item in items if item.tone == "risk")
    neutral = len(items) - positive - risk
    return f"已识别 {len(items)} 项事件：催化 {positive} · 中性 {neutral} · 风险 {risk}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _average(values: list[Decimal]) -> Decimal | None:
    return sum(values, Decimal("0")) / Decimal(len(values)) if values else None


def _score_by_thresholds(value: Decimal, thresholds: tuple[tuple[Decimal, Decimal], ...]) -> Decimal:
    for threshold, score in thresholds:
        if value >= threshold:
            return score
    return thresholds[-1][1]


def _observed(value: datetime | date | None) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, date):
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    return None


def _financial_unavailable(reason: str) -> FinancialHistory:
    return FinancialHistory(
        status="unavailable", periods=(), annual_periods=(), latest_period=None,
        revenue_cagr_3y=None, net_profit_cagr_3y=None, source="sina-finance",
        observed_at=None, reasons=(reason,),
    )


def _profile_unavailable(reason: str) -> CompanyProfileEvidence:
    return CompanyProfileEvidence(
        status="unavailable", company_overview=None, industry_analysis=None,
        latest_tips=None, source="mootdx-f10", observed_at=None,
        reasons=(reason,),
    )


def _evidence_id(source: str, label: str) -> str:
    digest = hashlib.sha256(f"{source}:{label}".encode("utf-8")).hexdigest()[:16]
    return f"{source}:{digest}"


class CompanyResearchService:
    def __init__(
        self,
        diagnosis_service: Any,
        financial_source: Any,
        profile_source: Any,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.diagnosis_service = diagnosis_service
        self.financial_source = financial_source
        self.profile_source = profile_source
        self.clock = clock

    async def get(self, symbol: str, as_of: date | None = None) -> CompanyResearchResponse:
        selected_date = as_of or self.clock().date()
        diagnosis_result, financial_result, profile_result = await asyncio.gather(
            self.diagnosis_service.diagnose(symbol, selected_date),
            asyncio.to_thread(self.financial_source.fetch, symbol),
            asyncio.to_thread(self.profile_source.fetch, symbol),
            return_exceptions=True,
        )
        if isinstance(diagnosis_result, Exception):
            raise diagnosis_result
        diagnosis: AShareDiagnosis = diagnosis_result
        history = (
            _financial_unavailable(f"新浪财务历史不可用：{financial_result}")
            if isinstance(financial_result, Exception) else financial_result
        )
        profile = (
            _profile_unavailable(f"通达信F10不可用：{profile_result}")
            if isinstance(profile_result, Exception) else profile_result
        )
        dimensions = self._dimensions(diagnosis, history, profile)
        coverage_weight = sum(item.weight for item in dimensions if item.status == "ready")
        coverage = Decimal(coverage_weight) / Decimal("100")
        scored = [item for item in dimensions if item.status == "ready" and item.score is not None]
        base_score = (
            sum((item.score * Decimal(item.weight) for item in scored), Decimal("0"))
            / Decimal(sum(item.weight for item in scored))
            if scored else None
        )
        counter_case = self._counter_case(diagnosis, history, coverage)
        risk_penalty = min(
            Decimal("25"),
            sum((item.penalty for item in counter_case if item.status == "triggered"), Decimal("0")),
        )
        base_score = base_score.quantize(Decimal("0.01")) if base_score is not None else None
        final_score = (
            max(Decimal("0"), base_score - risk_penalty).quantize(Decimal("0.01"))
            if base_score is not None and coverage >= Decimal("0.60") else None
        )
        market_metrics = diagnosis.sections["market"].metrics
        valuation_section = diagnosis.sections["valuation"]
        valuation_metrics = valuation_section.metrics
        valuation = ValuationObservation(
            status=valuation_section.status,
            pe_ttm=_decimal(valuation_metrics.get("pe_ttm")),
            pb=_decimal(valuation_metrics.get("pb")),
            market_cap_yi=_decimal(valuation_metrics.get("market_cap_yi")),
            observation_range_status="unavailable",
            observation_range_reason="缺少历史估值序列和可靠前向盈利预测，暂不计算价格区间。",
            source=valuation_section.source,
            observed_at=_observed(valuation_section.observed_at),
        )
        reasons = (*history.reasons, *profile.reasons)
        status = "ready" if coverage >= Decimal("0.60") and not reasons else "partial"
        return CompanyResearchResponse(
            status=status,
            symbol=symbol,
            name=str(market_metrics.get("name") or symbol),
            as_of=selected_date,
            generated_at=self.clock(),
            dimensions=dimensions,
            evidence_coverage=coverage,
            base_score=base_score,
            risk_penalty=risk_penalty,
            final_score=final_score,
            financial_history=history,
            valuation=valuation,
            counter_case=counter_case,
            profile=profile,
            sources=self._sources(diagnosis, history, profile),
            reasons=tuple(reasons),
        )

    def _dimensions(
        self,
        diagnosis: AShareDiagnosis,
        history: FinancialHistory,
        profile: CompanyProfileEvidence,
    ) -> tuple[CompanyResearchDimension, ...]:
        latest = history.latest_period
        fundamentals = diagnosis.sections["fundamentals"]
        valuation = diagnosis.sections["valuation"]
        profile_ids = ((_evidence_id(profile.source, "profile"),) if profile.observed_at else ())
        financial_ids = tuple(
            _evidence_id(history.source, item.period.isoformat()) for item in history.annual_periods
        )

        growth_values: list[Decimal] = []
        for value in (history.revenue_cagr_3y, history.net_profit_cagr_3y):
            if value is not None:
                growth_values.append(_score_by_thresholds(value, (
                    (Decimal("0.30"), Decimal("95")),
                    (Decimal("0.15"), Decimal("80")),
                    (Decimal("0.05"), Decimal("65")),
                    (Decimal("0"), Decimal("50")),
                    (Decimal("-999"), Decimal("20")),
                )))
        growth_score = _average(growth_values)

        profitability_values: list[Decimal] = []
        roe = _decimal(fundamentals.metrics.get("roe"))
        if roe is not None:
            profitability_values.append(_score_by_thresholds(roe, (
                (Decimal("20"), Decimal("90")),
                (Decimal("12"), Decimal("75")),
                (Decimal("6"), Decimal("55")),
                (Decimal("0"), Decimal("35")),
                (Decimal("-999"), Decimal("10")),
            )))
        if latest is not None and latest.gross_margin is not None:
            profitability_values.append(_score_by_thresholds(latest.gross_margin, (
                (Decimal("0.40"), Decimal("85")),
                (Decimal("0.20"), Decimal("65")),
                (Decimal("0"), Decimal("45")),
                (Decimal("-999"), Decimal("10")),
            )))
        profitability_score = _average(profitability_values)

        cash_score = None
        if latest is not None and latest.cash_to_profit is not None:
            cash_score = _score_by_thresholds(latest.cash_to_profit, (
                (Decimal("1"), Decimal("90")),
                (Decimal("0.8"), Decimal("75")),
                (Decimal("0.5"), Decimal("50")),
                (Decimal("0"), Decimal("30")),
                (Decimal("-999"), Decimal("10")),
            ))
        balance_score = None
        if latest is not None and latest.debt_ratio is not None:
            ratio = latest.debt_ratio
            balance_score = (
                Decimal("90") if ratio <= Decimal("0.30") else
                Decimal("75") if ratio <= Decimal("0.50") else
                Decimal("50") if ratio <= Decimal("0.70") else Decimal("20")
            )
        pe = _decimal(valuation.metrics.get("pe_ttm"))
        pb = _decimal(valuation.metrics.get("pb"))
        valuation_values: list[Decimal] = []
        if pe is not None:
            valuation_values.append(
                Decimal("10") if pe <= 0 else
                Decimal("85") if pe <= 15 else
                Decimal("70") if pe <= 30 else
                Decimal("50") if pe <= 50 else
                Decimal("35") if pe <= 80 else Decimal("20")
            )
        if pb is not None:
            valuation_values.append(
                Decimal("80") if 0 < pb <= 2 else
                Decimal("60") if pb <= 5 else
                Decimal("35") if pb > 5 else Decimal("10")
            )
        valuation_score = _average(valuation_values)

        def unavailable(key: str, label: str, summary: str, reason: str) -> CompanyResearchDimension:
            return CompanyResearchDimension(
                key=key, label=label, weight=DIMENSION_WEIGHTS[key],
                status="unavailable", score=None, summary=summary,
                metrics={}, evidence_ids=profile_ids, reason=reason,
            )

        def scored_dimension(
            key: str, label: str, score: Decimal | None,
            summary: str, metrics: dict[str, Decimal | str | None],
            evidence_ids: tuple[str, ...], reason: str,
        ) -> CompanyResearchDimension:
            return CompanyResearchDimension(
                key=key, label=label, weight=DIMENSION_WEIGHTS[key],
                status="ready" if score is not None else "unavailable",
                score=score.quantize(Decimal("0.01")) if score is not None else None,
                summary=summary if score is not None else reason,
                metrics=metrics if score is not None else {},
                evidence_ids=evidence_ids if score is not None else (),
                reason=None if score is not None else reason,
            )

        return (
            unavailable("industry_space", "行业空间", profile.industry_analysis or "行业分析原文暂缺", "第一阶段只展示F10行业原文，不自动量化行业空间。"),
            unavailable("business_model", "商业模式", profile.company_overview or "公司概况原文暂缺", "第一阶段不根据文本主观推断商业模式得分。"),
            scored_dimension("growth", "增长质量", growth_score, "根据年度营收与净利润增长计算。", {
                "revenue_cagr_3y": history.revenue_cagr_3y,
                "net_profit_cagr_3y": history.net_profit_cagr_3y,
                "latest_revenue_yoy": latest.revenue_yoy if latest else None,
                "latest_net_profit_yoy": latest.net_profit_yoy if latest else None,
            }, financial_ids, "至少需要三年可比年度营收或净利润。"),
            scored_dimension("profitability", "盈利能力", profitability_score, "根据ROE与最新毛利率计算。", {
                "roe": roe, "gross_margin": latest.gross_margin if latest else None,
            }, (*financial_ids, *fundamentals.evidence_ids), "ROE与毛利率均不可用。"),
            scored_dimension("cash_flow", "现金流质量", cash_score, "根据经营现金流净利润比计算。", {
                "cash_to_profit": latest.cash_to_profit if latest else None,
                "operating_cash_flow": latest.operating_cash_flow if latest else None,
            }, financial_ids, "经营现金流或净利润不可用。"),
            scored_dimension("balance_sheet", "资产负债质量", balance_score, "根据资产负债率计算。", {
                "debt_ratio": latest.debt_ratio if latest else None,
            }, financial_ids, "资产或负债数据不可用。"),
            unavailable("moat", "竞争壁垒", "尚无可量化市场份额证据", "第一阶段不根据叙事自动生成护城河分数。"),
            scored_dimension("valuation", "估值吸引力", valuation_score, "只按PE/PB做宽口径风险分层，不声称跨行业低估。", {
                "pe_ttm": pe, "pb": pb,
            }, valuation.evidence_ids, "腾讯未返回可用PE/PB。"),
            unavailable("catalysts", "未来催化", summarize_latest_tips(profile.latest_tip_items), "催化因素仅展示证据，不自动评分。"),
        )

    def _counter_case(
        self,
        diagnosis: AShareDiagnosis,
        history: FinancialHistory,
        coverage: Decimal,
    ) -> tuple[CounterCaseItem, ...]:
        latest = history.latest_period
        annual = history.annual_periods
        fundamentals = diagnosis.sections["fundamentals"].metrics
        valuation = diagnosis.sections["valuation"].metrics
        trend = diagnosis.sections["trend"].metrics
        events = diagnosis.sections["events"].metrics

        def check(
            key: str, title: str, available: bool, triggered: bool,
            clear_detail: str, trigger_detail: str, threshold: str, penalty: str,
        ) -> CounterCaseItem:
            status = "triggered" if available and triggered else "clear" if available else "unavailable"
            detail = trigger_detail if status == "triggered" else clear_detail if status == "clear" else "缺少对应证据，无法核验。"
            return CounterCaseItem(
                key=key, title=title, status=status, detail=detail,
                threshold=threshold, penalty=Decimal(penalty) if status == "triggered" else Decimal("0"),
                evidence_ids=(_evidence_id("company-research", key),) if available else (),
            )

        revenue_yoy = latest.revenue_yoy if latest else None
        profit_yoy = latest.net_profit_yoy if latest else None
        net_profit = latest.net_profit if latest else None
        cashflow = latest.operating_cash_flow if latest else None
        cash_ratio = latest.cash_to_profit if latest else None
        debt_ratio = latest.debt_ratio if latest else None
        previous_margin = annual[-2].gross_margin if len(annual) >= 2 else None
        latest_margin = annual[-1].gross_margin if annual else None
        roe = _decimal(fundamentals.get("roe"))
        pe = _decimal(valuation.get("pe_ttm"))
        volatility = _decimal(trend.get("volatility_20d"))
        drawdown = _decimal(trend.get("drawdown_60d"))
        adverse = int(events.get("adverse_event_count", 0) or 0)
        return (
            check("profit_lag", "收入增长但利润未同步", revenue_yoy is not None and profit_yoy is not None, bool(revenue_yoy is not None and profit_yoy is not None and revenue_yoy > 0 and profit_yoy <= 0), "收入与利润未出现明显背离。", "收入同比为正但利润同比未增长。", "收入同比>0且利润同比<=0", "3"),
            check("profit_cash_mismatch", "利润与经营现金流背离", net_profit is not None and cashflow is not None, bool(net_profit is not None and cashflow is not None and net_profit > 0 and cashflow < 0), "利润与经营现金流方向未明显背离。", "净利润为正但经营现金流为负。", "净利润>0且经营现金流<0", "4"),
            check("cash_to_profit", "现金流净利润比偏低", cash_ratio is not None, bool(cash_ratio is not None and cash_ratio < Decimal("0.5")), "经营现金流对利润覆盖尚可。", "经营现金流净利润比低于0.5。", "现金流/净利润<0.5", "3"),
            check("margin_decline", "毛利率明显下降", previous_margin is not None and latest_margin is not None, bool(previous_margin is not None and latest_margin is not None and latest_margin < previous_margin - Decimal("0.05")), "最近年度毛利率未下降超过5个百分点。", "最近年度毛利率下降超过5个百分点。", "年度毛利率下降>5个百分点", "3"),
            check("high_debt", "资产负债率偏高", debt_ratio is not None, bool(debt_ratio is not None and debt_ratio > Decimal("0.70")), "资产负债率未超过70%。", "资产负债率超过70%。", "资产负债率>70%", "3"),
            check("low_roe", "ROE偏低", roe is not None, bool(roe is not None and roe < Decimal("5")), "ROE不低于5%。", "ROE低于5%。", "ROE<5%", "2"),
            check("valuation_risk", "估值或盈利为异常状态", pe is not None, bool(pe is not None and (pe <= 0 or pe > Decimal("80"))), "PE为正且未超过80倍宽口径风险线。", "PE为负或超过80倍。", "PE<=0或PE>80", "3"),
            check("market_risk", "波动与回撤偏高", volatility is not None and drawdown is not None, bool(volatility is not None and drawdown is not None and (volatility >= Decimal("0.08") or drawdown <= Decimal("-0.20"))), "波动率与回撤未触发宽口径风险线。", "20日波动率偏高或60日回撤较深。", "波动率>=8%或回撤<=-20%", "3"),
            check("adverse_news", "存在明确反方新闻事件", True, adverse > 0, "冻结事件中未发现明确重大反方事件。", f"存在明确关联的反方事件 {adverse} 条。", "反方事件数>0", "3"),
            check("evidence_gap", "核心研究证据不足", True, coverage < Decimal("0.60"), "可评分证据覆盖度达到60%。", "可评分证据覆盖度不足60%。", "证据覆盖度<60%", "3"),
        )

    @staticmethod
    def _sources(
        diagnosis: AShareDiagnosis,
        history: FinancialHistory,
        profile: CompanyProfileEvidence,
    ) -> tuple[ResearchSourceEvidence, ...]:
        valuation = diagnosis.sections["valuation"]
        fundamentals = diagnosis.sections["fundamentals"]
        return (
            ResearchSourceEvidence(
                source=history.source, label="多年财报三表",
                status=history.status, observed_at=history.observed_at,
                detail="新浪公开财报接口，按报告期归一化。",
            ),
            ResearchSourceEvidence(
                source=profile.source, label="公司与行业原始资料",
                status=profile.status, observed_at=profile.observed_at,
                detail="通达信F10公司概况、行业分析和最新提示。",
            ),
            ResearchSourceEvidence(
                source=valuation.source, label="当前估值",
                status=valuation.status, observed_at=_observed(valuation.observed_at),
                detail="腾讯行情PE、PB和总市值原值。",
            ),
            ResearchSourceEvidence(
                source=fundamentals.source, label="最新财务快照",
                status=fundamentals.status, observed_at=_observed(fundamentals.observed_at),
                detail="通达信财务快照中的ROE等字段。",
            ),
        )
