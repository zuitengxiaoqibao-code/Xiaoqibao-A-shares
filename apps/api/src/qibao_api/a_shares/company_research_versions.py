from __future__ import annotations

import hashlib
import hmac
import json
import sqlite3
import threading
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from qibao_api.contracts.company_research import (
    CompanyResearchResponse,
    CompanyResearchVersion,
    CompanyResearchVersionChange,
)


class CompanyResearchVersionStoreError(RuntimeError):
    pass


class CompanyResearchVersionIntegrityError(CompanyResearchVersionStoreError):
    pass


def _semantic_payload(
    value: CompanyResearchResponse,
    *,
    retain_legacy_provenance: bool = False,
) -> dict:
    payload = value.model_dump(
        mode="json",
        exclude={"generated_at", "research_version", "conclusions"},
    )

    def strip_timestamps(item, *, in_evidence_ledger: bool = False):
        if isinstance(item, dict):
            return {
                key: strip_timestamps(child, in_evidence_ledger=in_evidence_ledger or key == "evidence_ledger")
                for key, child in item.items()
                if key not in {"observed_at", "generated_at", "fetched_at", "normalized_at"}
                and not (in_evidence_ledger and key in {"total_count", "coverage_percent"})
                and (retain_legacy_provenance or key not in {"change_type", "evidence_ids"})
            }
        if isinstance(item, list):
            return [strip_timestamps(child, in_evidence_ledger=in_evidence_ledger) for child in item]
        return item

    return strip_timestamps(payload)


