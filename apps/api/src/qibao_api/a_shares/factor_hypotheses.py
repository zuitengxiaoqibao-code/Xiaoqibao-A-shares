from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Mapping, Set

from qibao_api.contracts.quant_research import (
    FactorHypothesisCreate,
    FactorHypothesisRecord,
    FactorHypothesisValidation,
)


REQUIRED_CHECKS = ("point_in_time", "walk_forward", "transaction_cost", "fdr")


def hypothesis_id(hypothesis: FactorHypothesisCreate) -> str:
    canonical = json.dumps(
        hypothesis.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"hypothesis-{hashlib.sha256(canonical).hexdigest()[:24]}"


def validate_hypothesis_contract(
    hypothesis: FactorHypothesisCreate,
    *,
    available_fields: Set[str],
    checks: Mapping[str, bool | None],
    validated_at: datetime,
) -> FactorHypothesisValidation:
    missing_fields = tuple(sorted(set(hypothesis.required_fields) - available_fields))
    check_states = {
        key: "unavailable" if checks.get(key) is None else (
            "passed" if checks.get(key) else "failed"
        )
        for key in REQUIRED_CHECKS
    }
    reasons: list[str] = []
    if missing_fields:
        status = "insufficient"
        reasons.append("缺少验证所需字段：" + "、".join(missing_fields))
    elif any(value == "unavailable" for value in check_states.values()):
        status = "insufficient"
        reasons.append("部分确定性检查暂不可用")
    elif all(value == "passed" for value in check_states.values()):
        status = "accepted"
        reasons.append("PIT、样本外、成本和 FDR 检查全部通过")
    else:
        status = "rejected"
        reasons.append("至少一项确定性检查未通过")
    return FactorHypothesisValidation(
        hypothesis_id=hypothesis_id(hypothesis),
        status=status,
        checks=check_states,
        missing_fields=missing_fields,
        validated_at=validated_at,
        reasons=tuple(reasons),
    )


class FactorHypothesisStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS factor_hypotheses (
                    hypothesis_id TEXT PRIMARY KEY,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS factor_hypothesis_validations (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    hypothesis_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    validated_at TEXT NOT NULL,
                    FOREIGN KEY(hypothesis_id) REFERENCES factor_hypotheses(hypothesis_id)
                );
                CREATE TRIGGER IF NOT EXISTS reject_update_factor_hypotheses
                BEFORE UPDATE ON factor_hypotheses
                BEGIN SELECT RAISE(ABORT, 'append-only factor hypotheses'); END;
                CREATE TRIGGER IF NOT EXISTS reject_delete_factor_hypotheses
                BEFORE DELETE ON factor_hypotheses
                BEGIN SELECT RAISE(ABORT, 'append-only factor hypotheses'); END;
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def append(self, hypothesis: FactorHypothesisCreate) -> FactorHypothesisRecord:
        item_id = hypothesis_id(hypothesis)
        payload = json.dumps(
            hypothesis.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")
        )
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO factor_hypotheses VALUES (?, ?, ?)",
                (item_id, payload, hypothesis.generated_at.isoformat()),
            )
        return self.get(item_id)

    def append_validation(
        self,
        item_id: str,
        validation: FactorHypothesisValidation,
    ) -> None:
        if validation.hypothesis_id != item_id:
            raise ValueError("validation hypothesis id mismatch")
        with self._connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM factor_hypotheses WHERE hypothesis_id=?", (item_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(item_id)
            connection.execute(
                """INSERT INTO factor_hypothesis_validations
                (hypothesis_id, payload_json, validated_at) VALUES (?, ?, ?)""",
                (
                    item_id,
                    json.dumps(
                        validation.model_dump(mode="json"),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    validation.validated_at.isoformat(),
                ),
            )

    def validations(self, item_id: str) -> tuple[FactorHypothesisValidation, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT payload_json FROM factor_hypothesis_validations
                WHERE hypothesis_id=? ORDER BY sequence""",
                (item_id,),
            ).fetchall()
        return tuple(
            FactorHypothesisValidation.model_validate_json(row["payload_json"])
            for row in rows
        )

    def get(self, item_id: str) -> FactorHypothesisRecord:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM factor_hypotheses WHERE hypothesis_id=?",
                (item_id,),
            ).fetchone()
        if row is None:
            raise KeyError(item_id)
        hypothesis = FactorHypothesisCreate.model_validate_json(row["payload_json"])
        validations = self.validations(item_id)
        latest = validations[-1] if validations else None
        return FactorHypothesisRecord(
            hypothesis_id=item_id,
            statement=hypothesis.statement,
            expected_direction=hypothesis.expected_direction,
            status=latest.status if latest is not None else "draft",
            generated_at=hypothesis.generated_at,
            input_evidence_hash=hypothesis.input_evidence_hash,
            required_fields=hypothesis.required_fields,
            success_metric=hypothesis.success_metric,
            success_threshold=hypothesis.success_threshold,
            validation=latest,
        )
