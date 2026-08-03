import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from qibao_api.convertible_bonds.models import BondUniverseItem, BondUniverseSnapshot


class BondUniverseRepository:
    def __init__(self, database: str | Path) -> None:
        self.connection = sqlite3.connect(database, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS bond_universe_snapshots (
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              snapshot_id TEXT NOT NULL UNIQUE,
              source TEXT NOT NULL,
              observed_at TEXT NOT NULL,
              raw_identity TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bond_universe_items (
              snapshot_id TEXT NOT NULL,
              bond_code TEXT NOT NULL,
              payload TEXT NOT NULL,
              PRIMARY KEY (snapshot_id, bond_code),
              FOREIGN KEY(snapshot_id) REFERENCES bond_universe_snapshots(snapshot_id)
            );
            CREATE TRIGGER IF NOT EXISTS reject_update_bond_universe_snapshots
            BEFORE UPDATE ON bond_universe_snapshots
            BEGIN SELECT RAISE(ABORT, 'append-only bond universe snapshots'); END;
            CREATE TRIGGER IF NOT EXISTS reject_delete_bond_universe_snapshots
            BEFORE DELETE ON bond_universe_snapshots
            BEGIN SELECT RAISE(ABORT, 'append-only bond universe snapshots'); END;
            CREATE TRIGGER IF NOT EXISTS reject_update_bond_universe_items
            BEFORE UPDATE ON bond_universe_items
            BEGIN SELECT RAISE(ABORT, 'append-only bond universe items'); END;
            CREATE TRIGGER IF NOT EXISTS reject_delete_bond_universe_items
            BEFORE DELETE ON bond_universe_items
            BEGIN SELECT RAISE(ABORT, 'append-only bond universe items'); END;
            """
        )

    def append(self, snapshot: BondUniverseSnapshot) -> str:
        snapshot_id = f"bond-universe-{uuid4().hex}"
        observed_at = snapshot.observed_at.astimezone(timezone.utc).isoformat()
        with self.connection:
            self.connection.execute(
                "INSERT INTO bond_universe_snapshots(snapshot_id,source,observed_at,raw_identity) VALUES(?,?,?,?)",
                (snapshot_id, snapshot.source, observed_at, snapshot.raw_identity),
            )
            self.connection.executemany(
                "INSERT INTO bond_universe_items(snapshot_id,bond_code,payload) VALUES(?,?,?)",
                [
                    (
                        snapshot_id,
                        item.bond_code,
                        json.dumps(item.model_dump(mode="json"), ensure_ascii=False, sort_keys=True),
                    )
                    for item in snapshot.items
                ],
            )
        return snapshot_id

    def latest(self) -> BondUniverseSnapshot | None:
        row = self.connection.execute(
            "SELECT * FROM bond_universe_snapshots ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        items = self.connection.execute(
            "SELECT payload FROM bond_universe_items WHERE snapshot_id=? ORDER BY bond_code",
            (row["snapshot_id"],),
        ).fetchall()
        return BondUniverseSnapshot(
            observed_at=datetime.fromisoformat(row["observed_at"]),
            source=row["source"],
            raw_identity=row["raw_identity"],
            items=tuple(BondUniverseItem.model_validate(json.loads(item["payload"])) for item in items),
        )

    def close(self) -> None:
        self.connection.close()
