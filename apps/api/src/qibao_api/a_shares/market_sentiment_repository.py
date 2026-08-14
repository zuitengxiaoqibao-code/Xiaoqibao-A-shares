import hashlib
import hmac
import json
import sqlite3
import threading
import zlib
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from statistics import median

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from qibao_api.contracts.market_sentiment import (
    LiquidityBaseline,
    MarketSentimentSnapshot,
    SentimentPhase,
)
from qibao_api.gongbu.tencent_market_sentiment import RawSentimentBatch


RAW_RETENTION = timedelta(days=30)


class MarketSentimentStoreError(RuntimeError):
    pass


class MarketSentimentIntegrityError(MarketSentimentStoreError):
    pass


class StoredRawSentimentBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_snapshot_id: str = Field(min_length=1)
    requested_symbols: tuple[str, ...]
    valid_count: int = Field(ge=0)
    fetched_at: AwareDatetime
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    content: bytes | None


class MarketSentimentRepository:
    def __init__(self, database: str | Path) -> None:
        if isinstance(database, Path):
            database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        try:
            self.connection = sqlite3.connect(database, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._initialize()
        except sqlite3.DatabaseError as error:
            raise MarketSentimentStoreError(
                "market sentiment database cannot open"
            ) from error

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS market_sentiment_snapshots (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT NOT NULL UNIQUE,
                previous_snapshot_id TEXT,
                trading_date TEXT NOT NULL,
                phase TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                canonical_hash TEXT NOT NULL,
                chain_hash TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_market_sentiment_date_phase
            ON market_sentiment_snapshots(trading_date, phase, sequence);
            CREATE TABLE IF NOT EXISTS market_sentiment_raw_batches (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_snapshot_id TEXT NOT NULL,
                source_snapshot_id TEXT NOT NULL,
                requested_symbols TEXT NOT NULL,
                valid_count INTEGER NOT NULL,
                fetched_at TEXT NOT NULL,
                content_sha256 TEXT NOT NULL,
                compressed_content BLOB,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                UNIQUE(
                    owner_snapshot_id,
                    source_snapshot_id,
                    requested_symbols,
                    fetched_at
                ),
                FOREIGN KEY(owner_snapshot_id)
                    REFERENCES market_sentiment_snapshots(snapshot_id)
            );
            CREATE INDEX IF NOT EXISTS ix_market_sentiment_raw_expiry
            ON market_sentiment_raw_batches(expires_at, compressed_content);
            CREATE TABLE IF NOT EXISTS market_regime_risk_snapshots (
                sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                trading_date TEXT NOT NULL,
                risk_score TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                formula_version TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_market_regime_risk_date
            ON market_regime_risk_snapshots(trading_date, formula_version, sequence);
            CREATE TRIGGER IF NOT EXISTS reject_update_market_regime_risk_snapshots
            BEFORE UPDATE ON market_regime_risk_snapshots
            BEGIN
                SELECT RAISE(ABORT, 'append-only market regime risk snapshots');
            END;
            CREATE TRIGGER IF NOT EXISTS reject_delete_market_regime_risk_snapshots
            BEFORE DELETE ON market_regime_risk_snapshots
            BEGIN
                SELECT RAISE(ABORT, 'append-only market regime risk snapshots');
            END;
            CREATE TRIGGER IF NOT EXISTS reject_update_market_sentiment_snapshots
            BEFORE UPDATE ON market_sentiment_snapshots
            BEGIN
                SELECT RAISE(ABORT, 'append-only market sentiment snapshots');
            END;
            CREATE TRIGGER IF NOT EXISTS reject_delete_market_sentiment_snapshots
            BEFORE DELETE ON market_sentiment_snapshots
            BEGIN
                SELECT RAISE(ABORT, 'append-only market sentiment snapshots');
            END;
            """
        )
        self.connection.commit()

    def append_regime_risk(
        self,
        *,
        trading_date: date,
        risk_score: Decimal,
        observed_at: datetime,
        formula_version: str,
    ) -> None:
        if not Decimal("0") <= risk_score <= Decimal("100"):
            raise ValueError("regime risk score must be between 0 and 100")
        if not formula_version.strip():
            raise ValueError("regime risk formula version must not be empty")
        with self._lock, self.connection:
            existing = self.connection.execute(
                """SELECT 1 FROM market_regime_risk_snapshots
                WHERE trading_date=? AND risk_score=? AND formula_version=?
                LIMIT 1""",
                (trading_date.isoformat(), str(risk_score), formula_version),
            ).fetchone()
            if existing is not None:
                return
            self.connection.execute(
                """INSERT INTO market_regime_risk_snapshots(
                    trading_date, risk_score, observed_at, formula_version
                ) VALUES(?,?,?,?)""",
                (
                    trading_date.isoformat(), str(risk_score),
                    self._utc_text(observed_at), formula_version,
                ),
            )

    def previous_regime_risk(
        self, trading_date: date, *, formula_version: str
    ) -> Decimal | None:
        with self._lock:
            row = self.connection.execute(
                """SELECT risk_score FROM market_regime_risk_snapshots
                WHERE trading_date < ? AND formula_version=?
                ORDER BY trading_date DESC, sequence DESC LIMIT 1""",
                (trading_date.isoformat(), formula_version),
            ).fetchone()
        if row is None:
            return None
        try:
            return Decimal(str(row["risk_score"]))
        except (ArithmeticError, ValueError):
            raise MarketSentimentIntegrityError(
                "stored regime risk score is invalid"
            )

    def append(
        self,
        snapshot: MarketSentimentSnapshot,
        raw_batches: tuple[RawSentimentBatch, ...] | list[RawSentimentBatch],
    ) -> bool:
        encoded = self._canonical(snapshot)
        canonical_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        self._validate_raw_batches(raw_batches)
        with self._lock:
            existing = self.connection.execute(
                "SELECT * FROM market_sentiment_snapshots WHERE snapshot_id=?",
                (snapshot.snapshot_id,),
            ).fetchone()
            if existing is not None:
                stored = self._snapshot_from_row(existing)
                if stored != snapshot:
                    raise MarketSentimentIntegrityError(
                        "snapshot id refers to different market sentiment content"
                    )
                return False

            previous = self.connection.execute(
                """SELECT snapshot_id, chain_hash
                FROM market_sentiment_snapshots ORDER BY sequence DESC LIMIT 1"""
            ).fetchone()
            expected_previous = previous["snapshot_id"] if previous else None
            if snapshot.previous_snapshot_id != expected_previous:
                raise MarketSentimentIntegrityError(
                    "market sentiment previous snapshot does not match hash chain"
                )
            previous_chain = previous["chain_hash"] if previous else ""
            chain_hash = hashlib.sha256(
                f"{previous_chain}:{canonical_hash}".encode("ascii")
            ).hexdigest()
            try:
                with self.connection:
                    self.connection.execute(
                        """INSERT INTO market_sentiment_snapshots(
                            snapshot_id, previous_snapshot_id, trading_date, phase,
                            generated_at, canonical_hash, chain_hash, payload
                        ) VALUES(?,?,?,?,?,?,?,?)""",
                        (
                            snapshot.snapshot_id,
                            snapshot.previous_snapshot_id,
                            snapshot.trading_date.isoformat(),
                            snapshot.phase,
                            self._utc_text(snapshot.generated_at),
                            canonical_hash,
                            chain_hash,
                            encoded,
                        ),
                    )
                    for batch in raw_batches:
                        self._insert_raw_batch(snapshot.snapshot_id, batch)
            except sqlite3.DatabaseError as error:
                raise MarketSentimentStoreError(
                    "market sentiment snapshot append failed"
                ) from error
        return True

    def latest(
        self,
        *,
        trading_date: date | None = None,
        phase: SentimentPhase | None = None,
        cutoff: datetime | None = None,
        formula_version: str | None = None,
    ) -> MarketSentimentSnapshot | None:
        clauses = []
        params: list[object] = []
        if trading_date is not None:
            clauses.append("trading_date=?")
            params.append(trading_date.isoformat())
        if phase is not None:
            clauses.append("phase=?")
            params.append(phase)
        if cutoff is not None:
            clauses.append("generated_at<=?")
            params.append(self._utc_text(cutoff))
        if formula_version is not None:
            clauses.append("json_extract(payload, '$.formula_version')=?")
            params.append(formula_version)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self._lock:
            row = self.connection.execute(
                f"""SELECT * FROM market_sentiment_snapshots {where}
                ORDER BY sequence DESC LIMIT 1""",
                params,
            ).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def trajectory(
        self,
        trading_date: date,
        *,
        cutoff: datetime | None = None,
        formula_version: str | None = None,
    ) -> tuple[MarketSentimentSnapshot, ...]:
        query = "SELECT * FROM market_sentiment_snapshots WHERE trading_date=?"
        params: list[object] = [trading_date.isoformat()]
        if cutoff is not None:
            query += " AND generated_at<=?"
            params.append(self._utc_text(cutoff))
        if formula_version is not None:
            query += " AND json_extract(payload, '$.formula_version')=?"
            params.append(formula_version)
        query += " ORDER BY sequence"
        with self._lock:
            rows = self.connection.execute(query, params).fetchall()
        return tuple(self._snapshot_from_row(row) for row in rows)

    def previous_postclose(
        self, trading_date: date, *, formula_version: str | None = None
    ) -> MarketSentimentSnapshot | None:
        formula_clause = ""
        params: list[object] = [trading_date.isoformat()]
        if formula_version is not None:
            formula_clause = " AND json_extract(payload, '$.formula_version')=?"
            params.append(formula_version)
        with self._lock:
            row = self.connection.execute(
                f"""SELECT * FROM market_sentiment_snapshots
                WHERE trading_date < ? AND phase='postclose'
                {formula_clause}
                ORDER BY trading_date DESC, sequence DESC LIMIT 1""",
                params,
            ).fetchone()
        return self._snapshot_from_row(row) if row is not None else None

    def liquidity_baseline(
        self,
        *,
        phase: SentimentPhase,
        before_trading_date: date,
        sample_size: int = 20,
        formula_version: str | None = None,
    ) -> LiquidityBaseline | None:
        if sample_size < 1:
            raise ValueError("sample size must be positive")
        formula_clause = ""
        params: list[object] = [phase, before_trading_date.isoformat()]
        if formula_version is not None:
            formula_clause = " AND json_extract(payload, '$.formula_version')=?"
            params.append(formula_version)
        params.append(sample_size)
        with self._lock:
            rows = self.connection.execute(
                f"""SELECT * FROM (
                    SELECT *, row_number() OVER (
                        PARTITION BY trading_date ORDER BY sequence DESC
                    ) AS day_rank
                    FROM market_sentiment_snapshots
                    WHERE phase=? AND trading_date<?
                    {formula_clause}
                ) latest_by_day
                WHERE day_rank=1
                ORDER BY trading_date DESC
                LIMIT ?""",
                params,
            ).fetchall()
        amounts: list[Decimal] = []
        evidence_ids: list[str] = []
        for row in rows:
            item = self._snapshot_from_row(row)
            liquidity = next(
                (
                    component
                    for component in item.components
                    if component.name in {"activity", "liquidity"}
                ),
                None,
            )
            if liquidity is None:
                continue
            value = liquidity.metrics.get("total_amount_wan")
            if value is None:
                continue
            amount = Decimal(str(value))
            if amount <= 0:
                continue
            amounts.append(amount)
            evidence_ids.append(item.snapshot_id)
        if not amounts:
            return None
        return LiquidityBaseline(
            amount_wan=Decimal(median(amounts)),
            quality="ready" if len(amounts) >= sample_size else "partial",
            sample_size=len(amounts),
            evidence_ids=tuple(evidence_ids),
        )

    def raw_batches(
        self, snapshot_id: str
    ) -> tuple[StoredRawSentimentBatch, ...]:
        with self._lock:
            rows = self.connection.execute(
                """SELECT * FROM market_sentiment_raw_batches
                WHERE owner_snapshot_id=? ORDER BY sequence""",
                (snapshot_id,),
            ).fetchall()
        values = []
        for row in rows:
            content = (
                zlib.decompress(row["compressed_content"])
                if row["compressed_content"] is not None
                else None
            )
            if content is not None:
                digest = hashlib.sha256(content).hexdigest()
                if not hmac.compare_digest(digest, row["content_sha256"]):
                    raise MarketSentimentIntegrityError(
                        "raw batch failed integrity check"
                    )
            values.append(
                StoredRawSentimentBatch(
                    source_snapshot_id=row["source_snapshot_id"],
                    requested_symbols=tuple(json.loads(row["requested_symbols"])),
                    valid_count=row["valid_count"],
                    fetched_at=datetime.fromisoformat(row["fetched_at"]),
                    content_sha256=row["content_sha256"],
                    content=content,
                )
            )
        return tuple(values)

    def purge_expired_raw_batches(self, now: datetime) -> int:
        with self._lock, self.connection:
            cursor = self.connection.execute(
                """UPDATE market_sentiment_raw_batches
                SET compressed_content=NULL
                WHERE compressed_content IS NOT NULL AND expires_at<=?""",
                (self._utc_text(now),),
            )
        return cursor.rowcount

    def _snapshot_from_row(self, row: sqlite3.Row) -> MarketSentimentSnapshot:
        computed = hashlib.sha256(row["payload"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(computed, row["canonical_hash"]):
            raise MarketSentimentIntegrityError(
                "market sentiment snapshot failed integrity check"
            )
        try:
            snapshot = MarketSentimentSnapshot.model_validate_json(row["payload"])
        except (ValidationError, ValueError) as error:
            raise MarketSentimentIntegrityError(
                "market sentiment snapshot payload is invalid"
            ) from error
        stored_fields = (
            row["snapshot_id"],
            row["previous_snapshot_id"],
            row["trading_date"],
            row["phase"],
        )
        payload_fields = (
            snapshot.snapshot_id,
            snapshot.previous_snapshot_id,
            snapshot.trading_date.isoformat(),
            snapshot.phase,
        )
        if stored_fields != payload_fields:
            raise MarketSentimentIntegrityError(
                "market sentiment snapshot index differs from payload"
            )
        previous_chain = ""
        if snapshot.previous_snapshot_id is not None:
            previous = self.connection.execute(
                """SELECT chain_hash FROM market_sentiment_snapshots
                WHERE snapshot_id=?""",
                (snapshot.previous_snapshot_id,),
            ).fetchone()
            if previous is None:
                raise MarketSentimentIntegrityError(
                    "market sentiment hash chain predecessor is missing"
                )
            previous_chain = previous["chain_hash"]
        expected_chain = hashlib.sha256(
            f"{previous_chain}:{computed}".encode("ascii")
        ).hexdigest()
        if not hmac.compare_digest(expected_chain, row["chain_hash"]):
            raise MarketSentimentIntegrityError(
                "market sentiment hash chain failed integrity check"
            )
        return snapshot

    def _insert_raw_batch(
        self, owner_snapshot_id: str, batch: RawSentimentBatch
    ) -> None:
        fetched_at = batch.fetched_at.astimezone(timezone.utc)
        self.connection.execute(
            """INSERT OR IGNORE INTO market_sentiment_raw_batches(
                owner_snapshot_id, source_snapshot_id, requested_symbols,
                valid_count, fetched_at, content_sha256, compressed_content,
                created_at, expires_at
            ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                owner_snapshot_id,
                batch.snapshot_id,
                json.dumps(batch.requested_symbols, separators=(",", ":")),
                batch.valid_count,
                fetched_at.isoformat(),
                batch.content_sha256,
                sqlite3.Binary(zlib.compress(batch.content)),
                fetched_at.isoformat(),
                (fetched_at + RAW_RETENTION).isoformat(),
            ),
        )

    @staticmethod
    def _validate_raw_batches(
        raw_batches: tuple[RawSentimentBatch, ...] | list[RawSentimentBatch],
    ) -> None:
        for batch in raw_batches:
            digest = hashlib.sha256(batch.content).hexdigest()
            if not hmac.compare_digest(digest, batch.content_sha256):
                raise MarketSentimentIntegrityError(
                    "raw batch content hash does not match content"
                )

    @staticmethod
    def _canonical(snapshot: MarketSentimentSnapshot) -> str:
        return json.dumps(
            snapshot.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _utc_text(value: datetime) -> str:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("datetime must include a timezone")
        return value.astimezone(timezone.utc).isoformat()

    def close(self) -> None:
        with self._lock:
            self.connection.close()
