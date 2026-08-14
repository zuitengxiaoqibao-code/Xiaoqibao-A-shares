import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from threading import RLock

from qibao_api.contracts.market import AssetKind
from qibao_api.contracts.risk import AuditFinding
from qibao_api.dongchang.schema import SCHEMA
from qibao_api.dongchang.models import AuditInput, Snapshot


@dataclass(frozen=True)
class StoredSnapshot:
    snapshot: Snapshot
    content_hash: str


class AuditFindingRepository:
    def __init__(self, database: str | Path) -> None:
        self._lock = RLock()
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        with self._lock:
            self.connection.close()

    def append_audit(
        self, audit_input: AuditInput, findings: tuple[AuditFinding, ...]
    ) -> None:
        snapshot_ids = {audit_input.recommendation.snapshot_id, audit_input.outcome.snapshot_id}
        if any(
            finding.asset != audit_input.asset
            or set(finding.input_snapshot_ids) != snapshot_ids
            for finding in findings
        ):
            raise ValueError("findings must match current audit snapshots and asset")
        try:
            with self._lock, self.connection:
                for snapshot in (audit_input.recommendation, audit_input.outcome):
                    self.connection.execute(
                        """INSERT INTO audit_snapshots
                           (snapshot_id, asset, symbol, conclusion, evidence_link,
                            captured_at, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            snapshot.snapshot_id,
                            snapshot.asset.value,
                            snapshot.symbol,
                            snapshot.conclusion,
                            snapshot.evidence_link,
                            snapshot.captured_at.isoformat(),
                            snapshot.canonical_content_hash(),
                        ),
                    )
                for finding in findings:
                    self._append_finding(finding)
                    self.connection.executemany(
                        """INSERT INTO audit_finding_snapshots
                           (finding_id, snapshot_id, position) VALUES (?, ?, ?)""",
                        [
                            (finding.finding_id, snapshot_id, position)
                            for position, snapshot_id in enumerate(finding.input_snapshot_ids)
                        ],
                    )
                if audit_input.source_observations:
                    self.connection.executemany(
                        """INSERT INTO audit_source_observations(
                           audit_run_id, asset, symbol, as_of, field, value, source, evidence_link
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        [
                            (
                                audit_input.audit_run_id,
                                item.asset.value,
                                item.symbol,
                                item.as_of.isoformat(),
                                item.field,
                                item.value,
                                item.source,
                                item.evidence_link,
                            )
                            for item in audit_input.source_observations
                        ],
                    )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"audit run {audit_input.audit_run_id!r} already exists") from error

    def append_source_observations(self, audit_input: AuditInput) -> None:
        """Persist raw source candidates as immutable, local diagnostic rows."""
        if not audit_input.source_observations:
            return
        with self._lock, self.connection:
            self.connection.executemany(
                """INSERT INTO audit_source_observations(
                   audit_run_id, asset, symbol, as_of, field, value, source, evidence_link
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        audit_input.audit_run_id,
                        item.asset.value,
                        item.symbol,
                        item.as_of.isoformat(),
                        item.field,
                        item.value,
                        item.source,
                        item.evidence_link,
                    )
                    for item in audit_input.source_observations
                ],
            )

    def source_conflict_summary(
        self, *, asset: AssetKind | str, symbol: str | None = None, field: str | None = None,
    ) -> dict:
        """Return a redacted, deterministic view of conflicting field candidates."""
        asset = AssetKind(asset)
        clauses = ["asset = ?"]
        params: list[object] = [asset.value]
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol)
        if field:
            clauses.append("field = ?")
            params.append(field)
        query = "SELECT * FROM audit_source_observations WHERE " + " AND ".join(clauses)
        query += " ORDER BY symbol, field, as_of, sequence"
        with self._lock:
            rows = self.connection.execute(query, params).fetchall()
        grouped: dict[tuple[str, str, str], list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault((row["symbol"], row["field"], row["as_of"]), []).append(row)
        conflicts: list[dict] = []
        priority = {"local-tdx": 0, "tdx": 0, "mootdx": 0, "tencent": 1, "eastmoney": 2, "baidu": 3}
        for (group_symbol, group_field, as_of), candidates in sorted(grouped.items()):
            values = {row["value"] for row in candidates}
            if len(values) <= 1:
                continue
            ordered = sorted(candidates, key=lambda row: (priority.get(row["source"], 99), row["source"], row["sequence"]))
            selected = ordered[0]
            conflicts.append({
                "symbol": group_symbol,
                "field": group_field,
                "as_of": as_of,
                "candidate_sources": sorted({row["source"] for row in candidates}),
                "selected_source": selected["source"],
                "selection_reason": "source_priority_then_freshness",
                "candidate_count": len(candidates),
                "affects_conclusion": True,
                "candidates": [
                    {
                        "source": row["source"],
                        "value": row["value"],
                        "observed_at": row["as_of"],
                        "evidence_link": row["evidence_link"],
                    }
                    for row in ordered
                ],
            })
        return {"state": "ready", "conflict_count": len(conflicts), "conflicts": conflicts}

    def _append_finding(self, finding: AuditFinding) -> None:
        values = (
            finding.finding_id,
            finding.asset.value,
            finding.finding_type,
            finding.severity,
            json.dumps(finding.evidence, ensure_ascii=True),
            json.dumps(finding.input_snapshot_ids, ensure_ascii=True),
            finding.owner_department,
            finding.resolution_state,
            finding.detected_at.isoformat(),
        )
        self.connection.execute(
            """INSERT INTO audit_findings
               (finding_id, asset, finding_type, severity, evidence_json,
                input_snapshot_ids_json, owner_department, resolution_state, detected_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )

    def get_snapshot(self, snapshot_id: str) -> StoredSnapshot:
        with self._lock:
            row = self.connection.execute(
                "SELECT * FROM audit_snapshots WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        return StoredSnapshot(
            snapshot=Snapshot(
                snapshot_id=row["snapshot_id"],
                asset=row["asset"],
                symbol=row["symbol"],
                conclusion=row["conclusion"],
                evidence_link=row["evidence_link"],
                captured_at=row["captured_at"],
            ),
            content_hash=row["content_hash"],
        )

    def list_findings(self, *, asset: AssetKind | str) -> list[AuditFinding]:
        asset = AssetKind(asset)
        with self._lock:
            rows = self.connection.execute(
                """SELECT * FROM audit_findings WHERE asset = ?
                   ORDER BY detected_at, sequence""",
                (asset.value,),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    @staticmethod
    def _from_row(row: sqlite3.Row) -> AuditFinding:
        return AuditFinding(
            finding_id=row["finding_id"],
            asset=row["asset"],
            finding_type=row["finding_type"],
            severity=row["severity"],
            evidence=tuple(json.loads(row["evidence_json"])),
            input_snapshot_ids=tuple(json.loads(row["input_snapshot_ids_json"])),
            owner_department=row["owner_department"],
            resolution_state=row["resolution_state"],
            detected_at=row["detected_at"],
        )
