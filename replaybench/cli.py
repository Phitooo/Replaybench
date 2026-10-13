"""Command line. `smoke` never calls a model. `run` does, via LlamaIndex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from replaybench.checker import format_rate, score_trace


def _print_summary(summary: dict) -> None:
    fields = (
        ("mode", summary.get("mode")),
        ("model_called", summary.get("model_called")),
        ("published_rate", summary.get("published_rate")),
        ("family", summary.get("family")),
        ("template", summary.get("template")),
        ("mechanism", summary.get("mechanism")),
        ("n_attempted", summary.get("n_attempted")),
        ("n_valid", summary.get("n_valid")),
        ("n_blocked", summary.get("n_blocked")),
        ("DAR", format_rate(summary.get("DAR"))),
        ("WAR", format_rate(summary.get("WAR"))),
        ("AAR", format_rate(summary.get("AAR"))),
        ("FSER", format_rate(summary.get("FSER"))),
        ("FR", format_rate(summary.get("FR"))),
        ("Recov", format_rate(summary.get("Recov"))),
        ("label", summary.get("label")),
        ("hash_equal", summary.get("hash_equal")),
    )
    for key, value in fields:
        print(f"{key}={value}")


def _cmd_smoke(args: argparse.Namespace) -> int:
    from replaybench.protocol import smoke

    summary = smoke(args.family, args.template, args.mech)
    _print_summary(summary)
    return 0


def _cmd_score(args: argparse.Namespace) -> int:
    trace = json.loads(Path(args.trace).read_text(encoding="utf-8"))
    scored = score_trace(trace)
    for key in ("blocked", "n_valid", "n_blocked", "DAR", "WAR", "AAR", "FSER", "FR", "Recov", "label"):
        value = scored.get(key)
        if key in {"DAR", "WAR", "AAR", "FSER", "FR", "Recov"}:
            value = format_rate(value) if not isinstance(value, str) else value
        print(f"{key}={value}")
    return 0 if not scored.get("blocked") or args.allow_blocked else 0


def _cmd_run(args: argparse.Namespace) -> int:
    from replaybench.adapters.llamaindex import run_cell

    summary = run_cell(
        family=args.family,
        template=args.template,
        mechanism=args.mech,
        n=args.n,
        defense=args.defense,
    )
    _print_summary(summary)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="replaybench")
    sub = parser.add_subparsers(dest="cmd", required=True)

    smoke = sub.add_parser("smoke", help="scripted dry-run, no model call")
    smoke.add_argument("--family", required=True)
    smoke.add_argument("--template", default="T01")
    smoke.add_argument("--mech", default="M1")
    smoke.set_defaults(func=_cmd_smoke)

    run = sub.add_parser("run", help="LlamaIndex cell. Requires OPENAI_API_KEY and REPLAYBENCH_MODEL")
    run.add_argument("--family", required=True)
    run.add_argument("--template", default="T01")
    run.add_argument("--mech", default="M1")
    run.add_argument("--n", type=int, default=1)
    run.add_argument("--defense", default=None, choices=["binding", "revalidation"])
    run.set_defaults(func=_cmd_run)

    score = sub.add_parser("score", help="score one trace file; no model call")
    score.add_argument("--trace", required=True)
    score.add_argument("--allow-blocked", action="store_true")
    score.set_defaults(func=_cmd_score)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"error={type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
