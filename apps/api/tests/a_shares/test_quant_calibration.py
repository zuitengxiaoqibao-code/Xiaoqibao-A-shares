from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

from qibao_api.a_shares.quant_calibration import build_calibration_report


NOW = datetime(2026, 8, 14, 8, 0, tzinfo=UTC)


class Ledger:
    def recent(self, *, limit):
        assert limit == 500
        return tuple(
            SimpleNamespace(
                as_of=date(2026, 7, index + 1),
                symbol=f"600{index:03d}",
                formula_version="a-share-short-strategy-v2.0",
                outcomes=(SimpleNamespace(horizon=5, status="ready", return_percent=Decimal("1.5")),),
            )
            for index in range(10)
        )


def test_quant_calibration_is_partial_without_reliable_sample_size() -> None:
    report = build_calibration_report(Ledger(), horizon=5, generated_at=NOW)

    assert report.status == "partial"
    assert report.mature_sample_count == 10
    assert report.splits[0].sample_count == 6
    assert report.splits[1].sample_count == 2
    assert report.splits[2].sample_count == 2
    assert report.fee_bps is None
    assert "成本与滑点尚未" in report.limitations[0]
