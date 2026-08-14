from datetime import UTC, date, datetime

from qibao_api.a_shares.research_compare import build_research_comparison
from tests.routes.test_company_research import sample_response


def test_research_compare_preserves_real_evidence_status() -> None:
    first = sample_response().model_copy(update={"symbol": "600519", "name": "贵州茅台"})
    second = sample_response().model_copy(update={"symbol": "000858", "name": "五粮液", "status": "partial"})

    result = build_research_comparison(
        (first, second),
        as_of=date(2026, 8, 14),
        generated_at=datetime(2026, 8, 14, 8, tzinfo=UTC),
    )

    assert result.status == "partial"
    assert [(item.symbol, item.name) for item in result.companies] == [
        ("600519", "贵州茅台"), ("000858", "五粮液"),
    ]
    assert result.companies[0].evidence_coverage_percent >= 0
    assert "买卖结论" in result.limitations[0]
