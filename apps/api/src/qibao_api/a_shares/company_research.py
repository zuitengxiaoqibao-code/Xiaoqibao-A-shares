import asyncio
import hashlib
from collections.abc import Callable
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from qibao_api.a_shares.diagnosis import AShareDiagnosis
from qibao_api.contracts.company_research import (
    CompanyProfileEvidence,
    CompanyResearchDimension,
    CompanyResearchSection,
    CompanyResearchResponse,
    CounterCaseItem,
    FinancialHistory,
    HolderEvidence,
    MarginEvidence,
    PeerCandidateEvidence,
    ResearchEnrichmentEvidence,
    ResearchDecisionLedgerRow,
    ValuationScenarioRange,
    ResearchReportEvidence,
    ResearchSourceEvidence,
    UnlockEvidence,
    ValuationObservation,
)
from qibao_api.contracts.evidence_ledger import EvidenceLedgerEntry
from qibao_api.contracts.field_evidence import FieldEvidence


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


def _decision_ledger(
    symbol: str,
    enrichment: ResearchEnrichmentEvidence,
    valuation: ValuationObservation,
    profile: CompanyProfileEvidence,
    counter_case: tuple[CounterCaseItem, ...],
) -> tuple[ResearchDecisionLedgerRow, ...]:
    peers = tuple(item for item in enrichment.peer_candidates if item.symbol != symbol)
    peer_facts = []
    for item in peers:
        metrics = []
        if item.pe_ttm is not None and item.pe_ttm > 0:
            metrics.append(f"PE {item.pe_ttm:.2f}")
        if item.pb is not None and item.pb > 0:
            metrics.append(f"PB {item.pb:.2f}")
        peer_facts.append(f"{item.symbol} {item.name}" + (f" · {' · '.join(metrics)}" if metrics else ""))
    peer_row = ResearchDecisionLedgerRow(
        key="peer_context", label="同行参照",
        status="ready" if peers else "unavailable",
        summary=f"已核验 {len(peers)} 家同板块同行。" if peers else "尚未取得可核验同行样本。",
        facts=tuple(peer_facts),
        limitation=None if peers else "不使用跨行业公司或无估值字段的记录补位。",
    )

    valuation_facts = []
    if valuation.pe_ttm is not None:
        valuation_facts.append(f"PE(TTM) {valuation.pe_ttm:.2f}")
    if valuation.pb is not None:
        valuation_facts.append(f"PB {valuation.pb:.2f}")
    if valuation.peer_pe_median is not None:
        valuation_facts.append(f"同行 PE 中位 {valuation.peer_pe_median:.2f}")
    if valuation.peer_pb_median is not None:
        valuation_facts.append(f"同行 PB 中位 {valuation.peer_pb_median:.2f}")
    if valuation.forward_pe_status == "available" and valuation.forward_pe is not None:
        valuation_facts.append(
            f"前向 PE {valuation.forward_pe:.2f}（{valuation.forward_eps_sample_count}家机构明年EPS中位）"
        )
    elif valuation.forward_pe_status == "low_confidence":
        valuation_facts.append(
            f"明年EPS预测样本 {valuation.forward_eps_sample_count}家，未达到3家门槛"
        )
    valuation_row = ResearchDecisionLedgerRow(
        key="valuation", label="估值证据",
        status="ready" if valuation.forward_pe_status == "available" else "partial" if valuation_facts else "unavailable",
        summary=valuation.forward_pe_reason,
        facts=tuple(valuation_facts),
        limitation=valuation.observation_range_reason,
    )

    catalysts = tuple(item for item in profile.latest_tip_items if item.tone == "positive")
    catalyst_row = ResearchDecisionLedgerRow(
        key="catalysts", label="未来催化",
        status="ready" if catalysts else "partial" if profile.latest_tip_items else "unavailable",
        summary=f"识别 {len(catalysts)} 项有原文与时间的正向事件。" if catalysts else "未识别具备原文与时间的正向催化。",
        facts=tuple(f"{item.date or '日期未提供'} · {item.summary}" for item in catalysts),
        evidence_ids=tuple(item.id for item in catalysts),
        limitation="事件只作为待验证催化，不推导涨跌或目标价。",
    )

    triggered = tuple(item for item in counter_case if item.status == "triggered")
    unavailable = tuple(item for item in counter_case if item.status == "unavailable")
    contrary_row = ResearchDecisionLedgerRow(
        key="contrary", label="反方证据",
        status="triggered" if triggered else "partial" if unavailable else "clear",
        summary=f"触发 {len(triggered)} 项，待核验 {len(unavailable)} 项。",
        facts=tuple(f"{item.title} · {item.detail}" for item in triggered),
        evidence_ids=tuple(dict.fromkeys(evidence_id for item in triggered for evidence_id in item.evidence_ids)),
        limitation="未触发只表示当前字段未越过规则阈值，不代表风险不存在。",
    )
    invalidation_row = ResearchDecisionLedgerRow(
        key="invalidation", label="逻辑失效",
        status="triggered" if triggered else "partial" if unavailable else "clear",
        summary="存在已触发的逻辑失效条件，需要重新核验研究假设。" if triggered else "当前已核验条件未触发。",
        facts=tuple(f"{item.title} · 规则 {item.threshold}" for item in triggered if item.threshold),
        evidence_ids=tuple(dict.fromkeys(evidence_id for item in triggered for evidence_id in item.evidence_ids)),
        limitation=f"仍有 {len(unavailable)} 项缺少字段。" if unavailable else None,
    )
    return peer_row, valuation_row, catalyst_row, contrary_row, invalidation_row


