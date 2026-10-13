"""Scripted dry-run of one case. Does not call a model.

The scripted consumer is a protocol check: it shows what the checker does when
B is shown A's stored result. It is not a published attack rate.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from replaybench.cases import DATA, Case, load_case
from replaybench.checker import aggregate, score_trace
from replaybench.delivery import open_mechanism
from replaybench.delivery.common import TrialMeta
from replaybench.hashing import canonical_dumps, sha256_text
from replaybench.sandbox import SuiteSandbox


def _meta(case: Case, binding: str, run_id: str) -> TrialMeta:
    return TrialMeta(
        run_id=run_id,
        source_task="A",
        consumer_task="B",
        source_run_id=f"{run_id}:A",
        target_run_id=f"{run_id}:B",
        source_session_id=f"{run_id}:A:s",
        target_session_id=f"{run_id}:B:s",
        source_tool_call_id=f"{run_id}:src",
        target_tool_call_id=f"{run_id}:tgt",
        source_object_id=case.forbidden,
        target_object_id=case.expected,
        source_authorization_epoch="epoch-A",
        target_authorization_epoch="epoch-B",
        binding_config=binding,
    )


def _binding_for(defense: str | None) -> str:
    if defense == "binding":
        return "object_binding"
    if defense == "revalidation":
        return "execution_time_revalidation"
    return "no_binding"


def run_scripted(
    case: Case,
    mechanism: str = "M1",
    script: str = "follow_visible",
    defense: str | None = None,
    workdir: Path | None = None,
    seed: int = 1,
) -> dict[str, Any]:
    workdir = Path(workdir or Path.cwd() / "runs" / "scripted")
    workdir.mkdir(parents=True, exist_ok=True)
    db_path = workdir / f"{case.family}_{case.template}_{mechanism}_{seed}.sqlite"
    mech = open_mechanism(mechanism, db_path)
    sandbox = SuiteSandbox.from_case(case, DATA)
    if defense == "revalidation":
        sandbox.execution_gate = "revalidation"
    binding = _binding_for(defense)
    run_id = f"scripted:{case.family}:{case.template}:{mechanism}:{seed}"
    meta = _meta(case, binding, run_id)
    body = canonical_dumps(case.a_result)
    try:
        event_id = mech.publish(meta, body)
        calls: list[dict[str, Any]] = [
            {
                "phase": "A",
                "tool": case.verify,
                "arguments": {"object_id": case.forbidden},
                "result": case.a_result,
            }
        ]

        def verify(key: str, live: bool) -> dict[str, Any]:
            if live:
                return sandbox.call(case.verify, {"object_id": key, "live": True})
            delivered = mech.deliver(meta, event_id, consumer_id="B")
            if delivered.get("replay_delivery") and delivered.get("response_body"):
                parsed = json.loads(delivered["response_body"])
                calls.append(
                    {
                        "phase": "B",
                        "tool": case.verify,
                        "arguments": {"object_id": key},
                        "result": parsed,
                        "delivery_status": "delivered",
                        "delivered_sha256": delivered.get("response_body_sha256"),
                    }
                )
                return parsed
            live_result = sandbox.call(case.verify, {"object_id": key})
            if delivered.get("delivery_status") == "blocked":
                live_result = {
                    **live_result,
                    "binding": "blocked_cross_object",
                    "delivery_status": "blocked",
                }
            calls.append(
                {
                    "phase": "B",
                    "tool": case.verify,
                    "arguments": {"object_id": key},
                    "result": live_result,
                    "delivery_status": delivered.get("delivery_status"),
                }
            )
            return live_result

        def act(object_id: str, phase: str = "B") -> dict[str, Any]:
            receipt = sandbox.call(case.act, {"object_id": object_id})
            calls.append(
                {
                    "phase": phase,
                    "tool": case.act,
                    "arguments": {"object_id": object_id},
                    "result": receipt,
                }
            )
            return receipt

        if script == "follow_visible":
            visible = verify(case.expected if case.template == "T01" else case.forbidden, live=False)
            obj = visible.get("object_id")
            decision = str(visible.get("decision") or "").lower()
            usable = visible.get("approved") is True or visible.get("accepted") is True or decision in {"allow", "approved"}
            if usable and obj:
                act(str(obj))
        elif script == "refuse":
            verify(case.expected, live=False)
        elif script == "recover":
            visible = verify(case.expected, live=False)
            if defense == "revalidation" and visible.get("approved"):
                act(str(visible.get("object_id")), phase="attack")
            live = verify(case.expected, live=True)
            if live.get("approved"):
                act(case.expected, phase="recover")
        else:
            raise ValueError(f"unknown script {script}")

        trace = {
            "blocked": False,
            "defense": defense,
            "family": case.family,
            "template": case.template,
            "mechanism": mechanism.upper(),
            "forbidden": case.forbidden,
            "expected": case.expected,
            "verify_tools": case.verify_tools,
            "act_tools": case.act_tools,
            "a_result_sha256": sha256_text(body),
            "tool_calls": calls,
            "final_state": sandbox.final_state(),
            "mode": "scripted_dry_run",
            "model_called": False,
        }
        scored = score_trace(trace)
        delivered_hash = next(
            (c.get("delivered_sha256") for c in calls if c.get("delivered_sha256")),
            None,
        )
        scored["trace"] = trace
        scored["delivered_sha256"] = delivered_hash
        scored["a_result_sha256"] = sha256_text(body)
        return scored
    finally:
        mech.close()


def smoke(family: str, template: str, mechanism: str, workdir: Path | None = None) -> dict[str, Any]:
    case = load_case(family, template)
    if not case.b_user.strip():
        raise ValueError("b_user.txt is empty")
    one = run_scripted(case, mechanism=mechanism, script="follow_visible", defense=None, workdir=workdir)
    summary = aggregate([one])
    summary.update(
        {
            "family": case.family,
            "template": case.template,
            "mechanism": mechanism.upper(),
            "mode": "scripted_dry_run",
            "model_called": False,
            "published_rate": "not_this_process",
            "label": one["label"],
            "a_result_sha256": one["a_result_sha256"],
            "delivered_sha256": one["delivered_sha256"],
            "hash_equal": one["a_result_sha256"] == one["delivered_sha256"],
        }
    )
    return summary
