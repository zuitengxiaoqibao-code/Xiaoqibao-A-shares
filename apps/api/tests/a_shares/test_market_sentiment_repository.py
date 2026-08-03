import hashlib
import sqlite3
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from qibao_api.a_shares.market_sentiment import MarketSentimentEvaluator
from qibao_api.a_shares.market_sentiment_repository import (
    MarketSentimentIntegrityError,
    MarketSentimentRepository,
)
from qibao_api.contracts.market_sentiment import MarketBreadthObservation
from qibao_api.gongbu.tencent_market_sentiment import RawSentimentBatch


NOW = datetime(2026, 7, 18, 6, 0, tzinfo=timezone.utc)


def snapshot(
    trading_date: date,
    *,
    phase: str = "intraday",
    amount_wan: str = "1000",
    generated_at: datetime = NOW,
    previous_snapshot_id: str | None = None,
):
    observation = MarketBreadthObservation(
        requested_count=100,
        valid_count=100,
        rising_count=60,
        falling_count=35,
        flat_count=5,
        median_change_percent=Decimal("0.8"),
        total_amount_wan=Decimal(amount_wan),
        limit_up_count=20,
        limit_down_count=3,
        broken_limit_up_count=5,
        max_limit_streak=4,
        observed_at=generated_at - timedelta(seconds=5),
        fetched_at=generated_at,
        source_snapshot_ids=(f"source-{trading_date}-{phase}-{amount_wan}",),
    )
    return MarketSentimentEvaluator().evaluate(
        observation=observation,
        liquidity_baseline=None,
        hotspot=None,
        trading_date=trading_date,
        phase=phase,
        generated_at=generated_at,
        previous_snapshot_id=previous_snapshot_id,
    )


def raw_batch(*, fetched_at: datetime = NOW, content: bytes = b"raw quotes"):
    digest = hashlib.sha256(content).hexdigest()
    return RawSentimentBatch(
        snapshot_id=f"raw-{digest[:24]}",
        requested_symbols=("600000", "000001"),
        valid_count=2,
        fetched_at=fetched_at,
        content_sha256=digest,
        content=content,
    )


def test_append_is_idempotent_and_preserves_changed_same_phase_versions(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    first = snapshot(date(2026, 7, 17), phase="postclose")
    second = snapshot(
        date(2026, 7, 18),
        amount_wan="1200",
        generated_at=NOW + timedelta(minutes=1),
        previous_snapshot_id=first.snapshot_id,
    )

    assert repository.append(first, (raw_batch(),)) is True
    assert repository.append(first, (raw_batch(),)) is False
    assert repository.append(second, ()) is True
    assert repository.trajectory(date(2026, 7, 18)) == (second,)
    assert repository.previous_postclose(date(2026, 7, 18)) == first
    repository.close()


def test_snapshot_table_is_append_only_and_payload_tampering_is_detected(
    tmp_path: Path,
) -> None:
    database = tmp_path / "sentiment.sqlite3"
    repository = MarketSentimentRepository(database)
    stored = snapshot(date(2026, 7, 18))
    repository.append(stored, ())

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute(
            "UPDATE market_sentiment_snapshots SET payload='{}'"
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        repository.connection.execute("DELETE FROM market_sentiment_snapshots")

    repository.connection.execute(
        "DROP TRIGGER reject_update_market_sentiment_snapshots"
    )
    repository.connection.execute(
        "UPDATE market_sentiment_snapshots SET payload='{}' WHERE snapshot_id=?",
        (stored.snapshot_id,),
    )
    repository.connection.commit()
    with pytest.raises(MarketSentimentIntegrityError, match="integrity"):
        repository.latest(trading_date=date(2026, 7, 18))
    repository.close()


def test_raw_batches_are_hash_verified_compressed_and_expired_content_is_purged(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    stored = snapshot(date(2026, 7, 18))
    batch = raw_batch(fetched_at=NOW - timedelta(days=31))
    repository.append(stored, (batch,))

    before = repository.raw_batches(stored.snapshot_id)
    assert before[0].content == b"raw quotes"
    assert before[0].content_sha256 == hashlib.sha256(b"raw quotes").hexdigest()
    assert repository.purge_expired_raw_batches(NOW) == 1
    after = repository.raw_batches(stored.snapshot_id)
    assert after[0].content is None
    assert after[0].content_sha256 == before[0].content_sha256

    invalid = batch.model_copy(update={"content_sha256": "0" * 64})
    later = snapshot(
        date(2026, 7, 19),
        generated_at=NOW + timedelta(days=1),
        previous_snapshot_id=stored.snapshot_id,
    )
    with pytest.raises(MarketSentimentIntegrityError, match="raw batch"):
        repository.append(later, (invalid,))
    repository.close()


def test_queries_honor_cutoff_and_build_same_phase_liquidity_baseline(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    previous_id = None
    for offset, amount in enumerate(("800", "1000", "1200")):
        generated_at = NOW - timedelta(days=3 - offset)
        item = snapshot(
            date(2026, 7, 15 + offset),
            amount_wan=amount,
            generated_at=generated_at,
            previous_snapshot_id=previous_id,
        )
        repository.append(item, ())
        previous_id = item.snapshot_id

    cutoff = NOW - timedelta(days=1, seconds=1)
    assert len(repository.trajectory(date(2026, 7, 17), cutoff=cutoff)) == 0
    baseline = repository.liquidity_baseline(
        phase="intraday", before_trading_date=date(2026, 7, 18)
    )
    assert baseline is not None
    assert baseline.amount_wan == Decimal("1000")
    assert baseline.sample_size == 3
    assert baseline.quality == "partial"
    assert len(baseline.evidence_ids) == 3
    repository.close()


def test_current_formula_queries_never_return_another_formula_version(
    tmp_path: Path,
) -> None:
    repository = MarketSentimentRepository(tmp_path / "sentiment.sqlite3")
    current = snapshot(date(2026, 7, 17), phase="postclose", amount_wan="1200")
    repository.append(current, ())
    previous_formula = snapshot(
        date(2026, 7, 18),
        amount_wan="9000",
        generated_at=NOW + timedelta(minutes=1),
        previous_snapshot_id=current.snapshot_id,
    ).model_copy(update={
        "snapshot_id": "sentiment-previous-formula",
        "formula_version": "a-share-sentiment-v1",
    })
    repository.append(previous_formula, ())

    assert repository.latest(formula_version="a-share-sentiment-v2") == current
    assert repository.trajectory(
        date(2026, 7, 18), formula_version="a-share-sentiment-v2"
    ) == ()
    assert repository.previous_postclose(
        date(2026, 7, 18), formula_version="a-share-sentiment-v2"
    ) == current
    baseline = repository.liquidity_baseline(
        phase="intraday",
        before_trading_date=date(2026, 7, 19),
        formula_version="a-share-sentiment-v2",
    )
    assert baseline is None
    repository.close()