def _research_sections(
    symbol: str,
    history: FinancialHistory,
    valuation: ValuationObservation,
    profile: CompanyProfileEvidence,
    enrichment: ResearchEnrichmentEvidence,
    dimensions: tuple[CompanyResearchDimension, ...],
    counter_case: tuple[CounterCaseItem, ...],
) -> tuple[CompanyResearchSection, ...]:
    by_dimension = {item.key: item for item in dimensions}
    latest = history.latest_period
    financial_facts = tuple(
        item for item in (
            f"营收三年复合增长 {history.revenue_cagr_3y * 100:.2f}%" if history.revenue_cagr_3y is not None else None,
            f"净利润三年复合增长 {history.net_profit_cagr_3y * 100:.2f}%" if history.net_profit_cagr_3y is not None else None,
            f"最新营收同比 {latest.revenue_yoy:.2f}%" if latest is not None and latest.revenue_yoy is not None else None,
            f"最新净利润同比 {latest.net_profit_yoy:.2f}%" if latest is not None and latest.net_profit_yoy is not None else None,
        ) if item is not None
    )
    profit_facts = tuple(
        item for item in (
            f"经营现金流 {latest.operating_cash_flow:.2f}" if latest is not None and latest.operating_cash_flow is not None else None,
            f"经营现金流/净利润 {latest.cash_to_profit:.2f}" if latest is not None and latest.cash_to_profit is not None else None,
            f"毛利率 {latest.gross_margin * 100:.2f}%" if latest is not None and latest.gross_margin is not None else None,
        ) if item is not None
    )
    peers = tuple(item for item in enrichment.peer_candidates if item.symbol != symbol)
    peer_facts = tuple(
        f"{item.symbol} {item.name}"
        + (f" · PE {item.pe_ttm:.2f}" if item.pe_ttm is not None and item.pe_ttm > 0 else "")
        + (f" · PB {item.pb:.2f}" if item.pb is not None and item.pb > 0 else "")
        for item in peers
    )
    valuation_facts = tuple(
        item for item in (
            f"PE(TTM) {valuation.pe_ttm:.2f}" if valuation.pe_ttm is not None else None,
            f"PB {valuation.pb:.2f}" if valuation.pb is not None else None,
            f"同行 PE 中位 {valuation.peer_pe_median:.2f}" if valuation.peer_pe_median is not None else None,
            f"同行 PB 中位 {valuation.peer_pb_median:.2f}" if valuation.peer_pb_median is not None else None,
        ) if item is not None
    )
    catalysts = tuple(item for item in profile.latest_tip_items if item.tone == "positive")
    triggered = tuple(item for item in counter_case if item.status == "triggered")
    unavailable = tuple(item for item in counter_case if item.status == "unavailable")
    checklist = tuple(dict.fromkeys((
        "核对公司概况与主营业务原文",
        "核对最近三年财报与经营现金流",
        "核对同行样本是否属于同一行业口径",
        "核对机构预测样本数量与最新报告日期",
        "核对未来催化公告原文和发生时间",
        *(f"补齐风险检查：{item.title}" for item in unavailable),
    )))
    profile_ids = tuple(dict.fromkeys(
        item.id for item in profile.latest_tip_items
    ))
    return (
        CompanyResearchSection(
            key="business_model", label="商业模式",
            status="ready" if profile.company_overview else "unavailable",
            summary=profile.company_overview or "公司概况原文不可用，不能归纳商业模式。",
            evidence_ids=profile_ids,
            limitation=None if profile.company_overview else "缺少通达信 F10 公司概况原文。",
        ),
        CompanyResearchSection(
            key="industry_space", label="行业空间",
            status="ready" if profile.industry_analysis else "unavailable",
            summary=profile.industry_analysis or "行业分析原文不可用，不能判断行业空间。",
            evidence_ids=profile_ids,
            limitation=None if profile.industry_analysis else "缺少通达信 F10 行业分析原文。",
        ),
        CompanyResearchSection(
            key="financial_trend", label="财务趋势",
            status="ready" if financial_facts else "unavailable",
            summary=by_dimension["growth"].summary,
            facts=financial_facts,
            evidence_ids=by_dimension["growth"].evidence_ids,
            limitation=None if financial_facts else by_dimension["growth"].reason,
        ),
        CompanyResearchSection(
            key="profit_quality", label="利润质量",
            status="ready" if profit_facts else "unavailable",
            summary="使用利润、毛利率与经营现金流交叉核验利润质量。" if profit_facts else "利润质量证据不足。",
            facts=profit_facts,
            evidence_ids=tuple(dict.fromkeys((*by_dimension["profitability"].evidence_ids, *by_dimension["cash_flow"].evidence_ids))),
            limitation=None if profit_facts else "缺少毛利率、经营现金流或净利润字段。",
        ),
        CompanyResearchSection(
            key="competitive_position", label="竞争地位",
            status="partial" if peers else "unavailable",
            summary=f"已取得 {len(peers)} 家同板块同行作为估值参照；尚无市场份额证据，不能确认竞争优势。" if peers else "尚未取得可核验同行和市场份额证据。",
            facts=peer_facts,
            limitation="同行估值只能作为参照，不能替代市场份额、客户结构或成本优势证据。",
        ),
        CompanyResearchSection(
            key="valuation_percentile", label="估值分位",
            status="partial" if valuation_facts else "unavailable",
            summary="当前估值与同行中位已核验；历史估值分位暂不可用。" if valuation_facts else "估值证据不可用。",
            facts=valuation_facts,
            evidence_ids=by_dimension["valuation"].evidence_ids,
            limitation=valuation.observation_range_reason,
        ),
        CompanyResearchSection(
            key="future_catalysts", label="未来催化",
            status="ready" if catalysts else "partial" if profile.latest_tip_items else "unavailable",
            summary=f"识别 {len(catalysts)} 项有原文与时间的正向事件。" if catalysts else "未识别具备原文与时间的正向催化。",
            facts=tuple(f"{item.date or '日期未提供'} · {item.summary}" for item in catalysts),
            evidence_ids=tuple(item.id for item in catalysts),
            limitation="催化只作为待核验事件，不推导价格涨跌。",
        ),
        CompanyResearchSection(
            key="contrary_risks", label="反方风险",
            status="triggered" if triggered else "partial" if unavailable else "clear",
            summary=f"触发 {len(triggered)} 项反方风险，另有 {len(unavailable)} 项待核验。",
            facts=tuple(f"{item.title} · {item.detail}" for item in triggered),
            evidence_ids=tuple(dict.fromkeys(evidence_id for item in triggered for evidence_id in item.evidence_ids)),
            limitation="未触发只表示当前字段未越过规则阈值，不代表风险不存在。",
        ),
        CompanyResearchSection(
            key="invalidation_conditions", label="失效条件",
            status="triggered" if triggered else "partial" if unavailable else "clear",
            summary="已触发的规则需要重新核验研究逻辑。" if triggered else "当前已核验失效条件未触发。",
            facts=tuple(f"{item.title} · {item.threshold}" for item in triggered if item.threshold),
            evidence_ids=tuple(dict.fromkeys(evidence_id for item in triggered for evidence_id in item.evidence_ids)),
            limitation=f"仍有 {len(unavailable)} 项缺少字段。" if unavailable else None,
        ),
        CompanyResearchSection(
            key="verification_checklist", label="核验清单",
            status="partial" if unavailable else "ready",
            summary="下单前由用户逐项回到原始来源复核；系统不代替投资决定。",
            facts=checklist,
            limitation=f"仍有 {len(unavailable)} 项风险规则缺少字段。" if unavailable else None,
        ),
    )


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


