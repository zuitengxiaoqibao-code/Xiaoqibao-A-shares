from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from qibao_api.contracts.metric_contract import MetricContract, MetricMember


OBSERVED_AT = datetime(2026, 8, 13, 2, 30, tzinfo=timezone.utc)


def test_metric_contract_accepts_exact_member_drilldown() -> None:
    contract = MetricContract(
        metric_id="market.limit_up.count",
        label="严格涨停",
        value=23,
        unit="只",
        scope="全市场严格涨停",
        status="ready",
        trade_date=date(2026, 8, 13),
        observed_at=OBSERVED_AT,
        source="tdx-local-rpc",
        formula_version="strict-limit-v1",
        sample_count=5198,
        total_count=23,
        loaded_member_count=2,
        drilldown_kind="members",
        members=(
            MetricMember(symbol="600001", name="样本一", reason="当前价格达到涨停价"),
            MetricMember(symbol="000001", name="样本二", reason="当前价格达到涨停价"),
        ),
    )

    assert contract.loaded_member_count == 2
    assert contract.total_count == 23


def test_metric_contract_rejects_mismatched_loaded_member_count() -> None:
    with pytest.raises(ValidationError, match="loaded_member_count must match members"):
        MetricContract(
            metric_id="market.limit_up.count",
            label="严格涨停",
            value=23,
            scope="全市场严格涨停",
            status="ready",
            observed_at=OBSERVED_AT,
            source="tdx-local-rpc",
            total_count=23,
            loaded_member_count=1,
            drilldown_kind="members",
            members=(MetricMember(symbol="600001", name="样本一", reason="严格涨停"),
                     MetricMember(symbol="000001", name="样本二", reason="严格涨停")),
        )


def test_metric_contract_requires_reason_for_aggregate_only_and_unavailable() -> None:
    for status, kind in (("ready", "aggregate_only"), ("unavailable", "aggregate_only")):
        with pytest.raises(ValidationError, match="requires unavailable_reason"):
            MetricContract(
                metric_id="market.breadth.rising",
                label="上涨家数",
                value=3000 if status == "ready" else None,
                scope="全市场行情横截面",
                status=status,
                observed_at=OBSERVED_AT if status == "ready" else None,
                source="tdx-local-rpc",
                drilldown_kind=kind,
            )


def test_metric_contract_rejects_total_smaller_than_loaded_members() -> None:
    with pytest.raises(ValidationError, match="total_count cannot be smaller"):
        MetricContract(
            metric_id="market.theme.symbols",
            label="题材关联股票",
            value=1,
            unit="只",
            scope="题材关联股票去重",
            status="ready",
            observed_at=OBSERVED_AT,
            source="local-event-store",
            total_count=1,
            loaded_member_count=2,
            drilldown_kind="members",
            members=(MetricMember(symbol="600001", name="样本一", reason="题材关联"),
                     MetricMember(symbol="000001", name="样本二", reason="题材关联")),
        )