def _encoded_semantics(
    value: CompanyResearchResponse,
    *,
    retain_legacy_provenance: bool = False,
) -> str:
    return json.dumps(
        _semantic_payload(
            value,
            retain_legacy_provenance=retain_legacy_provenance,
        ),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _display(value) -> str | None:
    if value is None:
        return None
    return str(value)


def _changes(
    previous: CompanyResearchResponse | None,
    current: CompanyResearchResponse,
) -> tuple[CompanyResearchVersionChange, ...]:
    if previous is None:
        return ()
    changes: list[CompanyResearchVersionChange] = []
    previous_sections = {item.key: item for item in previous.research_sections}
    for item in current.research_sections:
        before = previous_sections.get(item.key)
        before_text = None if before is None else f"{before.status} · {before.summary}"
        after_text = f"{item.status} · {item.summary}"
        if before_text != after_text or (before is not None and before.facts != item.facts):
            if before is None:
                change_type = "new"
            elif before.status != item.status:
                rank = {"unavailable": 0, "partial": 1, "clear": 2, "triggered": 2, "ready": 3}
                change_type = "strengthened" if rank.get(item.status, 0) > rank.get(before.status, 0) else "weakened"
            elif len(item.facts) > len(before.facts):
                change_type = "strengthened"
            elif len(item.facts) < len(before.facts):
                change_type = "weakened"
            else:
                change_type = "updated"
            changes.append(CompanyResearchVersionChange(
                category="conclusion", label=item.label,
                before=before_text, after=after_text,
                change_type=change_type,
                evidence_ids=tuple(dict.fromkeys(item.evidence_ids)),
            ))
    data_fields = (
        ("研究截止日", previous.as_of, current.as_of),
        ("证据覆盖率", previous.evidence_coverage, current.evidence_coverage),
        ("最终评分", previous.final_score, current.final_score),
        ("PE(TTM)", previous.valuation.pe_ttm, current.valuation.pe_ttm),
        ("PB", previous.valuation.pb, current.valuation.pb),
        ("前向PE", previous.valuation.forward_pe, current.valuation.forward_pe),
    )
    for label, before, after in data_fields:
        if before != after:
            changes.append(CompanyResearchVersionChange(
                category="data", label=label,
                before=_display(before), after=_display(after),
                change_type="updated",
            ))
    previous_sources = {(item.source, item.label, item.status) for item in previous.sources}
    current_sources = {(item.source, item.label, item.status) for item in current.sources}
    if previous_sources != current_sources:
        changes.append(CompanyResearchVersionChange(
            category="source", label="来源集合",
            before="；".join(" / ".join(item) for item in sorted(previous_sources)) or "无",
            after="；".join(" / ".join(item) for item in sorted(current_sources)) or "无",
            change_type="updated",
        ))
    return tuple(changes)


class CompanyResearchVersionRepository:
    def __init__(self, database: str | Path, *, shared_snapshot_registry=None) -> None:
        self._lock = threading.RLock()
        self.shared_snapshot_registry = shared_snapshot_registry
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript("""
        CREATE TABLE IF NOT EXISTS company_research_versions (
          sequence INTEGER PRIMARY KEY AUTOINCREMENT,
          snapshot_id TEXT NOT NULL UNIQUE,
          symbol TEXT NOT NULL,
          version_number INTEGER NOT NULL,
          content_hash TEXT NOT NULL,
          canonical_hash TEXT NOT NULL,
          payload TEXT NOT NULL,
          generated_at TEXT NOT NULL,
          UNIQUE(symbol, version_number),
          UNIQUE(symbol, content_hash)
        );
        CREATE INDEX IF NOT EXISTS ix_company_research_versions_symbol
        ON company_research_versions(symbol, version_number DESC);
        CREATE TRIGGER IF NOT EXISTS reject_update_company_research_versions
        BEFORE UPDATE ON company_research_versions
        BEGIN SELECT RAISE(ABORT, 'append-only company research versions'); END;
        CREATE TRIGGER IF NOT EXISTS reject_delete_company_research_versions
        BEFORE DELETE ON company_research_versions
        BEGIN SELECT RAISE(ABORT, 'append-only company research versions'); END;
        """)

    def append(self, value: CompanyResearchResponse) -> CompanyResearchResponse:
        content_hash = hashlib.sha256(_encoded_semantics(value).encode("utf-8")).hexdigest()
        try:
            with self._lock:
                existing = self.connection.execute(
                    "SELECT * FROM company_research_versions WHERE symbol=? AND content_hash=?",
                    (value.symbol, content_hash),
                ).fetchone()
                if existing is not None:
                    stored = self._verified(existing)
                    self._record_shared_snapshot(stored, reused=True)
                    return stored
                previous_row = self.connection.execute(
                    "SELECT * FROM company_research_versions WHERE symbol=? ORDER BY version_number DESC LIMIT 1",
                    (value.symbol,),
                ).fetchone()
                previous = self._verified(previous_row) if previous_row is not None else None
                version_number = 1 if previous is None or previous.research_version is None else previous.research_version.version_number + 1
                snapshot_id = f"company-research-{value.symbol}-{uuid4().hex}"
                version = CompanyResearchVersion(
                    snapshot_id=snapshot_id,
                    version_number=version_number,
                    previous_snapshot_id=previous.research_version.snapshot_id if previous is not None and previous.research_version is not None else None,
                    content_hash=content_hash,
                    generated_at=value.generated_at,
                    changes=_changes(previous, value),
                )
                stored = value.model_copy(update={"research_version": version})
                encoded = stored.model_dump_json()
                canonical_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
                with self.connection:
                    self.connection.execute(
                        """INSERT INTO company_research_versions(
                        snapshot_id,symbol,version_number,content_hash,canonical_hash,payload,generated_at
                        ) VALUES(?,?,?,?,?,?,?)""",
                        (snapshot_id, value.symbol, version_number, content_hash, canonical_hash, encoded, value.generated_at.isoformat()),
                    )
                self._record_shared_snapshot(stored, reused=False)
                return stored
        except CompanyResearchVersionIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CompanyResearchVersionStoreError("company research version append failed") from error

    def _record_shared_snapshot(
        self, value: CompanyResearchResponse, *, reused: bool
    ) -> None:
        registry = self.shared_snapshot_registry
        version = value.research_version
        if registry is None or version is None:
            return
        try:
            registry.record(
                "financial_valuation",
                content_hash=version.content_hash,
                trade_date=value.as_of,
                observed_at=value.generated_at,
                coverage_percent=float(value.evidence_coverage * 100),
                freshness="frozen",
                source="company-research-version",
                reused=reused,
                latency_ms=0,
            )
        except Exception:
            return

    def history(self, symbol: str, *, limit: int = 20) -> tuple[CompanyResearchResponse, ...]:
        try:
            with self._lock:
                rows = self.connection.execute(
                    "SELECT * FROM company_research_versions WHERE symbol=? ORDER BY version_number DESC LIMIT ?",
                    (symbol, limit),
                ).fetchall()
                return tuple(self._verified(row) for row in rows)
        except CompanyResearchVersionIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CompanyResearchVersionStoreError("company research version read failed") from error

    def latest(self, symbol: str) -> CompanyResearchResponse | None:
        history = self.history(symbol, limit=1)
        return history[0] if history else None

    def get(self, snapshot_id: str) -> CompanyResearchResponse | None:
        try:
            with self._lock:
                row = self.connection.execute(
                    "SELECT * FROM company_research_versions WHERE snapshot_id=?",
                    (snapshot_id,),
                ).fetchone()
                return self._verified(row) if row is not None else None
        except CompanyResearchVersionIntegrityError:
            raise
        except (sqlite3.DatabaseError, ValidationError, ValueError) as error:
            raise CompanyResearchVersionStoreError("company research version lookup failed") from error

    def verify_all(self) -> int:
        with self._lock:
            rows = self.connection.execute("SELECT * FROM company_research_versions ORDER BY sequence").fetchall()
            for row in rows:
                self._verified(row)
            return len(rows)

    @staticmethod
    def _verified(row: sqlite3.Row) -> CompanyResearchResponse:
        canonical_hash = hashlib.sha256(row["payload"].encode("utf-8")).hexdigest()
        if not hmac.compare_digest(canonical_hash, row["canonical_hash"]):
            raise CompanyResearchVersionIntegrityError("company research version failed integrity check")
        value = CompanyResearchResponse.model_validate_json(row["payload"])
        version = value.research_version
        if version is None or version.snapshot_id != row["snapshot_id"] or version.content_hash != row["content_hash"]:
            raise CompanyResearchVersionIntegrityError("company research version identity differs")
        semantic_hash = hashlib.sha256(_encoded_semantics(value).encode("utf-8")).hexdigest()
        legacy_semantic_hash = hashlib.sha256(
            _encoded_semantics(value, retain_legacy_provenance=True).encode("utf-8")
        ).hexdigest()
        if not any(
            hmac.compare_digest(candidate, version.content_hash)
            for candidate in (semantic_hash, legacy_semantic_hash)
        ):
            raise CompanyResearchVersionIntegrityError("company research semantic content differs")
        return value

    def close(self) -> None:
        with self._lock:
            self.connection.close()
