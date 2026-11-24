from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import shutil
import threading
from datetime import date, datetime, timezone

from qibao_api.contracts.bars import DailyBar
from qibao_api.contracts.instruments import validate_a_share_code


@dataclass(frozen=True)
class BarCoverage:
    symbol: str
    bar_count: int
    latest_trade_date: date | None


@dataclass(frozen=True)
class BarCoverageAggregate:
    """One read-only market-wide coverage calculation for a target date."""

    universe_count: int
    dominant_trade_date: date | None
    dominant_date_count: int
    latest_available_trade_date: date | None
    latest_available_trade_date_count: int
    history_ready_count: int
    backfill_complete_count: int

    @property
    def fragmented_latest_count(self) -> int:
        return max(0, self.universe_count - self.dominant_date_count)

    @property
    def missing_history_count(self) -> int:
        return max(0, self.universe_count - self.history_ready_count)


class BarRepository:
    def __init__(
        self,
        database_path: Path,
        parquet_dir: Path,
        *,
        read_only: bool = False,
        ensure_schema: bool = True,
    ) -> None:
        self.database_path = database_path
        self.parquet_dir = parquet_dir
        self.read_only = read_only
        self.ensure_schema = ensure_schema
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.parquet_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._schema_ready = False

    def _raw_connect(self):
        import duckdb

        return duckdb.connect(str(self.database_path), read_only=self.read_only)

    def _connect(self):
        self._ensure_schema()
        return self._raw_connect()

    def _ensure_schema(self) -> None:
        if self.read_only or not self.ensure_schema:
            return
        if self._schema_ready:
            return
        with self._lock:
            if self._schema_ready:
                return
            self._create_schema()
            self._schema_ready = True

    def _create_schema(self) -> None:
        with self._lock, self._raw_connect() as connection:
            if connection.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'main' AND table_name = 'daily_bars_legacy'"
            ).fetchone()[0]:
                raise RuntimeError(
                    "Unfinished daily_bars migration: preserve daily_bars_legacy "
                    "and recover it before initializing the repository"
                )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS daily_bars (
                    symbol VARCHAR NOT NULL,
                    trade_date DATE NOT NULL,
                    open DECIMAL(18, 4) NOT NULL,
                    high DECIMAL(18, 4) NOT NULL,
                    low DECIMAL(18, 4) NOT NULL,
                    close DECIMAL(18, 4) NOT NULL,
                    volume BIGINT NOT NULL,
                    amount DECIMAL(24, 4) NOT NULL,
                    source VARCHAR NOT NULL,
                    ingested_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                    observation_id VARCHAR NOT NULL DEFAULT (uuid()::VARCHAR)
                )
                """
            )
            columns = connection.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'daily_bars'"
            ).fetchall()
            if "observation_id" not in {row[0] for row in columns}:
                connection.execute("BEGIN TRANSACTION")
                try:
                    self._migrate_legacy_schema(connection)
                    connection.execute("COMMIT")
                except Exception:
                    connection.execute("ROLLBACK")
                    raise

    @staticmethod
    def _migrate_legacy_schema(connection) -> None:
        original_count = connection.execute("SELECT count(*) FROM daily_bars").fetchone()[0]
        connection.execute("ALTER TABLE daily_bars RENAME TO daily_bars_legacy")
        connection.execute(
            """CREATE TABLE daily_bars (
                symbol VARCHAR NOT NULL, trade_date DATE NOT NULL,
                open DECIMAL(18, 4) NOT NULL, high DECIMAL(18, 4) NOT NULL,
                low DECIMAL(18, 4) NOT NULL, close DECIMAL(18, 4) NOT NULL,
                volume BIGINT NOT NULL, amount DECIMAL(24, 4) NOT NULL,
                source VARCHAR NOT NULL,
                ingested_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
                observation_id VARCHAR NOT NULL DEFAULT (uuid()::VARCHAR)
            )"""
        )
        connection.execute(
            """INSERT INTO daily_bars
            (symbol, trade_date, open, high, low, close, volume, amount, source, ingested_at)
            SELECT symbol, trade_date, open, high, low, close, volume, amount, source,
                   ingested_at FROM daily_bars_legacy"""
        )
        copied_count = connection.execute("SELECT count(*) FROM daily_bars").fetchone()[0]
        if copied_count != original_count:
            raise RuntimeError("daily_bars migration row count mismatch")
        connection.execute("DROP TABLE daily_bars_legacy")

    def upsert(self, bars: list[DailyBar]) -> None:
        rows = [
            (
                bar.symbol,
                bar.trade_date,
                bar.open,
                bar.high,
                bar.low,
                bar.close,
                bar.volume,
                bar.amount,
                bar.source,
            )
            for bar in bars
        ]
        if not rows:
            return
        with self._lock, self._connect() as connection:
            self._insert_rows(connection, rows, "daily_bars")

    @staticmethod
    def _insert_rows(connection, rows: list[tuple], table: str) -> None:
        """Scan a whole frame instead of executing an INSERT for every bar."""
        import pandas as pd

        if table not in {"daily_bars", "incoming_daily_bars"}:
            raise ValueError("Unsupported daily bar table")
        columns = ("symbol", "trade_date", "open", "high", "low", "close", "volume", "amount", "source")
        frame = pd.DataFrame.from_records(rows, columns=columns)
        # Keep exact decimals even when DuckDB's object sampling encounters
        # only whole numbers before a later row with fractional prices.
        for column in ("open", "high", "low", "close", "amount"):
            frame[column] = frame[column].map(str)
        connection.register("incoming_bar_frame", frame)
        try:
            connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) "
                f"SELECT {', '.join(columns)} FROM incoming_bar_frame"
            )
        finally:
            connection.unregister("incoming_bar_frame")

    def append_missing(self, bars: list[DailyBar]) -> int:
        if not bars:
            return 0
        grouped: dict[tuple[str, date], DailyBar] = {}
        for bar in bars:
            symbol = validate_a_share_code(bar.symbol)
            grouped[(symbol, bar.trade_date)] = bar
        existing: set[tuple[str, date]] = set()
        symbols = sorted({symbol for symbol, _ in grouped})
        with self._lock:
            with self._connect() as connection:
                for symbol in symbols:
                    dates = sorted(
                        trade_date
                        for candidate, trade_date in grouped
                        if candidate == symbol
                    )
                    placeholders = ", ".join("?" for _ in dates)
                    rows = connection.execute(
                        f"""SELECT DISTINCT symbol, trade_date
                            FROM daily_bars
                            WHERE symbol = ? AND trade_date IN ({placeholders})""",
                        [symbol, *dates],
                    ).fetchall()
                    existing.update((row[0], row[1]) for row in rows)
            missing = [bar for key, bar in grouped.items() if key not in existing]
            self.upsert(missing)
        return len(missing)

    def append_missing_batch(self, bars: list[DailyBar]) -> int:
        """Atomically insert a market-wide daily slice without per-symbol queries."""
        if not bars:
            return 0
        unique = {(validate_a_share_code(bar.symbol), bar.trade_date): bar for bar in bars}
        rows = [(bar.symbol, bar.trade_date, bar.open, bar.high, bar.low, bar.close,
                 bar.volume, bar.amount, bar.source) for bar in unique.values()]
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN TRANSACTION")
            try:
                connection.execute("CREATE TEMP TABLE incoming_daily_bars AS SELECT symbol,trade_date,open,high,low,close,volume,amount,source FROM daily_bars LIMIT 0")
                self._insert_rows(connection, rows, "incoming_daily_bars")
                count = connection.execute("SELECT count(*) FROM incoming_daily_bars i WHERE NOT EXISTS (SELECT 1 FROM daily_bars d WHERE d.symbol=i.symbol AND d.trade_date=i.trade_date)").fetchone()[0]
                connection.execute("INSERT INTO daily_bars (symbol,trade_date,open,high,low,close,volume,amount,source) SELECT * FROM incoming_daily_bars i WHERE NOT EXISTS (SELECT 1 FROM daily_bars d WHERE d.symbol=i.symbol AND d.trade_date=i.trade_date)")
                connection.execute("COMMIT")
            except Exception:
                connection.execute("ROLLBACK")
                raise
        return int(count)

    def append_preferred(self, bars: list[DailyBar], preferred_sources: tuple[str, ...]) -> tuple[int, int, int]:
        """Append missing rows and supersede weaker source revisions when needed."""
        if not bars:
            return 0, 0, 0
        grouped = {(validate_a_share_code(bar.symbol), bar.trade_date): bar for bar in bars}
        imported = replaced = skipped = 0
        with self._lock, self._connect() as connection:
            for (symbol, trade_date), bar in grouped.items():
                existing = connection.execute(
                    "SELECT source FROM daily_bars WHERE symbol=? AND trade_date=? ORDER BY ingested_at DESC LIMIT 1",
                    (symbol, trade_date),
                ).fetchone()
                if existing is None:
                    imported += 1
                elif existing[0] in preferred_sources:
                    skipped += 1
                    continue
                else:
                    replaced += 1
                connection.execute(
                    """INSERT INTO daily_bars (symbol,trade_date,open,high,low,close,volume,amount,source)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (symbol, bar.trade_date, bar.open, bar.high, bar.low, bar.close,
                     bar.volume, bar.amount, bar.source),
                )
        return imported, replaced, skipped

    def append_preferred_batch(
        self,
        bars: list[DailyBar],
        preferred_sources: tuple[str, ...],
    ) -> tuple[int, int, int]:
        """Append a de-duplicated batch without issuing one query per daily bar."""
        if not bars:
            return 0, 0, 0
        grouped = {
            (validate_a_share_code(bar.symbol), bar.trade_date): bar
            for bar in bars
        }
        rows = [
            (
                symbol, trade_date, bar.open, bar.high, bar.low, bar.close,
                bar.volume, bar.amount, bar.source,
            )
            for (symbol, trade_date), bar in grouped.items()
        ]
        with self._lock, self._connect() as connection:
            connection.execute(
                """CREATE TEMP TABLE incoming_daily_bars (
                    symbol VARCHAR, trade_date DATE, open DECIMAL(18, 4),
                    high DECIMAL(18, 4), low DECIMAL(18, 4), close DECIMAL(18, 4),
                    volume BIGINT, amount DECIMAL(24, 4), source VARCHAR
                )"""
            )
            self._insert_rows(connection, rows, "incoming_daily_bars")
            preferred = list(preferred_sources)
            placeholders = ", ".join("?" for _ in preferred)
            summary = connection.execute(
                f"""
                WITH existing AS (
                    SELECT i.symbol, i.trade_date,
                           arg_max(b.source, b.ingested_at) AS source
                    FROM incoming_daily_bars i
                    LEFT JOIN daily_bars b
                      ON b.symbol = i.symbol AND b.trade_date = i.trade_date
                    GROUP BY i.symbol, i.trade_date
                )
                SELECT
                    count(*) FILTER (WHERE source IS NULL),
                    count(*) FILTER (
                        WHERE source IS NOT NULL AND source NOT IN ({placeholders})
                    ),
                    count(*) FILTER (WHERE source IN ({placeholders}))
                FROM existing
                """,
                [*preferred, *preferred],
            ).fetchone()
            imported, replaced, skipped = (int(value or 0) for value in summary)
            connection.execute(
                f"""
                INSERT INTO daily_bars
                    (symbol, trade_date, open, high, low, close, volume, amount, source)
                SELECT i.symbol, i.trade_date, i.open, i.high, i.low, i.close,
                       i.volume, i.amount, i.source
                FROM incoming_daily_bars i
                LEFT JOIN (
                    SELECT symbol, trade_date, arg_max(source, ingested_at) AS source
                    FROM daily_bars
                    WHERE (symbol, trade_date) IN (
                        SELECT symbol, trade_date FROM incoming_daily_bars
                    )
                    GROUP BY symbol, trade_date
                ) existing
                  ON existing.symbol = i.symbol AND existing.trade_date = i.trade_date
                WHERE existing.source IS NULL
                   OR existing.source NOT IN ({placeholders})
                """,
                preferred,
            )
        return imported, replaced, skipped

    def coverage(
        self, symbols: Sequence[str], target_date: date
    ) -> dict[str, BarCoverage]:
        validated = list(dict.fromkeys(
            validate_a_share_code(symbol) for symbol in symbols
        ))
        result = {
            symbol: BarCoverage(symbol=symbol, bar_count=0, latest_trade_date=None)
            for symbol in validated
        }
        if not validated:
            return result
        placeholders = ", ".join("?" for _ in validated)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""SELECT symbol, count(DISTINCT trade_date), max(trade_date)
                    FROM daily_bars
                    WHERE symbol IN ({placeholders}) AND trade_date <= ?
                    GROUP BY symbol""",
                [*validated, target_date],
            ).fetchall()
        result.update({
            row[0]: BarCoverage(
                symbol=row[0], bar_count=int(row[1]), latest_trade_date=row[2]
            )
            for row in rows
        })
        return result

    def latest_dates(
        self,
        symbols: Sequence[str],
        target_date: date,
    ) -> dict[str, date | None]:
        """Return only the latest watermark needed by incremental imports."""
        validated = list(dict.fromkeys(
            validate_a_share_code(symbol) for symbol in symbols
        ))
        result: dict[str, date | None] = {symbol: None for symbol in validated}
        if not validated:
            return result
        placeholders = ", ".join("?" for _ in validated)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""SELECT symbol, max(trade_date)
                    FROM daily_bars
                    WHERE symbol IN ({placeholders}) AND trade_date <= ?
                    GROUP BY symbol""",
                [*validated, target_date],
            ).fetchall()
        result.update({row[0]: row[1] for row in rows})
        return result

    def coverage_aggregate(
        self,
        symbols: Sequence[str],
        target_date: date,
        *,
        minimum_bars: int = 250,
        backfill_bars: int = 300,
    ) -> BarCoverageAggregate:
        """Return de-duplicated latest-date and history watermarks in one query."""
        if minimum_bars < 1:
            raise ValueError("minimum_bars must be positive")
        if backfill_bars < minimum_bars:
            raise ValueError("backfill_bars must not be below minimum_bars")
        validated = list(dict.fromkeys(
            validate_a_share_code(symbol) for symbol in symbols
        ))
        if not validated:
            return BarCoverageAggregate(0, None, 0, None, 0, 0, 0)
        placeholders = ", ".join("?" for _ in validated)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                WITH latest_by_date AS (
                    SELECT symbol, trade_date,
                           ROW_NUMBER() OVER (
                               PARTITION BY symbol, trade_date
                               ORDER BY ingested_at DESC, observation_id DESC
                           ) AS revision_rank
                    FROM daily_bars
                    WHERE symbol IN ({placeholders}) AND trade_date <= ?
                ), deduped AS (
                    SELECT symbol, trade_date
                    FROM latest_by_date
                    WHERE revision_rank = 1
                ), per_symbol AS (
                    SELECT symbol, max(trade_date) AS latest_trade_date,
                           count(*) AS bar_count
                    FROM deduped
                    GROUP BY symbol
                ), date_counts AS (
                    SELECT latest_trade_date, count(*) AS symbol_count
                    FROM per_symbol
                    GROUP BY latest_trade_date
                )
                SELECT
                    (SELECT count(*) FROM per_symbol),
                    (SELECT latest_trade_date FROM date_counts
                     ORDER BY symbol_count DESC, latest_trade_date DESC LIMIT 1),
                    (SELECT symbol_count FROM date_counts
                     ORDER BY symbol_count DESC, latest_trade_date DESC LIMIT 1),
                    (SELECT max(latest_trade_date) FROM per_symbol),
                    (SELECT symbol_count FROM date_counts
                     WHERE latest_trade_date = (SELECT max(latest_trade_date) FROM per_symbol)),
                    (SELECT count(*) FROM per_symbol WHERE bar_count >= ?),
                    (SELECT count(*) FROM per_symbol WHERE bar_count >= ?)
                """,
                [*validated, target_date, minimum_bars, backfill_bars],
            ).fetchone()
        return BarCoverageAggregate(
            universe_count=int(rows[0] or 0),
            dominant_trade_date=rows[1],
            dominant_date_count=int(rows[2] or 0),
            latest_available_trade_date=rows[3],
            latest_available_trade_date_count=int(rows[4] or 0),
            history_ready_count=int(rows[5] or 0),
            backfill_complete_count=int(rows[6] or 0),
        )

    def latest(
        self, symbol: str, limit: int = 250, *, cutoff: datetime | None = None,
    ) -> list[DailyBar]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT symbol, trade_date, open, high, low, close, volume, amount, source
                FROM daily_bars
                WHERE symbol = ? AND (? IS NULL OR ingested_at <= ?)
                QUALIFY row_number() OVER (
                    PARTITION BY symbol, trade_date
                    ORDER BY ingested_at DESC, observation_id DESC
                ) = 1
                ORDER BY trade_date DESC LIMIT ?
                """,
                [symbol, _database_cutoff(cutoff), _database_cutoff(cutoff), limit],
            ).fetchall()
        return [
            DailyBar(
                symbol=row[0], trade_date=row[1], open=row[2], high=row[3], low=row[4],
                close=row[5], volume=row[6], amount=row[7], source=row[8],
            )
            for row in rows
        ]

    def trade_dates(self, limit: int = 1000) -> list:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """SELECT DISTINCT trade_date FROM daily_bars
                ORDER BY trade_date DESC LIMIT ?""",
                [limit],
            ).fetchall()
        return [row[0] for row in rows]

    def latest_trade_date(self, as_of: date) -> date | None:
        """Return the latest stored trading date at or before ``as_of``."""
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT max(trade_date) FROM daily_bars WHERE trade_date <= ?",
                [as_of],
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def dominant_trade_date(
        self, as_of: date, *, minimum_bars: int = 60
    ) -> date | None:
        """Return the latest date shared by the largest eligible symbol set."""
        if minimum_bars < 1:
            raise ValueError("minimum_bars must be positive")
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                WITH eligible_symbols AS (
                    SELECT symbol
                    FROM daily_bars
                    WHERE trade_date <= ?
                    GROUP BY symbol
                    HAVING count(DISTINCT trade_date) >= ?
                ), date_counts AS (
                    SELECT b.trade_date, count(DISTINCT b.symbol) AS symbol_count
                    FROM daily_bars b
                    JOIN eligible_symbols e ON e.symbol = b.symbol
                    WHERE b.trade_date <= ?
                    GROUP BY b.trade_date
                )
                SELECT trade_date
                FROM date_counts
                ORDER BY symbol_count DESC, trade_date DESC
                LIMIT 1
                """,
                [as_of, minimum_bars, as_of],
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def latest_common_trade_date(
        self,
        as_of: date,
        *,
        minimum_bars: int = 60,
        minimum_coverage: float = 0.8,
    ) -> date | None:
        """Return the newest date covering the requested share of eligible symbols."""
        if minimum_bars < 1:
            raise ValueError("minimum_bars must be positive")
        if not 0 < minimum_coverage <= 1:
            raise ValueError("minimum_coverage must be between 0 and 1")
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                WITH eligible_symbols AS (
                    SELECT symbol
                    FROM daily_bars
                    WHERE trade_date <= ?
                    GROUP BY symbol
                    HAVING count(DISTINCT trade_date) >= ?
                ), date_counts AS (
                    SELECT b.trade_date, count(DISTINCT b.symbol) AS symbol_count
                    FROM daily_bars b
                    JOIN eligible_symbols e ON e.symbol = b.symbol
                    WHERE b.trade_date <= ?
                    GROUP BY b.trade_date
                ), eligible_count AS (
                    SELECT count(*) AS value FROM eligible_symbols
                )
                SELECT d.trade_date
                FROM date_counts d CROSS JOIN eligible_count e
                WHERE e.value > 0
                  AND CAST(d.symbol_count AS DOUBLE) / e.value >= ?
                ORDER BY d.trade_date DESC
                LIMIT 1
                """,
                [as_of, minimum_bars, as_of, minimum_coverage],
            ).fetchone()
        return row[0] if row and row[0] is not None else None

    def symbols_with_history(
        self, minimum_bars: int, as_of: date, *, cutoff: datetime | None = None,
    ) -> list[str]:
        if minimum_bars < 1:
            raise ValueError("minimum_bars must be positive")
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT symbol
                FROM daily_bars
                WHERE trade_date <= ? AND (? IS NULL OR ingested_at <= ?)
                GROUP BY symbol
                HAVING count(DISTINCT trade_date) >= ?
                ORDER BY symbol
                """,
                [as_of, _database_cutoff(cutoff), _database_cutoff(cutoff), minimum_bars],
            ).fetchall()
        symbols = []
        for row in rows:
            try:
                symbols.append(validate_a_share_code(row[0]))
            except ValueError:
                continue
        return symbols

    def symbols_up_to(
        self, as_of: date, *, cutoff: datetime | None = None,
    ) -> list[str]:
        """Return every valid A-share symbol represented by bars up to a date."""
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT symbol
                FROM daily_bars
                WHERE trade_date <= ? AND (? IS NULL OR ingested_at <= ?)
                ORDER BY symbol
                """,
                [as_of, _database_cutoff(cutoff), _database_cutoff(cutoff)],
            ).fetchall()
        symbols = []
        for row in rows:
            try:
                symbols.append(validate_a_share_code(row[0]))
            except ValueError:
                continue
        return symbols

    def latest_many(
        self,
        symbols: list[str],
        limit: int,
        as_of: date,
        *,
        cutoff: datetime | None = None,
    ) -> dict[str, list[DailyBar]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        validated = [validate_a_share_code(symbol) for symbol in symbols]
        if len(set(validated)) != len(validated):
            raise ValueError("A-share symbols must be unique")
        if not validated:
            return {}
        placeholders = ", ".join("?" for _ in validated)
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                f"""
                WITH latest_by_date AS (
                    SELECT symbol, trade_date, open, high, low, close, volume, amount, source,
                           ROW_NUMBER() OVER (
                               PARTITION BY symbol, trade_date
                               ORDER BY ingested_at DESC, observation_id DESC
                           ) AS revision_rank
                    FROM daily_bars
                    WHERE symbol IN ({placeholders}) AND trade_date <= ?
                        AND (? IS NULL OR ingested_at <= ?)
                ), ranked AS (
                    SELECT symbol, trade_date, open, high, low, close, volume, amount, source,
                           ROW_NUMBER() OVER (
                               PARTITION BY symbol ORDER BY trade_date DESC
                           ) AS date_rank
                    FROM latest_by_date
                    WHERE revision_rank = 1
                )
                SELECT symbol, trade_date, open, high, low, close, volume, amount, source
                FROM ranked
                WHERE date_rank <= ?
                ORDER BY symbol, trade_date
                """,
                [
                    *validated, as_of, _database_cutoff(cutoff),
                    _database_cutoff(cutoff), limit,
                ],
            ).fetchall()
        result = {symbol: [] for symbol in validated}
        for row in rows:
            result[row[0]].append(DailyBar(
                symbol=row[0], trade_date=row[1], open=row[2], high=row[3], low=row[4],
                close=row[5], volume=row[6], amount=row[7], source=row[8],
            ))
        return result

    def export_parquet(self, symbol: str) -> Path:
        if not symbol.isdigit() or len(symbol) != 6:
            raise ValueError("symbol must be six digits")
        path = self.parquet_dir / f"{symbol}.parquet"
        escaped_path = path.as_posix().replace("'", "''")
        with self._lock, self._connect() as connection:
            connection.execute(
                f"""
                COPY (
                    SELECT * FROM daily_bars
                    WHERE symbol = '{symbol}'
                    QUALIFY row_number() OVER (
                        PARTITION BY symbol, trade_date
                        ORDER BY ingested_at DESC, observation_id DESC
                    ) = 1
                    ORDER BY trade_date
                ) TO '{escaped_path}' (FORMAT PARQUET, COMPRESSION ZSTD)
                """
            )
        return path

    def backup_to(self, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("CHECKPOINT")
            finally:
                connection.close()
            shutil.copy2(self.database_path, target_dir / self.database_path.name)
            if self.parquet_dir.is_dir():
                shutil.copytree(
                    self.parquet_dir,
                    target_dir / "parquet" / self.parquet_dir.name,
                    dirs_exist_ok=True,
                )

    def snapshot_database_to(self, target_path: Path) -> Path:
        """Checkpoint and copy only the DuckDB file for a read-only worker."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            connection = self._connect()
            try:
                connection.execute("CHECKPOINT")
            finally:
                connection.close()
            shutil.copy2(self.database_path, target_path)
        return target_path


def _database_cutoff(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("cutoff must include a timezone")
    return value.astimezone(timezone.utc).replace(tzinfo=None)
