#!/usr/bin/env python3
"""
state.py — the ONLY thing that touches Manara's per-project state files.

Plumbing, not brain: deterministic read/write of a project's `.manara/` folder.
The model must CALL this script; it must never edit state.json or session.md by hand.

Files it owns, inside <project>/.manara/:
  - state.json   machine-readable source of truth (this script reads/writes it)
  - session.md   human-readable resume narrative (regenerated from state.json)

Both are kept in sync: every `update` rewrites state.json AND regenerates session.md.

Usage (called by SKILL.md):
  python state.py init   --project <path>
  python state.py read   --project <path>
  python state.py update --project <path> --json '{"stage": "implementation", ...}'
  python state.py update --project <path> --set stage=implementation --done "wrote X" --next "review"

`read` prints a small JSON envelope to stdout:
  {"exists": true|false, "state": {...}, "session_md": "..."}
so the model can branch on cold-start vs resume deterministically.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Template lives next to the skill, two levels up from scripts/ -> skill root.
SKILL_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_ROOT / ".manara-template"

STATE_DIRNAME = ".manara"
STATE_FILE = "state.json"
SESSION_FILE = "session.md"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _state_dir(project: Path) -> Path:
    return project / STATE_DIRNAME


def _state_path(project: Path) -> Path:
    return _state_dir(project) / STATE_FILE


def _session_path(project: Path) -> Path:
    return _state_dir(project) / SESSION_FILE


def _load_state(project: Path) -> dict:
    return json.loads(_state_path(project).read_text(encoding="utf-8"))


def _render_list(items) -> str:
    if not items:
        return "_(none yet)_"
    return "\n".join(f"- {item}" for item in items)


def _render_guards(guards: dict) -> str:
    if not guards:
        return "_(no guards run yet)_"
    lines = []
    for skill, result in guards.items():
        lines.append(f"- **{skill}**: {result}")
    return "\n".join(lines)


def _regenerate_session(project: Path, state: dict) -> None:
    """Render session.md from state.json + the template, keeping the two in sync."""
    template = (TEMPLATE_DIR / SESSION_FILE).read_text(encoding="utf-8")
    rendered = template.format(
        project_name=state.get("project_name") or "(unnamed project)",
        profile=state.get("profile") or "(not set)",
        intent=state.get("intent") or "(not set)",
        stage=state.get("stage") or "(not set)",
        last_decision=state.get("last_decision") or "(none)",
        last_decision_why=state.get("last_decision_why") or "(none)",
        done=_render_list(state.get("done", [])),
        next=_render_list(state.get("next", [])),
        guards=_render_guards(state.get("guards", {})),
        updated_at=state.get("updated_at") or _now(),
        manara_version=state.get("manara_version") or "1.0",
    )
    _session_path(project).write_text(rendered, encoding="utf-8")


def _write_state(project: Path, state: dict) -> None:
    state["updated_at"] = _now()
    _state_path(project).write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _regenerate_session(project, state)


# --- commands ---------------------------------------------------------------

def cmd_init(project: Path) -> dict:
    """Copy .manara-template/ -> <project>/.manara/. Idempotent: never clobbers."""
    dest = _state_dir(project)
    if dest.exists():
        return {"ok": True, "created": False, "note": ".manara/ already exists", "path": str(dest)}

    dest.mkdir(parents=True, exist_ok=False)
    state = json.loads((TEMPLATE_DIR / STATE_FILE).read_text(encoding="utf-8"))
    state["project_name"] = project.name
    state["created_at"] = _now()
    _write_state(project, state)
    return {"ok": True, "created": True, "path": str(dest)}


def cmd_read(project: Path) -> dict:
    """Return existence + parsed state + raw session.md for cold-start branching."""
    sp = _state_path(project)
    if not sp.exists():
        return {"exists": False, "state": None, "session_md": None}
    state = _load_state(project)
    session_md = _session_path(project).read_text(encoding="utf-8")
    return {"exists": True, "state": state, "session_md": session_md}


def _coerce(value: str):
    """Best-effort scalar coercion for --set key=value pairs."""
    lowered = value.lower()
    if lowered in ("true", "false"):
        return lowered == "true"
    return value


def cmd_update(project: Path, json_patch: str | None, sets: list[str],
               adds_done: list[str], adds_next: list[str],
               guard: list[str]) -> dict:
    if not _state_path(project).exists():
        return {"ok": False, "error": ".manara/ not initialized; run `init` first"}

    state = _load_state(project)

    # 1) merge patch (full control: can replace lists/dicts wholesale)
    if json_patch:
        patch = json.loads(json_patch)
        if not isinstance(patch, dict):
            return {"ok": False, "error": "--json must be a JSON object"}
        state.update(patch)

    # 2) scalar sets
    for item in sets:
        if "=" not in item:
            return {"ok": False, "error": f"--set expects key=value, got: {item}"}
        key, _, val = item.partition("=")
        state[key.strip()] = _coerce(val)

    # 3) append to done / next lists
    if adds_done:
        state.setdefault("done", []).extend(adds_done)
    if adds_next:
        state["next"] = list(adds_next)  # next is a forward plan: replace, don't pile up

    # 4) record guard results: --guard "clean-code-guard=pass"
    for g in guard:
        if "=" not in g:
            return {"ok": False, "error": f"--guard expects skill=result, got: {g}"}
        skill, _, result = g.partition("=")
        state.setdefault("guards", {})[skill.strip()] = result.strip()

    _write_state(project, state)
    return {"ok": True, "state": state}


# --- cli --------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="state.py", description="Manara per-project state")
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("init", "read", "update"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True, help="path to the target project root")
        if name == "update":
            p.add_argument("--json", dest="json_patch", default=None,
                           help="JSON object merged into state (replaces lists/dicts wholesale)")
            p.add_argument("--set", dest="sets", action="append", default=[],
                           help="key=value scalar set (repeatable)")
            p.add_argument("--done", dest="adds_done", action="append", default=[],
                           help="append an item to the done list (repeatable)")
            p.add_argument("--next", dest="adds_next", action="append", default=[],
                           help="set the next list (repeatable; replaces the plan)")
            p.add_argument("--guard", dest="guard", action="append", default=[],
                           help="skill=result guard outcome (repeatable)")

    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().resolve()

    if args.cmd == "init":
        result = cmd_init(project)
    elif args.cmd == "read":
        result = cmd_read(project)
    elif args.cmd == "update":
        result = cmd_update(project, args.json_patch, args.sets,
                            args.adds_done, args.adds_next, args.guard)
    else:  # pragma: no cover
        parser.error("unknown command")

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok", True) and result.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
