#!/usr/bin/env python3
"""
archive.py — v1 STUB. Snapshot the Manara skill folder before any self-modification.

WHY THIS EXISTS NOW (but does nothing yet)
------------------------------------------
Self-modification is a DEFERRED feature (v2/v3): Manara editing its own SKILL.md,
scripts, or references. When that lands, the contract is: *never* mutate Manara's
own folder without first taking a restorable snapshot, and self-modification only
ever happens AFTER the report and WITH explicit user approval — never mid-task.

We fix the interface now so v2 can rely on it. v1 must NOT call this to actually
archive anything; v1 does not self-modify.

Interface (frozen for v2):
  snapshot(skill_root: Path, reason: str) -> Path   # returns the snapshot location
  restore(snapshot_path: Path, skill_root: Path)    # roll back to a snapshot

Usage (stub):
  py -3 archive.py snapshot --reason "about to edit routing.md"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent


def snapshot(skill_root: Path, reason: str) -> dict:
    # TODO(v2): copy skill_root (excluding .git and existing snapshots) into
    # skill_root/.manara-snapshots/<timestamp>/ and return the path. Use shutil.copytree.
    # Guard: refuse to run mid-task; require an explicit post-report approval flag.
    return {
        "ok": True,
        "stub": True,
        "would_snapshot": str(skill_root),
        "reason": reason,
        "note": "archive.py is a v1 STUB — self-modification is deferred to v2. No files were copied.",
    }


def restore(snapshot_path: Path, skill_root: Path) -> dict:
    # TODO(v2): replace skill_root contents from snapshot_path atomically.
    raise NotImplementedError("restore() is reserved for v2 self-modification support.")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="archive.py",
                                     description="(v1 stub) snapshot Manara before self-change")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("snapshot")
    p.add_argument("--reason", required=True)

    args = parser.parse_args(argv)
    result = snapshot(SKILL_ROOT, args.reason)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
