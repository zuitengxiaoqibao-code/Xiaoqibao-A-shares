import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from qibao_api.contracts.instruments import AShareCode
from qibao_api.contracts.industry import ShenwanIndustry
from qibao_api.contracts.market import AssetKind
from qibao_api.gongbu.tencent_quotes import market_prefix


NON_EQUITY_IDENTIFIERS = frozenset({"000300"})


class AShareInstrument(BaseModel):
    model_config = ConfigDict(frozen=True)

    symbol: AShareCode
    name: str = Field(min_length=1)
    exchange: Literal["sh", "sz", "bj"]
    observed_at: AwareDatetime
    quote_quality: Literal["ready", "stale", "unavailable"]
    short_name: str | None = None
    historical_names: tuple[str, ...] = ()
    search_aliases: tuple[str, ...] = ()
    industry: str | None = None
    shenwan_industry: ShenwanIndustry | None = None
    sectors: tuple[str, ...] = ()
    trading_status: Literal["active", "suspended", "delisted", "unknown"] = "unknown"

    @field_validator("observed_at")
    @classmethod
    def normalize_observed_at(cls, value: datetime) -> datetime:
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def exchange_matches_symbol(self) -> "AShareInstrument":
        if self.symbol in NON_EQUITY_IDENTIFIERS:
            raise ValueError("symbol must identify an A-share equity, not an index")
        if self.exchange != market_prefix(self.symbol):
            raise ValueError("exchange must match A-share symbol")
        return self


