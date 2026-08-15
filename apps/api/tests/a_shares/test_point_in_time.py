from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from qibao_api.a_shares.point_in_time import as_of, filter_as_of


NOW = datetime(2026, 8, 15, 8, 0, tzinfo=UTC)


@dataclass(frozen=True)
class Observation:
    value: str
    observed_at: datetime | None


def test_as_of_accepts_only_evidence_observed_before_cutoff():
    before = Observation("before", datetime(2026, 8, 14, 8, 0, tzinfo=UTC))
    after = Observation("after", datetime(2026, 8, 15, 9, 0, tzinfo=UTC))
    missing = Observation("missing", None)

    assert as_of(before, NOW) is before
    assert as_of(after, NOW) is None
    assert as_of(missing, NOW) is None
    assert filter_as_of((before, after, missing), NOW) == (before,)


def test_as_of_rejects_naive_cutoff_or_observation():
    with pytest.raises(ValueError, match="timezone"):
        as_of(Observation("naive", datetime(2026, 8, 14, 8, 0)), NOW)
    with pytest.raises(ValueError, match="timezone"):
        as_of(Observation("aware", NOW), datetime(2026, 8, 15, 8, 0))
