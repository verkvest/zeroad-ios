#!/bin/bash
# Fetches the pinned 0 A.D. engine sources (code only, no art) into build/0ad.
# Usage: scripts/fetch-0ad.sh [extra sparse paths...]
#   e.g. scripts/fetch-0ad.sh binaries/data/mods/mod   (minimal data mod)
set -eo pipefail
ZEROAD_TAG="${ZEROAD_TAG:-v0.28.0}"
ZEROAD_COMMIT="${ZEROAD_COMMIT:-a2cae4d69f816e9e9d7eecb6bf88f762afc0c90d}"
ZEROAD_URL="${ZEROAD_URL:-https://gitea.wildfiregames.com/0ad/0ad.git}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/build/0ad"
if [ ! -d "$DEST/.git" ]; then
	GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch "$ZEROAD_TAG" --filter=blob:none --sparse "$ZEROAD_URL" "$DEST"
fi
cd "$DEST"
git sparse-checkout set source libraries build "$@"
test "$(git rev-parse HEAD)" = "$ZEROAD_COMMIT" || { echo "Unexpected 0 A.D. commit $(git rev-parse HEAD)"; exit 1; }
echo "0 A.D. $ZEROAD_TAG ($ZEROAD_COMMIT) in $DEST"
