"""M3: SQLite checkpoint cache. Write A's result, restore it at B's verify."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from replaybench.delivery.common import TrialMeta, binding_allows, binding_from_meta, now_iso
from replaybench.hashing import sha256_text


class M3Cache:
    name = "M3"
    path_type = "sqlite_cache_checkpoint"

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cache (
                checkpoint_id TEXT PRIMARY KEY,
                body TEXT NOT NULL,
                body_sha256 TEXT NOT NULL,
                source_object_id TEXT,
                written_at TEXT,
                read_count INTEGER DEFAULT 0
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def publish(self, meta: TrialMeta, body: str) -> str:
        checkpoint_id = "ckpt_" + hashlib.sha256(
            (meta.source_run_id + meta.source_tool_call_id + body).encode("utf-8")
        ).hexdigest()[:24]
        self.conn.execute(
            """
            INSERT OR REPLACE INTO cache (checkpoint_id, body, body_sha256, source_object_id, written_at, read_count)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (checkpoint_id, body, sha256_text(body), meta.source_object_id, now_iso()),
        )
        self.conn.commit()
        return checkpoint_id

    def deliver(self, meta: TrialMeta, event_id: str, consumer_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM cache WHERE checkpoint_id = ?", (event_id,)).fetchone()
        if row is None:
            return {"replay_delivery": False, "delivery_status": "miss", "mechanism": self.name, "response_body": None}
        allowed, check = binding_allows(binding_from_meta(meta), meta.target_tool_call_id)
        if not allowed:
            return {
                "replay_delivery": False,
                "delivery_status": "blocked",
                "block_reason": check["reason"],
                "binding_check": check,
                "mechanism": self.name,
                "response_body": None,
                "response_body_sha256": None,
            }
        body = str(row["body"])
        stored = str(row["body_sha256"])
        self.conn.execute(
            "UPDATE cache SET read_count = read_count + 1 WHERE checkpoint_id=?",
            (event_id,),
        )
        self.conn.commit()
        return {
            "replay_delivery": True,
            "delivery_status": "delivered",
            "mechanism": self.name,
            "path_type": self.path_type,
            "event_id": event_id,
            "consumer_id": consumer_id,
            "response_body": body,
            "response_body_sha256": sha256_text(body),
            "source_result_hash": stored,
            "hash_equal": sha256_text(body) == stored,
            "binding_check": check,
        }
