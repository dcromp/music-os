#!/usr/bin/env bash
# Publish the committed strumalong/ folder to the gh-pages branch (GitHub Pages).
# Deployment stays separate from source pushes: only the tree at HEAD:strumalong is
# published, as a new commit on gh-pages whose message names the source commit.
# Usage: scripts/deploy-strumalong.sh [--dry-run]
set -euo pipefail

ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

if ! git diff --quiet HEAD -- strumalong || [ -n "$(git ls-files --others --exclude-standard strumalong)" ]; then
  echo "strumalong/ has uncommitted changes; commit them first (only committed files are deployed)." >&2
  exit 1
fi

node strumalong/test/run.js
# songs/ must be exactly what the exporter builds from the current packs (fails on stale or extra files).
node strumalong/tools/build-songs.js --check

SOURCE=$(git rev-parse --short HEAD)
TREE=$(git rev-parse "HEAD:strumalong")
PARENT_ARGS=()
if git fetch --quiet origin gh-pages 2>/dev/null; then
  PARENT=$(git rev-parse FETCH_HEAD)
  if [ "$(git rev-parse "$PARENT^{tree}")" = "$TREE" ]; then
    echo "gh-pages already matches strumalong/ at $SOURCE; nothing to deploy."
    exit 0
  fi
  PARENT_ARGS=(-p "$PARENT")
fi

COMMIT=$(git commit-tree "$TREE" ${PARENT_ARGS[@]+"${PARENT_ARGS[@]}"} -m "Deploy strumalong from $SOURCE")
echo "Deploy commit $COMMIT (strumalong/ from $SOURCE)"

if [ "${1:-}" = "--dry-run" ]; then
  echo "Dry run: not pushing."
  exit 0
fi

git push origin "$COMMIT:refs/heads/gh-pages"
echo "Pushed. GitHub Pages: https://dcromp.github.io/music-os/ (allow a minute for the Pages build)."
