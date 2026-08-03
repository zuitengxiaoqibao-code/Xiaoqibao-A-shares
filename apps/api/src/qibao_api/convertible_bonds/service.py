from datetime import datetime, timedelta, timezone
from decimal import Decimal

import httpx

from qibao_api.contracts.market import AssetKind
from qibao_api.convertible_bonds.adapters import ClauseDataUnavailable
from qibao_api.convertible_bonds.candidates import BondCandidate, BondCandidateFilter, filter_and_rank_candidates
from qibao_api.convertible_bonds.metrics import (
    EvidenceBackedClauseState,
    calculate_metrics,
)
from qibao_api.convertible_bonds.risk import BondRiskInput, BondRiskPolicy, evaluate_bond_risk
from qibao_api.libu_compliance.repository import SourceAuthorizationError


def classify_diagnosis_state(diagnosis: dict | None) -> tuple[str, str | None]:
    """Return the user-facing observation state for one discovered bond."""
    if diagnosis is None:
        return "discovered", "尚未诊断，行情、条款与估值尚未核验"
    status = diagnosis.get("status")
    bond = diagnosis.get("bond") or {}
    if status == "stale_quote":
        return "unavailable", "行情已过期，未进入观察候选"
    if status == "source_conflict":
        return "unavailable", "条款来源冲突，未进入观察候选"
    if status != "ready":
        return "unavailable", "诊断数据不可用"
    if bond.get("suspended") or bond.get("price") is None:
        return "unavailable", "行情停牌或价格缺失"
    risk = diagnosis.get("risk") or {}
    unknowns = risk.get("unknowns") or []
    if unknowns:
        return "unavailable", "缺少：" + "、".join(str(item) for item in unknowns)
    if risk.get("outcome") == "exclude":
        return "risk_excluded", "规则风险拦截"
    if risk.get("outcome") == "eligible":
        return "diagnosed", None
    return "unavailable", "风险输入不完整，暂不进入观察候选"


