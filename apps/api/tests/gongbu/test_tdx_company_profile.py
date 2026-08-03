from datetime import datetime, timezone

from qibao_api.gongbu.tdx_client import TdxOperationError
from qibao_api.gongbu.tdx_company_profile import TdxCompanyProfileSource


class FakeClient:
    def __init__(self, values: dict[str, str | Exception]) -> None:
        self.values = values
        self.closed = False

    def F10(self, *, symbol: str, name: str):
        value = self.values[name]
        if isinstance(value, Exception):
            raise value
        return value

    def close(self) -> None:
        self.closed = True


def test_tdx_company_profile_cleans_and_limits_each_section() -> None:
    client = FakeClient({
        "公司概况": "  主营业务\n\n高端白酒   " + "甲" * 1400,
        "行业分析": " 白酒行业\n需求稳定 ",
        "最新提示": " 2026 年中报已披露 ",
    })
    source = TdxCompanyProfileSource(
        client_factory=lambda: client,
        clock=lambda: datetime(2026, 8, 3, tzinfo=timezone.utc),
    )

    result = source.fetch("600519")

    assert result.status == "ready"
    assert result.company_overview is not None
    assert "\n" not in result.company_overview
    assert len(result.company_overview) == 1200
    assert result.industry_analysis == "白酒行业 需求稳定"
    assert result.latest_tips == "2026 年中报已披露"
    assert client.closed is True


def test_tdx_company_profile_keeps_partial_evidence_when_one_section_fails() -> None:
    client = FakeClient({
        "公司概况": "主营业务为高端白酒",
        "行业分析": RuntimeError("tdx timeout"),
        "最新提示": "最新公告摘要",
    })

    result = TdxCompanyProfileSource(client_factory=lambda: client).fetch("600519")

    assert result.status == "partial"
    assert result.company_overview == "主营业务为高端白酒"
    assert result.industry_analysis is None
    assert any("行业分析" in reason for reason in result.reasons)


def test_tdx_company_profile_extracts_only_the_requested_section_from_mapping() -> None:
    client = FakeClient({
        "公司概况": {"公司概况": "主营业务为高端白酒"},
        "行业分析": {"行业分析": "白酒行业集中度较高"},
        "最新提示": {"最新提示": "最新公告摘要"},
    })

    result = TdxCompanyProfileSource(client_factory=lambda: client).fetch("600519")

    assert result.status == "ready"
    assert result.company_overview == "主营业务为高端白酒"
    assert result.industry_analysis == "白酒行业集中度较高"
    assert result.latest_tips == "最新公告摘要"


def test_tdx_company_profile_summarizes_node_failures_for_users() -> None:
    client = FakeClient({
        "公司概况": TdxOperationError(
            "mootdx F10 failed for all servers: 1.1.1.1:7709 (empty response); "
            "2.2.2.2:7709 (empty response)"
        ),
        "行业分析": TdxOperationError(
            "mootdx F10 failed for all servers: 1.1.1.1:7709 (empty response)"
        ),
        "最新提示": {"最新提示": "最新公告摘要"},
    })

    result = TdxCompanyProfileSource(client_factory=lambda: client).fetch("600519")

    assert result.status == "partial"
    assert result.reasons == (
        "通达信节点未提供公司概况",
        "通达信节点未提供行业分析",
    )
    assert all("7709" not in reason for reason in result.reasons)
