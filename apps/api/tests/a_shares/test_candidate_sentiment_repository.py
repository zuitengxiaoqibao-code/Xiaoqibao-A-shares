from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import sqlite3

import pytest

from qibao_api.a_shares.candidate_sentiment_repository import (
    CandidateSentimentIntegrityError,
    CandidateSentimentRepository,
)
from qibao_api.contracts.candidate_sentiment import (
    CandidateSentimentBatch,
    CandidateSentimentComponent,
    CandidateSentimentSnapshot,
)


CUTOFF = datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc)


def batch(*, generated_at: datetime = CUTOFF, score: str = "65") -> CandidateSentimentBatch:
    components = (
        CandidateSentimentComponent(
            name="news", status="ready", score=Decimal("65"), weight=Decimal("40"),
            summary="新闻偏积极", observed_at=generated_at, evidence_ids=("news-1",),
        ),
        CandidateSentimentComponent(
            name="hotspot", status="ready", score=Decimal("65"), weight=Decimal("30"),
            summary="热点可用", observed_at=generated_at, evidence_ids=("hotspot-1",),
        ),
        CandidateSentimentComponent(
            name="fund_flow", status="ready", score=Decimal("65"), weight=Decimal("30"),
            summary="资金可用", observed_at=generated_at, evidence_ids=("fund-1",),
        ),
    )
    item = CandidateSentimentSnapshot(
        candidate_snapshot_id="a-share-candidates-1",
        candidate_input_hash="a" * 64,
        symbol="600000",
        quality="ready",
        freshness="current",
        score=Decimal(score),
        band="positive",
        coverage_percent=Decimal("100"),
        components=components,
        primary_reason="新闻偏积极。",
        primary_risk="高分不代表低风险。",
        beginner_guidance="继续观察。",
        observed_at=generated_at,
        generated_at=generated_at,
        source_snapshot_ids=("news-1", "hotspot-1", "fund-1"),
    )
    return CandidateSentimentBatch(
        candidate_snapshot_id="a-share-candidates-1",
        candidate_input_hash="a" * 64,
        as_of=date(2026, 7, 18),
        cutoff=generated_at,
        quality="ready",
        items=(item,),
        generated_at=generated_at,
    )


def test_repository_reuses_identical_input_and_appends_changed_input(tmp_path) -> None:
    repository = CandidateSentimentRepository(tmp_path / "candidate-sentiment.sqlite3")

    first = repository.append(batch(), {"candidate": "a", "sources": ["one"]})
    same = repository.append(batch(), {"candidate": "a", "sources": ["one"]})
    changed = repository.append(batch(score="70"), {"candidate": "a", "sources": ["two"]})

    assert same.snapshot_id == first.snapshot_id
    assert same.items[0].snapshot_id == first.items[0].snapshot_id
    assert changed.snapshot_id != first.snapshot_id
    assert repository.verify_all() == 2


def test_repository_reads_latest_at_or_before_cutoff_and_reopens(tmp_path) -> None:
    database = tmp_path / "candidate-sentiment.sqlite3"
    repository = CandidateSentimentRepository(database)
    old = repository.append(batch(generated_at=CUTOFF), {"version": 1})
    newer_time = CUTOFF + timedelta(minutes=10)
    newer = repository.append(batch(generated_at=newer_time, score="70"), {"version": 2})

    assert repository.latest("a" * 64, cutoff=CUTOFF).snapshot_id == old.snapshot_id
    assert repository.latest("a" * 64).snapshot_id == newer.snapshot_id
    repository.close()

    reopened = CandidateSentimentRepository(database)
    assert reopened.latest("a" * 64).snapshot_id == newer.snapshot_id
    reopened.close()


def test_repository_is_append_only(tmp_path) -> None:
    repository = CandidateSentimentRepository(tmp_path / "candidate-sentiment.sqlite3")
    stored = repository.append(batch(), {"version": 1})

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute(
            "UPDATE candidate_sentiment_batches SET payload='{}' WHERE snapshot_id=?",
            (stored.snapshot_id,),
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute(
            "DELETE FROM candidate_sentiment_batches WHERE snapshot_id=?",
            (stored.snapshot_id,),
        )


def test_repository_detects_payload_and_input_tampering(tmp_path) -> None:
    repository = CandidateSentimentRepository(tmp_path / "candidate-sentiment.sqlite3")
    stored = repository.append(batch(), {"version": 1})
    repository.connection.execute("DROP TRIGGER reject_update_candidate_sentiment_batches")
    repository.connection.execute(
        "UPDATE candidate_sentiment_batches SET input_payload='{}' WHERE snapshot_id=?",
        (stored.snapshot_id,),
    )
    repository.connection.commit()

    with pytest.raises(CandidateSentimentIntegrityError, match=stored.snapshot_id):
        repository.latest("a" * 64)