class AShareInstrumentDirectory:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS a_share_instrument_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                exchange TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                quote_quality TEXT NOT NULL,
                short_name TEXT,
                historical_names TEXT NOT NULL DEFAULT '[]',
                search_aliases TEXT NOT NULL DEFAULT '[]',
                industry TEXT,
                shenwan_industry TEXT,
                sectors TEXT NOT NULL DEFAULT '[]',
                trading_status TEXT NOT NULL DEFAULT 'unknown'
            )
            """
        )
        self._connection.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_a_share_instrument_latest
            ON a_share_instrument_observations(symbol, observed_at DESC, id DESC)
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS a_share_active_universe (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                exchange TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                quote_quality TEXT NOT NULL,
                short_name TEXT,
                historical_names TEXT NOT NULL DEFAULT '[]',
                search_aliases TEXT NOT NULL DEFAULT '[]',
                industry TEXT,
                shenwan_industry TEXT,
                sectors TEXT NOT NULL DEFAULT '[]',
                trading_status TEXT NOT NULL DEFAULT 'unknown'
            )
            """
        )
        self._migrate_metadata_columns("a_share_instrument_observations")
        self._migrate_metadata_columns("a_share_active_universe")
        self._connection.commit()

    def _migrate_metadata_columns(self, table: str) -> None:
        existing = {
            row[1] for row in self._connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        definitions = {
            "short_name": "TEXT",
            "historical_names": "TEXT NOT NULL DEFAULT '[]'",
            "search_aliases": "TEXT NOT NULL DEFAULT '[]'",
            "industry": "TEXT",
            "shenwan_industry": "TEXT",
            "sectors": "TEXT NOT NULL DEFAULT '[]'",
            "trading_status": "TEXT NOT NULL DEFAULT 'unknown'",
        }
        for name, definition in definitions.items():
            if name not in existing:
                self._connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    @staticmethod
    def _metadata(instrument: AShareInstrument) -> tuple[object, ...]:
        return (
            instrument.short_name,
            json.dumps(instrument.historical_names, ensure_ascii=False),
            json.dumps(instrument.search_aliases, ensure_ascii=False),
            instrument.industry,
            json.dumps(
                instrument.shenwan_industry.model_dump(mode="json"),
                ensure_ascii=False,
            ) if instrument.shenwan_industry is not None else None,
            json.dumps(instrument.sectors, ensure_ascii=False),
            instrument.trading_status,
        )

    def observe(self, instrument: AShareInstrument) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO a_share_instrument_observations
                    (symbol, name, exchange, observed_at, quote_quality, short_name,
                     historical_names, search_aliases, industry, shenwan_industry,
                     sectors, trading_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    instrument.symbol,
                    instrument.name,
                    instrument.exchange,
                    instrument.observed_at.isoformat(),
                    instrument.quote_quality,
                    *self._metadata(instrument),
                ),
            )
            self._connection.commit()

    def observe_many(self, instruments: tuple[AShareInstrument, ...] | list[AShareInstrument]) -> None:
        active_instruments = {instrument.symbol: instrument for instrument in instruments}
        with self._lock:
            self._connection.executemany(
                """
                INSERT INTO a_share_instrument_observations
                    (symbol, name, exchange, observed_at, quote_quality, short_name,
                     historical_names, search_aliases, industry, shenwan_industry,
                     sectors, trading_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        instrument.symbol,
                        instrument.name,
                        instrument.exchange,
                        instrument.observed_at.isoformat(),
                        instrument.quote_quality,
                        *self._metadata(instrument),
                    )
                    for instrument in instruments
                ],
            )
            self._connection.execute("DELETE FROM a_share_active_universe")
            self._connection.executemany(
                """
                INSERT INTO a_share_active_universe
                    (symbol, name, exchange, observed_at, quote_quality, short_name,
                     historical_names, search_aliases, industry, shenwan_industry,
                     sectors, trading_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        instrument.symbol,
                        instrument.name,
                        instrument.exchange,
                        instrument.observed_at.isoformat(),
                        instrument.quote_quality,
                        *self._metadata(instrument),
                    )
                    for instrument in active_instruments.values()
                ],
            )
            self._connection.commit()

    def resolve(self, symbol: str) -> AShareInstrument | None:
        active = self._active(symbol)
        if active is not None:
            return active
        return self.resolve_at(symbol, None)

    def resolve_at(
        self, symbol: str, cutoff: datetime | None
    ) -> AShareInstrument | None:
        normalized_cutoff = cutoff.astimezone(timezone.utc).isoformat() if cutoff else None
        with self._lock:
            row = self._connection.execute(
                """
                SELECT symbol, name, exchange, observed_at, quote_quality, short_name,
                       historical_names, search_aliases, industry, shenwan_industry,
                       sectors, trading_status
                FROM a_share_instrument_observations
                WHERE symbol = ? AND (? IS NULL OR observed_at <= ?)
                ORDER BY observed_at DESC, id DESC
                LIMIT 1
                """,
                (symbol, normalized_cutoff, normalized_cutoff),
            ).fetchone()
        return self._instrument(row) if row is not None else None

    def search(self, query: str, limit: int = 10) -> tuple[AShareInstrument, ...]:
        normalized = query.strip().casefold()
        if not normalized:
            raise ValueError("query must not be empty")
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = self._active_rows() if self._active_count() else self._all_rows()
        def terms(item: AShareInstrument) -> tuple[str, ...]:
            return (
                item.symbol, item.name, item.short_name or "", *item.historical_names,
                *item.search_aliases,
            )

        matches = [
            item for item in rows
            if any(normalized in value.casefold() for value in terms(item) if value)
        ]
        return tuple(
            sorted(
                matches,
                key=lambda item: (
                    item.symbol != normalized,
                    item.name.casefold() != normalized,
                    not item.name.casefold().startswith(normalized),
                    item.symbol,
                ),
            )[:limit]
        )

    def snapshot(self) -> tuple[AShareInstrument, ...]:
        """Return the current local read model without invoking any network source."""
        return self._active_rows() if self._active_count() else self._all_rows()

    def latest_observed_at(self) -> datetime | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT MAX(observed_at) FROM a_share_instrument_observations"
            ).fetchone()
        return datetime.fromisoformat(row[0]) if row and row[0] else None

    def latest_named_observed_at(self) -> datetime | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT MAX(observed_at) FROM a_share_instrument_observations WHERE name <> symbol"
            ).fetchone()
        return datetime.fromisoformat(row[0]) if row and row[0] else None

    def active_symbols(self) -> tuple[str, ...]:
        return tuple(item.symbol for item in self._active_rows())

    def alias_map(self) -> dict[tuple[AssetKind, str], tuple[str, ...]]:
        rows = self._active_rows() if self._active_count() else self._all_rows()
        return {
            (AssetKind.A_SHARE, item.symbol): (item.name.strip(),)
            for item in rows
            if item.name.strip() and item.name.strip() != item.symbol
        }

    def named_count(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(DISTINCT symbol) FROM a_share_instrument_observations WHERE name <> symbol"
            ).fetchone()
        return int(row[0] or 0)

    def _all_rows(self) -> tuple[AShareInstrument, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT symbol, name, exchange, observed_at, quote_quality, short_name,
                       historical_names, search_aliases, industry, shenwan_industry,
                       sectors, trading_status
                FROM (
                    SELECT *, row_number() OVER (
                        PARTITION BY symbol ORDER BY observed_at DESC, id DESC
                    ) AS row_number
                    FROM a_share_instrument_observations
                ) latest
                WHERE row_number = 1
                """
            ).fetchall()
        return tuple(self._instrument(row) for row in rows)

    def _active_count(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) FROM a_share_active_universe"
            ).fetchone()
        return int(row[0] or 0)

    def _active_rows(self) -> tuple[AShareInstrument, ...]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT symbol, name, exchange, observed_at, quote_quality, short_name,
                       historical_names, search_aliases, industry, shenwan_industry,
                       sectors, trading_status
                FROM a_share_active_universe ORDER BY symbol
                """
            ).fetchall()
        return tuple(self._instrument(row) for row in rows)

    def _active(self, symbol: str) -> AShareInstrument | None:
        with self._lock:
            row = self._connection.execute(
                """
                SELECT symbol, name, exchange, observed_at, quote_quality, short_name,
                       historical_names, search_aliases, industry, shenwan_industry,
                       sectors, trading_status
                FROM a_share_active_universe WHERE symbol = ?
                """,
                (symbol,),
            ).fetchone()
        return self._instrument(row) if row is not None else None

    @staticmethod
    def _instrument(row) -> AShareInstrument:
        return AShareInstrument(
            symbol=row[0],
            name=row[1],
            exchange=row[2],
            observed_at=datetime.fromisoformat(row[3]),
            quote_quality=row[4],
            short_name=row[5],
            historical_names=tuple(json.loads(row[6] or "[]")),
            search_aliases=tuple(json.loads(row[7] or "[]")),
            industry=row[8],
            shenwan_industry=(
                ShenwanIndustry.model_validate(json.loads(row[9]))
                if row[9] else None
            ),
            sectors=tuple(json.loads(row[10] or "[]")),
            trading_status=row[11] or "unknown",
        )

    def close(self) -> None:
        with self._lock:
            self._connection.close()
