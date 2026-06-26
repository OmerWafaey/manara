#!/usr/bin/env bash
# Manara installer for macOS / Linux.
# Clones (or updates) Manara into your Claude Code user-skills folder so it's
# available in every project. Safe to re-run — it updates an existing install.
set -euo pipefail

REPO="https://github.com/OmerWafaey/manara.git"
DEST="$HOME/.claude/skills/manara"

echo "Manara installer"
echo "  target: $DEST"

# Need git.
if ! command -v git >/dev/null 2>&1; then
  echo "Error: git is not installed. Please install git and re-run." >&2
  exit 1
fi

mkdir -p "$HOME/.claude/skills"

if [ -d "$DEST/.git" ]; then
  echo "Already installed — pulling the latest version..."
  git -C "$DEST" pull --ff-only
else
  if [ -e "$DEST" ]; then
    echo "Error: $DEST exists but is not a git clone. Move or remove it, then re-run." >&2
    exit 1
  fi
  echo "Cloning Manara..."
  git clone --depth 1 "$REPO" "$DEST"
fi

echo
echo "Done. Manara is installed at: $DEST"
echo "Next: cd into any project and run  /manara  inside Claude Code."
echo "(Python 3.7+ is required for the state/guard scripts — standard library only.)"
