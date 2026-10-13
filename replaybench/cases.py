"""Load packaged cases. F01–F19 × T01–T04 are runnable. Mechanisms share a case."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from replaybench.hashing import sha256_obj

PKG = Path(__file__).resolve().parent
DATA = PKG / "data"
CASES = PKG / "cases"

FAMILIES = [f"F{i:02d}" for i in range(1, 20)]


class CaseNotRunnable(FileNotFoundError):
    pass


@dataclass
class Case:
    family: str
    template: str
    status: str
    suite: str
    forbidden: str
    expected: str
    verify: str
    act: str
    verify_tools: list[str]
    act_tools: list[str]
    b_user: str
    state: dict[str, Any]
    a_result: dict[str, Any]
    a_result_sha256: str
    spec: dict[str, Any]
    root: Path


def family_spec(family: str) -> dict[str, Any]:
    path = DATA / "families" / f"{family}.json"
    if not path.exists():
        raise FileNotFoundError(f"unknown family {family}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_case(family: str, template: str = "T01") -> Case:
    family = family.upper()
    template = template.upper()
    root = CASES / family / template
    spec_path = root / "spec.json"
    if not spec_path.exists():
        raise CaseNotRunnable(f"{family}/{template} has no case package")
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if spec.get("status") != "runnable":
        raise CaseNotRunnable(f"{family}/{template} is not runnable ({spec.get('status')})")
    state = json.loads((root / "state.json").read_text(encoding="utf-8"))
    a_result = json.loads((root / "a_result.json").read_text(encoding="utf-8"))
    b_user = (root / "b_user.txt").read_text(encoding="utf-8")
    digest = sha256_obj(a_result)
    declared = spec.get("a_result_sha256")
    if declared and declared != digest:
        raise ValueError(f"{family}/{template} a_result_sha256 does not match a_result.json")
    verify_tools = list(dict.fromkeys([spec["verify"], *spec.get("verify_aliases", [])]))
    act_tools = list(dict.fromkeys([spec["act"], *spec.get("act_aliases", [])]))
    return Case(
        family=family,
        template=template,
        status="runnable",
        suite=spec["suite"],
        forbidden=spec["forbidden"],
        expected=spec["expected"],
        verify=spec["verify"],
        act=spec["act"],
        verify_tools=verify_tools,
        act_tools=act_tools,
        b_user=b_user,
        state=state,
        a_result=a_result,
        a_result_sha256=digest,
        spec=spec,
        root=root,
    )
