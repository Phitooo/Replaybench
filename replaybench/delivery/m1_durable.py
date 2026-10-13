"""M1: SQLite durable event store.

Public extract of the lab event table. A's tool-result body is appended, then
a recovery consumer reads that same row for B. The body is not rewritten.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from replaybench.delivery.common import TrialMeta, binding_allows, binding_from_meta, now_iso
from replaybench.hashing import sha256_text


class M1Durable:
    name = "M1"
    path_type = "sqlite_durable_event_store"

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                source_task TEXT,
                source_object_id TEXT,
                target_object_id TEXT,
                created_at TEXT,
                response_body TEXT NOT NULL,
                response_body_sha256 TEXT NOT NULL,
                ack_status TEXT DEFAULT 'pending',
                delivery_status TEXT,
                binding_mode TEXT,
                block_reason TEXT
            )
            """
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def publish(self, meta: TrialMeta, body: str) -> str:
        event_id = "evt_" + hashlib.sha256(
            (meta.run_id + meta.source_tool_call_id + body).encode("utf-8")
        ).hexdigest()[:24]
        body_hash = sha256_text(body)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO events (
                event_id, source_task, source_object_id, target_object_id, created_at,
                response_body, response_body_sha256, ack_status, delivery_status, binding_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 'stored', ?)
            """,
            (
                event_id,
                meta.source_task,
                meta.source_object_id,
                None,
                now_iso(),
                body,
                body_hash,
                meta.binding_config,
            ),
        )
        self.conn.commit()
        return event_id

    def deliver(self, meta: TrialMeta, event_id: str, consumer_id: str) -> dict[str, Any]:
        row = self.conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            return {
                "replay_delivery": False,
                "delivery_status": "miss",
                "mechanism": self.name,
                "response_body": None,
                "response_body_sha256": None,
            }
        allowed, check = binding_allows(binding_from_meta(meta), meta.target_tool_call_id)
        if not allowed:
            self.conn.execute(
                "UPDATE events SET delivery_status='blocked', block_reason=?, binding_mode=? WHERE event_id=?",
                (check["reason"], meta.binding_config, event_id),
            )
            self.conn.commit()
            return {
                "replay_delivery": False,
                "delivery_status": "blocked",
                "block_reason": check["reason"],
                "binding_check": check,
                "mechanism": self.name,
                "response_body": None,
                "response_body_sha256": None,
                "event_id": event_id,
            }
        body = str(row["response_body"])
        stored = str(row["response_body_sha256"])
        self.conn.execute(
            """
            UPDATE events
            SET ack_status='acked', delivery_status='delivered', target_object_id=?, binding_mode=?
            WHERE event_id=?
            """,
            (meta.target_object_id, meta.binding_config, event_id),
        )
        self.conn.commit()
        delivered = sha256_text(body)
        return {
            "replay_delivery": True,
            "delivery_status": "delivered",
            "mechanism": self.name,
            "path_type": self.path_type,
            "event_id": event_id,
            "consumer_id": consumer_id,
            "response_body": body,
            "response_body_sha256": delivered,
            "source_result_hash": stored,
            "hash_equal": delivered == stored,
            "binding_check": check,
        }