def _median(values: list[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / Decimal("2")


def _forward_eps(
    reports: tuple[ResearchReportEvidence, ...],
    selected_date: date,
) -> tuple[Decimal | None, int, date | None]:
    latest_by_organization: dict[str, ResearchReportEvidence] = {}
    for report in sorted(
        (item for item in reports if item.publish_date <= selected_date),
        key=lambda item: item.publish_date,
        reverse=True,
    ):
        organization = report.organization.strip()
        if not organization or organization in latest_by_organization:
            continue
        if report.eps_next_year is None or report.eps_next_year <= 0:
            continue
        latest_by_organization[organization] = report
    values = [item.eps_next_year for item in latest_by_organization.values() if item.eps_next_year is not None]
    latest_date = max((item.publish_date for item in latest_by_organization.values()), default=None)
    return _median(values), len(values), latest_date


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
        enrichment_source: Any | None = None,
        enrichment_repository: Any | None = None,
        version_repository: Any | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.diagnosis_service = diagnosis_service
        self.financial_source = financial_source
        self.profile_source = profile_source
        self.enrichment_source = enrichment_source
        self.enrichment_repository = enrichment_repository
        self.version_repository = version_repository
        self.clock = clock
        self._enrichment_tasks: dict[str, asyncio.Task] = {}

    async def get(
        self,
        symbol: str,
        as_of: date | None = None,
        progress_callback: Callable[[str, str], None] | None = None,
    ) -> CompanyResearchResponse:
        selected_date = as_of or self.clock().date()
        if progress_callback is not None:
            progress_callback("identity", f"已锁定 {symbol} · {selected_date.isoformat()}")
        diagnosis_task = asyncio.create_task(self.diagnosis_service.diagnose(symbol, selected_date))
        financial_task = asyncio.create_task(asyncio.to_thread(self.financial_source.fetch, symbol))
        profile_task = asyncio.create_task(asyncio.to_thread(self.profile_source.fetch, symbol))
        for task, stage, detail in (
            (diagnosis_task, "diagnosis", "行情、估值和风险诊断已返回"),
            (financial_task, "financials", "多年财务数据已返回"),
            (profile_task, "profile", "通达信 F10 证据已返回"),
        ):
            if progress_callback is not None:
                task.add_done_callback(
                    lambda _task, current_stage=stage, current_detail=detail: progress_callback(current_stage, current_detail)
                )
        diagnosis_result, financial_result, profile_result = await asyncio.gather(
            diagnosis_task,
            financial_task,
            profile_task,
            return_exceptions=True,
        )
        if isinstance(diagnosis_result, Exception):
            latest = self.version_repository.latest(symbol) if self.version_repository is not None else None
            if latest is not None:
                reason = f"核心研究刷新失败，沿用最近冻结研究版本：{type(diagnosis_result).__name__}"
                return latest.model_copy(update={
                    "status": "partial",
                    "reasons": tuple(dict.fromkeys((*latest.reasons, reason))),
                })
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
        enrichment = self._cached_enrichment(symbol)
        self._schedule_enrichment(symbol, enrichment.observed_at)
        if progress_callback is not None:
            progress_callback("events", "研报、催化、解禁和筹码缓存已核验")
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
        price = _decimal(market_metrics.get("price"))
        forward_eps_median, forward_eps_sample_count, forecast_latest_report_date = _forward_eps(
            enrichment.stock_reports,
            selected_date,
        )
        forecast_age_days = (
            (selected_date - forecast_latest_report_date).days
            if forecast_latest_report_date is not None else None
        )
        forecast_freshness = (
            "fresh" if forecast_age_days is not None and forecast_age_days <= 180
            else "stale" if forecast_age_days is not None
            else "unavailable"
        )
        forward_pe_status = (
            "available" if forecast_freshness == "fresh" and forward_eps_sample_count >= 3 and price is not None and price > 0
            else "low_confidence" if forecast_freshness == "fresh" and forward_eps_sample_count > 0
            else "unavailable"
        )
        forward_pe = (
            (price / forward_eps_median).quantize(Decimal("0.01"))
            if forward_pe_status == "available" and forward_eps_median is not None else None
        )
        peer_pe_median = _median([
            item.pe_ttm for item in enrichment.peer_candidates
            if item.symbol != symbol and item.pe_ttm is not None and item.pe_ttm > 0
        ])
        peer_pb_median = _median([
            item.pb for item in enrichment.peer_candidates
            if item.symbol != symbol and item.pb is not None and item.pb > 0
        ])
        scenario_available = (
            forecast_freshness == "fresh"
            and forward_eps_sample_count >= 3
            and forward_eps_median is not None
            and forward_eps_median > 0
            and peer_pe_median is not None
            and peer_pe_median > 0
        )
        scenario_range = ValuationScenarioRange(
            status="available" if scenario_available else "unavailable",
            conservative=(forward_eps_median * peer_pe_median * Decimal("0.8")).quantize(Decimal("0.01")) if scenario_available else None,
            neutral=(forward_eps_median * peer_pe_median).quantize(Decimal("0.01")) if scenario_available else None,
            optimistic=(forward_eps_median * peer_pe_median * Decimal("1.2")).quantize(Decimal("0.01")) if scenario_available else None,
            eps_basis=forward_eps_median if scenario_available else None,
            peer_pe_basis=peer_pe_median if scenario_available else None,
            institution_sample_count=forward_eps_sample_count,
            latest_report_date=forecast_latest_report_date,
            reason=(
                "使用机构明年 EPS 中位数与同行 PE 中位数做 0.8/1.0/1.2 倍机械情景；这不是目标价，也不是价格预测。"
                if scenario_available
                else "机构样本少于3家、报告超过180天、EPS非正或同行PE中位缺失，不计算情景区间。"
            ),
        )
        valuation = ValuationObservation(
            status=valuation_section.status,
            pe_ttm=_decimal(valuation_metrics.get("pe_ttm")),
            pb=_decimal(valuation_metrics.get("pb")),
            market_cap_yi=_decimal(valuation_metrics.get("market_cap_yi")),
            peer_pe_median=peer_pe_median,
            peer_pb_median=peer_pb_median,
            forward_eps_median=forward_eps_median,
            forward_eps_sample_count=forward_eps_sample_count,
            forecast_latest_report_date=forecast_latest_report_date,
            forecast_age_days=forecast_age_days,
            forecast_freshness=forecast_freshness,
            forward_pe=forward_pe,
            forward_pe_status=forward_pe_status,
            forward_pe_reason=(
                f"采用 {forward_eps_sample_count} 家不同机构的最新明年 EPS 预测中位数计算。"
                if forward_pe_status == "available"
                else f"明年 EPS 预测距研究日已 {forecast_age_days} 天，超过 180 天，不计算前向 PE。"
                if forecast_freshness == "stale"
                else f"仅有 {forward_eps_sample_count} 家不同机构预测，少于 3 家，不计算前向 PE。"
                if forward_pe_status == "low_confidence"
                else "没有可用的正值明年 EPS 预测，不计算前向 PE。"
            ),
            scenario_range=scenario_range,
            observation_range_status="unavailable",
            observation_range_reason="缺少历史估值序列，不计算价格目标或历史分位。",
            source=valuation_section.source,
            observed_at=_observed(valuation_section.observed_at),
        )
        reasons = (*history.reasons, *profile.reasons)
        status = "ready" if coverage >= Decimal("0.60") and not reasons else "partial"
        evidence_ledger = (
            EvidenceLedgerEntry(
                source=" / ".join(dict.fromkeys((
                    *(item.source for item in self._sources(diagnosis, history, profile)),
                    *enrichment.sources,
                ))) or "unavailable",
                operation="company_research",
                status=status,
                trade_date=selected_date,
                observed_at=self.clock(),
                formula_version="company-research-evidence-v2",
                sample_count=len(history.periods) if history.periods else None,
                limitations=tuple(reasons),
            ),
        )
        response = CompanyResearchResponse(
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
            enrichment=enrichment,
            decision_ledger=_decision_ledger(symbol, enrichment, valuation, profile, counter_case),
            research_sections=_research_sections(
                symbol, history, valuation, profile, enrichment, dimensions, counter_case,
            ),
            evidence_ledger=evidence_ledger,
            field_evidence=self._field_evidence(
                selected_date=selected_date, generated_at=self.clock(),
                coverage=coverage, base_score=base_score,
                risk_penalty=risk_penalty, final_score=final_score,
                history=history, valuation=valuation, profile=profile,
                reasons=tuple(reasons),
            ),
            sources=self._sources(diagnosis, history, profile),
            reasons=tuple(reasons),
        )
        if progress_callback is not None:
            progress_callback("analysis", "评分、反方审查和证据账本已合成")
        return self.version_repository.append(response) if self.version_repository is not None else response

    @staticmethod
    def _field_evidence(
        *, selected_date, generated_at, coverage, base_score, risk_penalty,
        final_score, history, valuation, profile, reasons,
    ) -> tuple[FieldEvidence, ...]:
        coverage_percent = (coverage * Decimal("100")).quantize(Decimal("0.01"))
        final_limitations = tuple(reasons) or (("evidence_coverage_below_60_percent",) if final_score is None else ())
        entries = [
            FieldEvidence(
                field_path="base_score", value=base_score,
                source="company-research-dimensions" if base_score is not None else "unavailable",
                source_field=None, status="derived" if base_score is not None else "missing",
                trade_date=selected_date, observed_at=generated_at if base_score is not None else None,
                coverage_percent=coverage_percent if base_score is not None else None,
                derived=base_score is not None, formula="verified dimension weighted mean" if base_score is not None else None,
                limitations=tuple(reasons) if base_score is not None else ("verified_dimensions_unavailable",),
            ),
            FieldEvidence(
                field_path="risk_penalty", value=risk_penalty,
                source="company-research-counter-case", source_field=None,
                status="derived", trade_date=selected_date, observed_at=generated_at,
                coverage_percent=coverage_percent, derived=True,
                formula="sum(triggered counter-case penalties)", limitations=tuple(reasons),
            ),
            FieldEvidence(
                field_path="final_score", value=final_score,
                source="company-research-evidence", source_field=None,
                status="derived" if final_score is not None else "missing",
                trade_date=selected_date, observed_at=generated_at if final_score is not None else None,
                coverage_percent=coverage_percent if final_score is not None else None,
                derived=final_score is not None, formula="base_score - risk_penalty" if final_score is not None else None,
                limitations=final_limitations,
            ),
        ]
        latest = history.latest_period
        for path, source, source_field, value, observed_at in (
            ("financial_history.latest_period.revenue", history.source, "revenue", latest.revenue if latest else None, history.observed_at),
            ("financial_history.latest_period.net_profit", history.source, "net_profit", latest.net_profit if latest else None, history.observed_at),
            ("valuation.pe_ttm", valuation.source, "pe_ttm", valuation.pe_ttm, valuation.observed_at),
            ("valuation.pb", valuation.source, "pb", valuation.pb, valuation.observed_at),
        ):
            entries.append(FieldEvidence(
                field_path=path, value=value,
                source=source if value is not None else "unavailable", source_field=source_field,
                status="cached" if value is not None else "missing", trade_date=selected_date,
                observed_at=observed_at if value is not None else None,
                coverage_percent=None, derived=False, formula=None,
                limitations=() if value is not None else (f"{path}_unavailable",),
            ))
        profile_source = profile.source if profile.source else "unavailable"
        profile_observed = _observed(profile.observed_at)
        profile_evidence_id = (_evidence_id(profile.source, "profile"),) if profile.observed_at else ()
        for path, source_field, value, limitation in (
            ("profile.company_overview", "company_overview", profile.company_overview, "company_overview_unavailable"),
            ("profile.industry_analysis", "industry_analysis", profile.industry_analysis, "industry_analysis_unavailable"),
            ("profile.latest_tips", "latest_tips", Decimal(len(profile.latest_tip_items)), "latest_tips_unavailable"),
        ):
            available = bool(value) if path != "profile.latest_tips" else value > 0
            entries.append(FieldEvidence(
                field_path=path,
                value=value if available else None,
                source=profile_source if available else "unavailable",
                source_field=source_field,
                status="cached" if available else "missing",
                trade_date=selected_date,
                observed_at=profile_observed if available else None,
                coverage_percent=coverage_percent if available else None,
                derived=False,
                formula=None,
                evidence_ids=profile_evidence_id if available else (),
                limitations=() if available else (limitation,),
            ))
        forward_available = valuation.forward_pe_status in {"available", "low_confidence"} and valuation.forward_pe is not None
        entries.append(FieldEvidence(
            field_path="valuation.forward_pe",
            value=valuation.forward_pe if forward_available else None,
            source=valuation.source if forward_available else "unavailable",
            source_field="forward_pe",
            status="derived" if forward_available else "missing",
            trade_date=selected_date,
            observed_at=valuation.observed_at if forward_available else None,
            coverage_percent=coverage_percent if forward_available else None,
            derived=forward_available,
            formula="price / forward_eps_median" if forward_available else None,
            evidence_ids=(_evidence_id(valuation.source, "forward_pe"),) if forward_available else (),
            limitations=() if forward_available else (valuation.forward_pe_reason,),
        ))
        return tuple(entries)

    def _cached_enrichment(self, symbol: str) -> ResearchEnrichmentEvidence:
        if self.enrichment_repository is None:
            return ResearchEnrichmentEvidence(reasons=("研究扩展缓存未配置",))
        try:
            snapshot = self.enrichment_repository.latest(symbol)
        except (OSError, RuntimeError, ValueError):
            return ResearchEnrichmentEvidence(reasons=("研究扩展缓存读取失败",))
        if snapshot is None:
            return ResearchEnrichmentEvidence(reasons=("后台正在首次采集研报与筹码数据",))
        populated = sum(bool(value) for value in (
            snapshot.stock_reports, snapshot.industry_reports, snapshot.unlocks,
            snapshot.margin, snapshot.holders, snapshot.peer_candidates,
        ))
        return ResearchEnrichmentEvidence(
            status="ready" if populated >= 3 else "partial",
            observed_at=snapshot.observed_at,
            stock_reports=tuple(ResearchReportEvidence.model_validate(item, from_attributes=True) for item in snapshot.stock_reports),
            industry_reports=tuple(ResearchReportEvidence.model_validate(item, from_attributes=True) for item in snapshot.industry_reports),
            industry_name=snapshot.industry_name,
            industry_code=snapshot.industry_code,
            industry_board_code=snapshot.industry_board_code,
            peer_candidates=tuple(PeerCandidateEvidence.model_validate(item, from_attributes=True) for item in snapshot.peer_candidates),
            unlocks=tuple(UnlockEvidence.model_validate(item, from_attributes=True) for item in snapshot.unlocks),
            margin=tuple(MarginEvidence.model_validate(item, from_attributes=True) for item in snapshot.margin),
            holders=tuple(HolderEvidence.model_validate(item, from_attributes=True) for item in snapshot.holders),
            sources=snapshot.sources,
            reasons=snapshot.warnings,
        )

    def _schedule_enrichment(self, symbol: str, observed_at: datetime | None) -> None:
        if self.enrichment_source is None or self.enrichment_repository is None:
            return
        if observed_at is not None and self.clock() - observed_at < timedelta(hours=12):
            return
        current = self._enrichment_tasks.get(symbol)
        if current is not None and not current.done():
            return
        task = asyncio.create_task(self._refresh_enrichment(symbol))
        self._enrichment_tasks[symbol] = task

    async def _refresh_enrichment(self, symbol: str) -> None:
        try:
            snapshot = await self.enrichment_source.fetch(symbol)
            await asyncio.to_thread(self.enrichment_repository.append, snapshot)
        except asyncio.CancelledError:
            raise
        except Exception:
            return
        finally:
            self._enrichment_tasks.pop(symbol, None)

    def close(self) -> None:
        for task in self._enrichment_tasks.values():
            task.cancel()
        self._enrichment_tasks.clear()

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
