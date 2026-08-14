from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
from pathlib import Path

from pydantic import ValidationError

from qibao_api.contracts.company_research import CompanyResearchAIResult


class CompanyResearchAIResultStoreError(RuntimeError):
    pass


class CompanyResearchAIResultIntegrityError(CompanyResearchAIResultStoreError):
    pass


def _identity_payload(identity: tuple[str, ...]) -> str:
    return json.dumps(identity, ensure_ascii=False, separators=(",", ":"))


def _identity_hash(identity: tuple[str, ...]) -> str:
    return hashlib.sha256(_identity_payload(identity).encode("utf-8")).hexdigest()


class CompanyResearchAIResultRepository:
    def __init__(self, database: str | Path) -> None:
        self._lock = threading.RLock()
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS company_research_ai_results (
          snapshot_id TEXT NOT NULL,
          configuration_hash TEXT NOT NULL,
          configuration_identity TEXT NOT NULL,
          payload TEXT NOT NULL,
          canonical_hash TEXT NOT NULL,
          generated_at TEXT NOT NULL,
          PRIMARY KEY(snapshot_id, configuration_hash)
        );
        """)

    def get(
        self,
        snapshot_id: str,
        configuration_identity: tuple[str, ...],
    ) -> CompanyResearchAIResult | None:
        identity = _identity_payload(configuration_identity)
        try:
            with self._lock:
                row = self.connection.execute(
                    """SELECT * FROM company_research_ai_results
                    WHERE snapshot_id=? AND configuration_hash=?""",
                    (snapshot_id, _identity_hash(configuration_identity)),
                ).fetchone()
                if row is None:
                    return None
                if row["configuration_identity"] != identity:
                    raise CompanyResearchAIResultIntegrityError(
                        "company research AI configuration identity differs"
                    )
                return self._verified(row)
        except CompanyResearchAIResultIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CompanyResearchAIResultStoreError(
                "company research AI result read failed"
            ) from error

    def put(
        self,
        value: CompanyResearchAIResult,
        configuration_identity: tuple[str, ...],
    ) -> CompanyResearchAIResult:
        encoded = value.model_dump_json()
        canonical_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        identity = _identity_payload(configuration_identity)
        try:
            with self._lock, self.connection:
                self.connection.execute(
                    """INSERT INTO company_research_ai_results(
                    snapshot_id,configuration_hash,configuration_identity,payload,
                    canonical_hash,generated_at
                    ) VALUES(?,?,?,?,?,?)
                    ON CONFLICT(snapshot_id,configuration_hash) DO NOTHING""",
                    (
                        value.snapshot_id,
                        _identity_hash(configuration_identity),
                        identity,
                        encoded,
                        canonical_hash,
                        value.generated_at.isoformat(),
                    ),
                )
                row = self.connection.execute(
                    """SELECT * FROM company_research_ai_results
                    WHERE snapshot_id=? AND configuration_hash=?""",
                    (value.snapshot_id, _identity_hash(configuration_identity)),
                ).fetchone()
                if row is None or row["configuration_identity"] != identity:
                    raise CompanyResearchAIResultIntegrityError(
                        "company research AI result identity differs"
                    )
                return self._verified(row)
        except CompanyResearchAIResultIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CompanyResearchAIResultStoreError(
                "company research AI result write failed"
            ) from error

    @staticmethod
    def _verified(row: sqlite3.Row) -> CompanyResearchAIResult:
        actual_hash = hashlib.sha256(row["payload"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual_hash, row["canonical_hash"]):
            raise CompanyResearchAIResultIntegrityError(
                "company research AI result failed integrity check"
            )
        value = CompanyResearchAIResult.model_validate_json(row["payload"])
        if value.snapshot_id != row["snapshot_id"]:
            raise CompanyResearchAIResultIntegrityError(
                "company research AI result snapshot differs"
            )
        return value

    def close(self) -> None:
        with self._lock:
            self.connection.close()
