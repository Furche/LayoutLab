#!/bin/sh
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_SRC="$ROOT/scripts/hooks"
HOOKS_DST="$ROOT/.git/hooks"

if [ ! -d "$ROOT/.git" ]; then
  echo "Not a git repository: $ROOT"
  exit 1
fi

mkdir -p "$HOOKS_DST"

for hook in post-commit; do
  src="$HOOKS_SRC/$hook"
  dst="$HOOKS_DST/$hook"
  if [ ! -f "$src" ]; then
    echo "Missing hook template: $src"
    exit 1
  fi
  cp "$src" "$dst"
  chmod +x "$dst"
  echo "Installed: $dst"
done

echo "Done. Addon zip rebuilds automatically after commits that touch layoutlab/."
