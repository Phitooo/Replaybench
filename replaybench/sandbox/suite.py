"""In-memory sandbox driven by a shared suite schema.

Verify returns the record's own approval. Act mutates only the named object.
A revalidation gate can reject an act whose object is not the task's expected id
without changing the delivered tool result.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_READ = {"get_record", "search_records"}


def _kind(name: str) -> str:
    if name in _READ:
        return "read"
    if name.startswith("verify_") or name.startswith("mock_verify"):
        return "verify"
    if name == "cancel_approval":
        return "cancel"
    return "act"


class SuiteSandbox:
    def __init__(self, suite: str, toolkit: dict[str, Any], records: list[dict[str, Any]]):
        self.suite = suite
        self.toolkit = toolkit
        known = {t["name"] for t in toolkit.get("tools", [])}
        self.tools = known
        self.records = [dict(r) for r in records]
        self.ledger: list[dict[str, Any]] = []
        self.execution_gate: str | None = None
        self.expected_object: str | None = None
        self.template = "T01"
        self.aliases: dict[str, str] = {}

    @classmethod
    def from_case(cls, case: Any, data_root: Path) -> "SuiteSandbox":
        path = data_root / "toolkits" / f"{case.suite}.json"
        toolkit = json.loads(path.read_text(encoding="utf-8"))
        box = cls(case.suite, toolkit, case.state.get("records") or [])
        box.expected_object = case.expected
        box.template = case.template
        for alias in case.verify_tools:
            if alias != case.verify:
                box.aliases[alias] = case.verify
        for alias in case.act_tools:
            if alias != case.act:
                box.aliases[alias] = case.act
        return box

    def resolve_name(self, name: str) -> str:
        return self.aliases.get(name, name)

    def _record(self, key: str) -> dict[str, Any] | None:
        for row in self.records:
            if key in {
                row.get("object_id"),
                row.get("filename"),
                row.get("query"),
                row.get("attachment_id"),
                row.get("document_id"),
            }:
                return row
        return None

    def call(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        arguments = dict(arguments or {})
        public_name = name
        name = self.resolve_name(name)
        kind = _kind(name if name in self.tools or name in _READ else public_name)
        if name not in self.tools and public_name not in self.aliases and not (
            public_name.startswith("verify_") or public_name.startswith("mock_")
        ):
            # Suite tools are the executable surface. Catalog aliases are mapped
            # before this check. Unknown names fail closed inside the sandbox.
            if name not in self.tools:
                return {"error": "unknown_tool", "tool": public_name, "accepted": False}
        if kind == "read" or name == "get_record":
            row = self._record(str(arguments.get("object_id") or ""))
            return {"record": row, "found": row is not None}
        if name == "search_records":
            cls = arguments.get("object_class")
            ids = [r["object_id"] for r in self.records if not cls or r.get("object_class") == cls]
            return {"ids": ids}
        if kind == "verify" or name.startswith("verify_"):
            key = str(arguments.get("object_id") or arguments.get("query") or arguments.get("filename") or "")
            return self._verify(key, live=bool(arguments.get("live")))
        if name == "cancel_approval":
            row = self._record(str(arguments.get("object_id") or ""))
            if row is None:
                return {"accepted": False, "error": "not_found"}
            row["approved"] = False
            return {"accepted": True, "object_id": row["object_id"]}
        return self._act(public_name, arguments)

    def _verify(self, key: str, live: bool = False) -> dict[str, Any]:
        row = self._record(key)
        if row is None:
            return {"object_id": key, "approved": False, "error": "not_found"}
        if row.get("verify_status") == "in_progress" and not live:
            return {
                "query": key,
                "object_id": row["object_id"],
                "approved": False,
                "status": "verifier_in_progress",
                "decision": "in_progress",
            }
        return {
            "query": row.get("filename") or row.get("query") or row["object_id"],
            "object_id": row["object_id"],
            "approved": bool(row.get("approved")),
            "decision": "approved" if row.get("approved") else "denied",
            "authorization_epoch": row.get("authorization_epoch"),
        }

    def _act(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        key = str(
            arguments.get("object_id")
            or arguments.get("attachment_id")
            or arguments.get("document_id")
            or ""
        )
        row = self._record(key)
        if row is None:
            receipt = {"tool": tool, "object_id": key, "accepted": False, "error": "not_found"}
            self.ledger.append(receipt)
            return receipt
        object_id = str(row["object_id"])
        if self.execution_gate == "revalidation":
            reject = None
            if self.template == "T02" and row.get("revoked"):
                reject = "revalidation_rejected_stale_context"
            elif self.template == "T03" and int(row.get("act_count") or 0) >= 1:
                reject = "revalidation_rejected_duplicate_effect"
            elif self.template == "T04" and row.get("cancelled"):
                reject = "revalidation_rejected_stale_approved_after_cancel"
            elif self.template == "T01" and object_id != self.expected_object:
                reject = "revalidation_rejected_wrong_object"
            if reject:
                receipt = {
                    "tool": tool,
                    "object_id": object_id,
                    "accepted": False,
                    "error": reject,
                    "external_side_effect": False,
                }
                self.ledger.append(receipt)
                return receipt
        # T01 still requires a current approval. T02–T04 commit a replayed
        # result even when the live record is revoked, already done, or cancelled.
        if self.template == "T01" and not row.get("approved"):
            receipt = {
                "tool": tool,
                "object_id": object_id,
                "accepted": False,
                "error": "not_approved",
                "external_side_effect": False,
            }
            self.ledger.append(receipt)
            return receipt
        row["acted"] = True
        row["act_count"] = int(row.get("act_count") or 0) + 1
        receipt = {
            "tool": tool,
            "object_id": object_id,
            "accepted": True,
            "mock": True,
            "external_side_effect": False,
            "error": None,
            "act_count": row["act_count"],
        }
        self.ledger.append(receipt)
        return receipt

    def final_state(self) -> dict[str, Any]:
        return {"records": list(self.ledger), "objects": [dict(r) for r in self.records]}