class ConvertibleBondService:
    def __init__(self, quote_source, clause_source, linked_stock_source, repository, compliance,
                 diagnosis_repository, valuation_source=None,
                 *, universe_source=None, universe_repository=None,
                 clock=lambda: datetime.now(timezone.utc)) -> None:
        self.quote_source = quote_source
        self.clause_source = clause_source
        self.linked_stock_source = linked_stock_source
        self.repository = repository
        self.compliance = compliance
        self.diagnosis_repository = diagnosis_repository
        self.clock = clock
        self.valuation_source = valuation_source
        self.universe_source = universe_source
        self.universe_repository = universe_repository

    def dashboard(self) -> dict:
        all_diagnosed_codes = sorted({item["bond_code"] for item in self.diagnosis_repository.latest_by_bond()})
        diagnosis_by_code = {
            item["bond_code"]: item.get("payload") for item in self.diagnosis_repository.latest_by_bond()
        }
        clause_codes = sorted({item.contract.bond_code for item in self.repository.all_latest()})
        snapshot = self.universe_repository.latest() if self.universe_repository is not None else None
        discovered_codes = [item.bond_code for item in snapshot.items] if snapshot else []
        discovered_code_set = set(discovered_codes)
        diagnosed_codes = (
            [code for code in all_diagnosed_codes if code in discovered_code_set]
            if snapshot
            else all_diagnosed_codes
        )
        state_counts = {"discovered": 0, "unavailable": 0, "risk_excluded": 0, "diagnosed": 0}
        if snapshot:
            for item in snapshot.items:
                state, _ = classify_diagnosis_state(diagnosis_by_code.get(item.bond_code))
                state_counts[state] += 1
        codes = discovered_codes or clause_codes or diagnosed_codes
        return {
            "status": "ready" if codes else "empty",
            "bond_count": len(codes),
            "bond_codes": codes,
            "discovered_count": len(discovered_codes),
            "diagnosed_count": len(diagnosed_codes),
            "unavailable_count": state_counts["discovered"] if snapshot else max(0, len(discovered_codes) - len(diagnosed_codes)),
            "undiagnosed_count": state_counts["discovered"],
            "undignosed_count": state_counts["discovered"],
            "data_unavailable_count": state_counts["unavailable"],
            "risk_excluded_count": state_counts["risk_excluded"],
            "observable_count": state_counts["diagnosed"],
            "diagnosed_outside_universe_count": max(0, len(all_diagnosed_codes) - len(diagnosed_codes)),
            "universe_observed_at": snapshot.observed_at if snapshot else None,
        }

    async def sync_universe(self, *, max_age: timedelta = timedelta(hours=12)) -> bool:
        if self.universe_source is None or self.universe_repository is None:
            return False
        latest = self.universe_repository.latest()
        now = self.clock()
        if latest is not None and now - latest.observed_at.astimezone(timezone.utc) < max_age:
            return False
        self.compliance.require_feature_sources("bond_clauses", AssetKind.CONVERTIBLE_BOND)
        snapshot = await self.universe_source.fetch()
        self.universe_repository.append(snapshot)
        return True

    async def diagnose(self, bond_code: str) -> dict:
        now = self.clock()
        asset = AssetKind.CONVERTIBLE_BOND
        self.compliance.require_feature_sources("bond_quotes", asset)
        quote = await self.quote_source.fetch(bond_code)
        self.compliance.require_feature_sources("bond_clauses", asset)
        snapshot = await self.clause_source.fetch(bond_code)
        latest_by_source = {
            item.source: item for item in self.repository.snapshots(bond_code)
            if item.source != snapshot.source
        }
        snapshot_id = self.repository.append(snapshot)
        stock = await self.linked_stock_source.fetch(snapshot.contract.linked_stock)
        valuation = None
        if self.valuation_source is not None:
            self.compliance.require_feature_sources("bond_valuations", asset)
            try:
                valuation = await self.valuation_source.fetch(bond_code)
            except (ValueError, OSError):
                valuation = None

        metrics = calculate_metrics(
            par_value=Decimal("100"), conversion_price=snapshot.contract.conversion_price,
            stock_price=stock.price, bond_price=quote.price,
            pure_bond_value=valuation.pure_bond_value if valuation else None,
            as_of=now.date(), maturity=snapshot.contract.maturity,
            remaining_size=snapshot.contract.remaining_size, bond_suspended=quote.suspended,
            stock_suspended=getattr(stock, "suspended", False),
        )
        evidence = EvidenceBackedClauseState(
            bond_code=bond_code, state=snapshot.strong_redemption.state,
            clause_text=snapshot.strong_redemption.clause_text,
            source=snapshot.source, observed_at=snapshot.fetched_at,
            evidence_fields=snapshot.strong_redemption.evidence_fields,
        )
        risk_input = BondRiskInput(
            bond_code=bond_code, turnover_amount=quote.turnover_amount,
            conversion_premium=metrics.conversion_premium,
            remaining_size=metrics.remaining_size, remaining_days=metrics.remaining_term.days,
            strong_redemption=evidence,
        )
        risk = evaluate_bond_risk(risk_input, BondRiskPolicy())
        source_conflict = any(
            item.contract.linked_stock != snapshot.contract.linked_stock
            or item.contract.conversion_price != snapshot.contract.conversion_price
            for item in latest_by_source.values()
        )
        stale = now - quote.observed_at.astimezone(timezone.utc) > timedelta(minutes=3)
        status = "source_conflict" if source_conflict else "stale_quote" if stale else "ready"
        result = {
            "status": status,
            "bond": {"code": bond_code, "name": quote.name, "price": quote.price,
                     "previous_close": quote.previous_close, "suspended": quote.suspended},
            "linked_stock": {"code": stock.symbol, "name": stock.name, "price": stock.price,
                             "source": stock.source, "observed_at": stock.observed_at},
            "quote": {"source": quote.source, "observed_at": quote.observed_at,
                      "quality": "stale" if stale else quote.quality,
                      "raw_identity": quote.raw_identity,
                      "turnover_amount": (
                          str(quote.turnover_amount)
                          if quote.turnover_amount is not None else None
                      )},
            "clause_snapshot": {"source": snapshot.source, "fetched_at": snapshot.fetched_at,
                                "content_hash": snapshot.content_hash,
                                "conversion_price": snapshot.contract.conversion_price,
                                "maturity": snapshot.contract.maturity,
                                "remaining_size": snapshot.contract.remaining_size},
            "metric_inputs": {
                "par_value": "100", "pure_bond_value": str(valuation.pure_bond_value) if valuation else None,
                "as_of": now.date(), "maturity": snapshot.contract.maturity,
                "remaining_size": str(snapshot.contract.remaining_size),
                "conversion_price": str(snapshot.contract.conversion_price),
                "bond_quote": {"price": str(quote.price) if quote.price is not None else None,
                               "suspended": quote.suspended,
                               "quality": quote.quality, "source": quote.source,
                               "observed_at": quote.observed_at, "raw_identity": quote.raw_identity,
                               "turnover_amount": str(quote.turnover_amount)
                               if quote.turnover_amount is not None else None},
                "stock_quote": {"price": str(stock.price) if stock.price is not None else None,
                                "suspended": getattr(stock, "suspended", False),
                                "quality": stock.quality, "source": stock.source,
                                "observed_at": stock.observed_at},
                "clause_snapshot": {"snapshot_id": snapshot_id,
                                    "content_hash": snapshot.content_hash,
                                    "parser_version": snapshot.parser_version,
                                    "source": snapshot.source, "fetched_at": snapshot.fetched_at},
                "valuation": ({"source": valuation.source, "observed_at": valuation.observed_at,
                               "raw_identity": valuation.raw_identity,
                               "provider_conversion_premium": valuation.provider_conversion_premium,
                               "provider_pure_bond_premium": valuation.provider_pure_bond_premium}
                              if valuation else None),
            },
            "metrics": metrics.model_dump(mode="json"),
            "risk": {**risk.model_dump(mode="json"),
                     "unknowns": (["pure_bond_value"] if valuation is None else [])
                     + (["turnover_amount"] if quote.turnover_amount is None else []),
                     "explanations": [risk.reason_code]},
            "strong_redemption": evidence.model_dump(mode="json"),
        }
        result["diagnosis_id"] = self.diagnosis_repository.append(bond_code, result)
        return result

    def cached_diagnosis(self, bond_code: str) -> dict | None:
        record = self.diagnosis_repository.latest_for_bond(bond_code)
        if record is None:
            return None
        return {
            **record["payload"],
            "is_cached": True,
            "cache_recorded_at": record["recorded_at"],
        }

    async def diagnose_discovered(self, *, limit: int = 6) -> dict:
        """Diagnose a small, deterministic slice of the current bond universe."""
        snapshot = self.universe_repository.latest() if self.universe_repository is not None else None
        if snapshot is None:
            return {"status": "empty", "requested": 0, "processed": 0,
                    "diagnosed_count": 0, "unavailable_count": 0, "items": []}

        existing = {item["bond_code"] for item in self.diagnosis_repository.latest_by_bond()}
        targets = [item for item in snapshot.items if item.bond_code not in existing][:limit]
        items: list[dict] = []
        for item in targets:
            try:
                diagnosis = await self.diagnose(item.bond_code)
            except (ClauseDataUnavailable, SourceAuthorizationError, httpx.HTTPError, OSError, ValueError) as error:
                items.append({
                    "bond_code": item.bond_code,
                    "state": "unavailable",
                    "reason_code": self._batch_failure_reason(error),
                })
                continue
            items.append({
                "bond_code": item.bond_code,
                "state": "diagnosed",
                "status": diagnosis.get("status"),
                "risk_outcome": diagnosis.get("risk", {}).get("outcome"),
            })

        diagnosed_count = sum(item["state"] == "diagnosed" for item in items)
        observable_count = sum(
            item["state"] == "diagnosed" and item.get("risk_outcome") == "eligible"
            for item in items
        )
        risk_excluded_count = sum(
            item["state"] == "diagnosed" and item.get("risk_outcome") == "exclude"
            for item in items
        )
        return {
            "status": "ready" if items else "empty",
            "requested": len(targets),
            "processed": len(items),
            "diagnosed_count": diagnosed_count,
            "unavailable_count": len(items) - diagnosed_count,
            "observable_count": observable_count,
            "risk_excluded_count": risk_excluded_count,
            "data_unavailable_count": len(items) - diagnosed_count,
            "items": items,
        }

    @staticmethod
    def _batch_failure_reason(error: Exception) -> str:
        if isinstance(error, SourceAuthorizationError):
            return "source_unauthorized"
        if isinstance(error, ClauseDataUnavailable):
            return "clauses_unavailable"
        if isinstance(error, (httpx.HTTPError, OSError)):
            return "upstream_unavailable"
        return "invalid_provider_data"

    def candidates(self, filters: BondCandidateFilter | None = None) -> dict:
        items = []
        stored_rows = self.diagnosis_repository.latest_by_bond()
        universe_snapshot = self.universe_repository.latest() if self.universe_repository is not None else None
        universe_codes = {item.bond_code for item in universe_snapshot.items} if universe_snapshot else None
        for stored in stored_rows:
            diagnosis = stored["payload"]
            if universe_codes is not None and stored["bond_code"] not in universe_codes:
                continue
            if (diagnosis["status"] != "ready" or diagnosis["bond"]["suspended"]
                    or diagnosis["bond"]["price"] is None):
                continue
            metrics = diagnosis["metrics"]
            evidence = EvidenceBackedClauseState.model_validate(diagnosis["strong_redemption"])
            risk_input = BondRiskInput(
                bond_code=diagnosis["bond"]["code"],
                turnover_amount=diagnosis["metric_inputs"]["bond_quote"].get("turnover_amount"),
                conversion_premium=metrics["conversion_premium"],
                remaining_size=metrics["remaining_size"],
                remaining_days=metrics["remaining_term"]["days"], strong_redemption=evidence,
            )
            risk = evaluate_bond_risk(risk_input, BondRiskPolicy())
            items.append(BondCandidate(
                bond_code=diagnosis["bond"]["code"], bond_price=diagnosis["bond"]["price"],
                turnover_amount=diagnosis["metric_inputs"]["bond_quote"].get("turnover_amount"),
                conversion_premium=metrics["conversion_premium"],
                remaining_size=metrics["remaining_size"],
                remaining_days=metrics["remaining_term"]["days"],
                strong_redemption=evidence, risk=risk,
            ))
        ranked = filter_and_rank_candidates(items, filters)
        diagnosis_by_code = {stored["bond_code"]: stored["payload"] for stored in stored_rows}
        snapshot = universe_snapshot
        discovered = []
        for item in snapshot.items if snapshot else ():
            state, reason = classify_diagnosis_state(diagnosis_by_code.get(item.bond_code))
            discovered.append(
                {
                    "bond_code": item.bond_code,
                    "name": item.name,
                    "linked_stock_code": item.linked_stock_code,
                    "state": state,
                    "reason": reason,
                }
            )
        state_counts = {state: sum(item["state"] == state for item in discovered)
                        for state in ("discovered", "unavailable", "risk_excluded", "diagnosed")}
        diagnosed_count = len(discovered) - state_counts["discovered"]
        return {
            "status": "ready" if ranked else "empty",
            "items": [item.model_dump(mode="json") for item in ranked],
            "coverage": {
                "discovered_count": len(discovered),
                "diagnosed_count": diagnosed_count,
                "candidate_count": len(ranked),
                "unavailable_count": state_counts["unavailable"],
                "undiagnosed_count": state_counts["discovered"],
                "undignosed_count": state_counts["discovered"],
                "data_unavailable_count": state_counts["unavailable"],
                "risk_excluded_count": state_counts["risk_excluded"],
                "observable_count": state_counts["diagnosed"],
                "observed_at": snapshot.observed_at if snapshot else None,
            },
            "discovered": discovered,
        }

    @staticmethod
    def _diagnosis_unavailable_reason(diagnosis: dict) -> str:
        return classify_diagnosis_state(diagnosis)[1] or "诊断数据不可用"
