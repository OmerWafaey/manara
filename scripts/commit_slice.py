#!/usr/bin/env python3
"""
commit_slice.py — git mechanics for auto-committing a verified slice (plumbing).

IMPORTANT DESIGN NOTE
---------------------
This is PLUMBING, not brain. It performs the deterministic git work — staging the
right files, listing what would be committed, creating a local commit — but it does
NOT decide *when* to commit. That judgment lives in SKILL.md (the brain):

    a commit happens only after BOTH
      - the slice's blocking guards passed, AND
      - the user explicitly verified/approved the slice.

This script never makes that call for you. It also never pushes to a remote, never
rebases/squashes/rewrites history, and never `git init`s silently — initializing a
repo is a separate, explicit command the user has to approve.

Two hard safety rules enforced here (not left to the model):
  1. `.manara/` (Manara's per-project session state) is ALWAYS excluded from staging,
     regardless of whether the project's .gitignore lists it.
  2. The project's existing .gitignore is respected (native `git add` behavior).

Usage:
  py -3 commit_slice.py check     --project <path>
  py -3 commit_slice.py init-repo --project <path>
  py -3 commit_slice.py commit    --project <path> --message "Slice A — blur strength (blur-only)"

Every command prints a JSON envelope to stdout so the model can branch deterministically.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

STATE_DIRNAME = ".manara"

# Pathspecs that exclude Manara's own state from any staging operation.
# `:(exclude).manara` covers the entry; the glob covers everything beneath it.
EXCLUDE_PATHSPECS = [":(exclude).manara", ":(exclude).manara/**"]


def _git(project: Path, *args: str) -> subprocess.CompletedProcess:
    """Run a git command inside the project. Never touches any remote."""
    return subprocess.run(
        ["git", "-C", str(project), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _is_git_repo(project: Path) -> bool:
    proc = _git(project, "rev-parse", "--is-inside-work-tree")
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _porcelain_entries(project: Path) -> list[dict]:
    """Parse `git status --porcelain` into {status, path} entries (relative paths)."""
    proc = _git(project, "status", "--porcelain")
    entries: list[dict] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        path = line[3:].strip()
        # Renames look like "old -> new"; keep the new path.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        # Strip optional surrounding quotes git adds for unusual filenames.
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        entries.append({"status": status, "path": path})
    return entries


def _is_under_manara(path: str) -> bool:
    norm = path.replace("\\", "/")
    return norm == STATE_DIRNAME or norm.startswith(STATE_DIRNAME + "/")


def _committable(entries: list[dict]) -> list[dict]:
    """Changed/untracked entries, with anything under .manara/ filtered out."""
    return [e for e in entries if not _is_under_manara(e["path"])]


# --- commands ---------------------------------------------------------------

def cmd_check(project: Path) -> dict:
    """Read-only: report repo status + what a commit would include. Stages nothing."""
    if not _is_git_repo(project):
        return {
            "ok": True,
            "is_git_repo": False,
            "message": (
                "This project has no git repo yet. Ask the user before initializing "
                "one — do NOT init silently."
            ),
        }

    entries = _porcelain_entries(project)
    committable = _committable(entries)
    excluded = [e for e in entries if _is_under_manara(e["path"])]

    return {
        "ok": True,
        "is_git_repo": True,
        "manara_excluded": True,
        "nothing_to_commit": len(committable) == 0,
        "files": [e["path"] for e in committable],
        "files_detail": committable,
        "excluded_manara_files": [e["path"] for e in excluded],
        "message": (
            "Nothing to commit (after excluding .manara/)."
            if not committable
            else f"{len(committable)} file(s) would be committed; .manara/ excluded."
        ),
    }


def cmd_init_repo(project: Path) -> dict:
    """Explicit `git init` — only ever run after the user approves. Never automatic."""
    if _is_git_repo(project):
        return {"ok": True, "initialized": False, "note": "already a git repo"}

    proc = _git(project, "init")
    if proc.returncode != 0:
        return {"ok": False, "error": f"git init failed: {proc.stderr.strip()}"}
    return {
        "ok": True,
        "initialized": True,
        "message": "Initialized empty git repo. Source can now be checkpointed.",
    }


def cmd_commit(project: Path, message: str) -> dict:
    """Stage source (excluding .manara/), verify, and create a LOCAL commit."""
    if not _is_git_repo(project):
        return {
            "ok": False,
            "is_git_repo": False,
            "error": "Not a git repo. Run `init-repo` first (after user approval).",
        }

    if not message or not message.strip():
        return {"ok": False, "error": "--message is required and must be non-empty"}

    # 1) Stage everything except .manara/ (respects the project's .gitignore natively).
    add = _git(project, "add", "-A", "--", ".", *EXCLUDE_PATHSPECS)
    if add.returncode != 0:
        return {"ok": False, "error": f"git add failed: {add.stderr.strip()}"}

    # 2) Defense in depth: unstage anything under .manara/ that slipped through.
    _git(project, "reset", "-q", "--", STATE_DIRNAME)

    # 3) Inspect the staged set.
    staged = _git(project, "diff", "--cached", "--name-only")
    staged_files = [p.strip() for p in staged.stdout.splitlines() if p.strip()]

    leaked = [p for p in staged_files if _is_under_manara(p)]
    if leaked:
        # Should never happen given the exclusions, but never commit state by accident.
        _git(project, "reset", "-q", "--", STATE_DIRNAME)
        return {
            "ok": False,
            "error": f".manara/ files were staged and have been unstaged: {leaked}. "
                     "Re-run after confirming exclusion.",
        }

    if not staged_files:
        return {
            "ok": True,
            "committed": False,
            "nothing_to_commit": True,
            "message": "Nothing staged to commit (after excluding .manara/).",
        }

    # 4) Local commit only — no remote is ever contacted.
    commit = _git(project, "commit", "-m", message)
    if commit.returncode != 0:
        return {"ok": False, "error": f"git commit failed: {commit.stderr.strip()}"}

    rev = _git(project, "rev-parse", "--short", "HEAD")
    return {
        "ok": True,
        "committed": True,
        "commit": rev.stdout.strip(),
        "files": staged_files,
        "commit_message": message,
        "pushed": False,
        "message": f"Committed {len(staged_files)} file(s) locally as {rev.stdout.strip()}. "
                   "Not pushed — pushing is the user's manual action.",
    }


# --- cli --------------------------------------------------------------------

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="commit_slice.py",
        description="Auto-commit a verified slice (local only, .manara/ excluded).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    for name in ("check", "init-repo", "commit"):
        p = sub.add_parser(name)
        p.add_argument("--project", required=True, help="path to the target project root")
        if name == "commit":
            p.add_argument("--message", required=True,
                           help="commit message (plain-language slice summary)")

    args = parser.parse_args(argv)
    project = Path(args.project).expanduser().resolve()

    if args.cmd == "check":
        result = cmd_check(project)
    elif args.cmd == "init-repo":
        result = cmd_init_repo(project)
    else:
        result = cmd_commit(project, args.message)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result.get("ok", False) and result.get("error") is None else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
