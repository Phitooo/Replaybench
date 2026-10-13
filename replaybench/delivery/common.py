"""Shared trial metadata and binding checks for M1/M2/M3.

Binding here is a delivery gate. Execution-time revalidation does not block
delivery; the sandbox act gate does.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TrialMeta:
    run_id: str
    source_task: str
    consumer_task: str
    source_run_id: str
    target_run_id: str
    source_session_id: str
    target_session_id: str
    source_tool_call_id: str
    target_tool_call_id: str
    source_object_id: str
    target_object_id: str
    source_authorization_epoch: str
    target_authorization_epoch: str
    binding_config: str = "no_binding"
    replay_mode: str = "explicit_recipient"


def binding_allows(binding: dict[str, Any], tool_call_id: str | None) -> tuple[bool, dict[str, Any]]:
    mode = str(binding.get("mode") or "no_binding")
    source_object = str(binding.get("source_object_id"))
    target_object = str(binding.get("target_object_id"))
    comparisons = {
        "object": source_object == target_object,
        "task": str(binding.get("source_task_id")) == str(binding.get("target_task_id")),
        "run": str(binding.get("source_run_id")) == str(binding.get("target_run_id")),
        "authorization_epoch": str(binding.get("source_authorization_epoch"))
        == str(binding.get("target_authorization_epoch")),
        "session": str(binding.get("source_session_id")) == str(binding.get("target_session_id")),
        "tool_call": str(binding.get("source_tool_call_id"))
        == (str(tool_call_id) if tool_call_id is not None else str(binding.get("target_tool_call_id"))),
    }
    if mode in ("no_binding", "weak_binding", "replay"):
        allowed, reason = True, "no_binding_allows_cross_task_delivery"
    elif mode in ("object_binding", "binding", "binding_defense"):
        allowed, reason = comparisons["object"], "object_binding"
    elif mode in ("execution_time_revalidation", "revalidation", "replay_revalidation"):
        allowed, reason = True, "execution_time_revalidation_does_not_block_delivery"
    elif mode == "task_binding":
        allowed, reason = comparisons["task"], "task_binding"
    elif mode == "session_binding":
        allowed, reason = comparisons["session"], "session_binding"
    else:
        allowed, reason = False, f"unsupported_binding:{mode}"
    check = {
        "event": "binding_check",
        "mode": mode,
        "comparisons_equal": comparisons,
        "gate_result": "allow" if allowed else "block",
        "reason": reason if allowed else f"{reason}_mismatch",
    }
    return allowed, check


def binding_from_meta(meta: TrialMeta) -> dict[str, Any]:
    return {
        "mode": meta.binding_config,
        "source_task_id": meta.source_task,
        "target_task_id": meta.consumer_task,
        "source_run_id": meta.source_run_id,
        "target_run_id": meta.target_run_id,
        "source_session_id": meta.source_session_id,
        "target_session_id": meta.target_session_id,
        "source_tool_call_id": meta.source_tool_call_id,
        "target_tool_call_id": meta.target_tool_call_id,
        "source_object_id": meta.source_object_id,
        "target_object_id": meta.target_object_id,
        "source_authorization_epoch": meta.source_authorization_epoch,
        "target_authorization_epoch": meta.target_authorization_epoch,
    }
