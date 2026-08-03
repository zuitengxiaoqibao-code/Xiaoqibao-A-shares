import hashlib
import hmac
import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from qibao_api.contracts.candidate_sentiment import CandidateSentimentBatch


class CandidateSentimentStoreError(RuntimeError):
    pass


class CandidateSentimentIntegrityError(CandidateSentimentStoreError):
    pass


class CandidateSentimentRepository:
    def __init__(self, database: str | Path) -> None:
        self._lock = threading.RLock()
        try:
            self.connection = sqlite3.connect(database, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._initialize()
        except sqlite3.DatabaseError as error:
            raise CandidateSentimentStoreError(
                "candidate sentiment database cannot open"
            ) from error

    def _initialize(self) -> None:
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS candidate_sentiment_batches (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_id TEXT NOT NULL UNIQUE,
          candidate_snapshot_id TEXT NOT NULL,
          candidate_input_hash TEXT NOT NULL,
          input_hash TEXT NOT NULL UNIQUE,
          input_payload TEXT NOT NULL,
          canonical_hash TEXT NOT NULL,
          payload TEXT NOT NULL,
          generated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_candidate_sentiment_input
        ON candidate_sentiment_batches(candidate_input_hash, generated_at, sequence);
        CREATE TRIGGER IF NOT EXISTS reject_update_candidate_sentiment_batches
        BEFORE UPDATE ON candidate_sentiment_batches
        BEGIN SELECT RAISE(ABORT, 'append-only candidate sentiment batches'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_candidate_sentiment_batches
        BEFORE DELETE ON candidate_sentiment_batches
        BEGIN SELECT RAISE(ABORT, 'append-only candidate sentiment batches'); END;
        """)

    def append(
        self, batch: CandidateSentimentBatch, input_payload: dict
    ) -> CandidateSentimentBatch:
        if batch.snapshot_id is not None or any(
            item.snapshot_id is not None for item in batch.items
        ):
            raise ValueError("cannot append an already frozen candidate sentiment batch")
        input_encoded = json.dumps(
            input_payload,
            default=str,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        input_hash = hashlib.sha256(input_encoded.encode("utf-8")).hexdigest()
        try:
            with self._lock:
                existing = self.connection.execute(
                    "SELECT * FROM candidate_sentiment_batches WHERE input_hash=?",
                    (input_hash,),
                ).fetchone()
                if existing is not None:
                    return self._verified(existing)

                snapshot_id = f"candidate-sentiment-batch-{uuid4().hex}"
                items = tuple(
                    item.model_copy(update={
                        "snapshot_id": f"{snapshot_id}-{item.symbol}",
                    })
                    for item in batch.items
                )
                stored = batch.model_copy(update={
                    "snapshot_id": snapshot_id,
                    "items": items,
                })
                encoded = stored.model_dump_json()
                canonical_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
                with self.connection:
                    self.connection.execute(
                        """INSERT INTO candidate_sentiment_batches(
                        snapshot_id,candidate_snapshot_id,candidate_input_hash,input_hash,
                        input_payload,canonical_hash,payload,generated_at
                        ) VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            snapshot_id,
                            stored.candidate_snapshot_id,
                            stored.candidate_input_hash,
                            input_hash,
                            input_encoded,
                            canonical_hash,
                            encoded,
                            stored.generated_at.astimezone(timezone.utc).isoformat(),
                        ),
                    )
                return stored
        except CandidateSentimentIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CandidateSentimentStoreError(
                "candidate sentiment append failed"
            ) from error

    def latest(
        self,
        candidate_input_hash: str,
        *,
        cutoff: datetime | None = None,
    ) -> CandidateSentimentBatch | None:
        normalized_cutoff = cutoff.astimezone(timezone.utc) if cutoff else None
        try:
            with self._lock:
                rows = self.connection.execute(
                    """SELECT * FROM candidate_sentiment_batches
                    WHERE candidate_input_hash=?
                    ORDER BY generated_at DESC, sequence DESC""",
                    (candidate_input_hash,),
                ).fetchall()
                for row in rows:
                    generated_at = datetime.fromisoformat(row["generated_at"])
                    if normalized_cutoff is not None and generated_at > normalized_cutoff:
                        continue
                    return self._verified(row)
            return None
        except CandidateSentimentIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CandidateSentimentStoreError(
                "candidate sentiment read failed"
            ) from error

    def verify_all(self) -> int:
        try:
            with self._lock:
                rows = self.connection.execute(
                    "SELECT * FROM candidate_sentiment_batches ORDER BY sequence"
                ).fetchall()
                for row in rows:
                    self._verified(row)
            return len(rows)
        except CandidateSentimentIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CandidateSentimentStoreError(
                "candidate sentiment verification failed"
            ) from error

    @staticmethod
    def _verified(row: sqlite3.Row) -> CandidateSentimentBatch:
        snapshot_id = str(row["snapshot_id"])
        input_hash = hashlib.sha256(row["input_payload"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(input_hash, row["input_hash"]):
            raise CandidateSentimentIntegrityError(
                f"candidate sentiment {snapshot_id} input failed integrity check"
            )
        canonical_hash = hashlib.sha256(row["payload"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(canonical_hash, row["canonical_hash"]):
            raise CandidateSentimentIntegrityError(
                f"candidate sentiment {snapshot_id} failed integrity check"
            )
        batch = CandidateSentimentBatch.model_validate_json(row["payload"])
        if batch.snapshot_id != snapshot_id:
            raise CandidateSentimentIntegrityError(
                f"candidate sentiment {snapshot_id} identity differs"
            )
        if not hmac.compare_digest(
            batch.candidate_input_hash, str(row["candidate_input_hash"])
        ):
            raise CandidateSentimentIntegrityError(
                f"candidate sentiment {snapshot_id} candidate hash differs"
            )
        return batch

    def close(self) -> None:
        with self._lock:
            self.connection.close()
