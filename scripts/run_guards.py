#!/usr/bin/env python3
"""
run_guards.py — guard-loop bookkeeping (plumbing, not the guard itself).

IMPORTANT DESIGN NOTE
---------------------
The guard *skills* (clean-code-guard, test-guard, docs-guard, wp-guard, woo-guard)
are run by the MODEL via the Skill tool — that is the "brain". This script is the
deterministic PLUMBING around that loop:

  - it records each guard attempt and its result into per-project state,
  - it enforces a hard `max_retries` cap so a failing guard can't loop forever,
  - it returns a clear verdict the model can branch on (continue / blocked / escalate).

It does NOT itself invoke a skill — a Python script cannot call the Skill tool.
The model's loop is:
    1. ask this script `should_run` (have we hit the cap?)
    2. if allowed, run the guard skill, read its pass/fail
    3. report the outcome back here with `record`
    4. repeat while result is "fail" and the cap is not reached

Guards are BLOCKING: a fail does not get waved through. After `max_retries`
consecutive fails, the verdict becomes "escalate" and the flow stops for the user.

Usage:
  py -3 run_guards.py should-run --project <path> --guard clean-code-guard [--max-retries 3]
  py -3 run_guards.py record     --project <path> --guard clean-code-guard --result pass|fail [--detail "..."]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Reuse state.py as the single owner of state files.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import state as state_mod  # noqa: E402

DEFAULT_MAX_RETRIES = 3
ATTEMPTS_KEY = "guard_attempts"  # {guard: int} — consecutive-fail counter


def _load(project: Path) -> dict:
    env = state_mod.cmd_read(project)
    if not env["exists"]:
        raise SystemExit(json.dumps(
            {"ok": False, "error": ".manara/ not initialized; run state.py init first"}))
    return env["state"]


def cmd_should_run(project: Path, guard: str, max_retries: int) -> dict:
    state = _load(project)
    attempts = state.get(ATTEMPTS_KEY, {}).get(guard, 0)
    if attempts >= max_retries:
        return {
            "ok": True,
            "allowed": False,
            "verdict": "escalate",
            "guard": guard,
            "attempts": attempts,
            "max_retries": max_retries,
            "message": (f"Guard '{guard}' has failed {attempts} time(s) "
                        f"(cap {max_retries}). Stop and escalate to the user."),
        }
    return {
        "ok": True,
        "allowed": True,
        "verdict": "run",
        "guard": guard,
        "attempts": attempts,
        "max_retries": max_retries,
    }


def cmd_record(project: Path, guard: str, result: str, detail: str | None,
               max_retries: int) -> dict:
    result = result.lower()
    if result not in ("pass", "fail"):
        return {"ok": False, "error": "--result must be 'pass' or 'fail'"}

    state = _load(project)
    attempts_map = state.get(ATTEMPTS_KEY, {})

    if result == "pass":
        attempts_map[guard] = 0  # reset the consecutive-fail counter
        verdict = "continue"
        message = f"Guard '{guard}' passed. Flow may continue."
    else:
        attempts_map[guard] = attempts_map.get(guard, 0) + 1
        if attempts_map[guard] >= max_retries:
            verdict = "escalate"
            message = (f"Guard '{guard}' failed {attempts_map[guard]} time(s) "
                       f"(cap {max_retries}). BLOCKED — escalate to the user.")
        else:
            verdict = "retry"
            message = (f"Guard '{guard}' failed (attempt {attempts_map[guard]} "
                       f"of {max_retries}). BLOCKED — fix and retry.")

    label = result if not detail else f"{result} ({detail})"
    state_mod.cmd_update(
        project,
        json_patch=json.dumps({ATTEMPTS_KEY: attempts_map}),
        sets=[],
        adds_done=[],
        adds_next=[],
        guard=[f"{guard}={label}"],
    )

    return {
        "ok": True,
        "guard": guard,
        "result": result,
        "verdict": verdict,
        "attempts": attempts_map[guard],
        "max_retries": max_retries,
        "blocking": result == "fail",
        "message": message,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="run_guards.py",
                                     description="Blocking guard-loop bookkeeping")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("should-run", "record"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True)
        p.add_argument("--guard", required=True)
        p.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES)
        if name == "record":
            p.add_argument("--result", required=True, help="pass|fail")
            p.add_argument("--detail", default=None)

    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().resolve()

    if args.cmd == "should-run":
        result = cmd_should_run(project, args.guard, args.max_retries)
    else:
        result = cmd_record(project, args.guard, args.result, args.detail, args.max_retries)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok", False) and result.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
