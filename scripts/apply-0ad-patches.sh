#!/bin/bash
# Applies the iOS port changes on top of the pinned 0 A.D. sources in build/0ad.
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/build/0ad"
git checkout -q -- source build 2>/dev/null || true
git clean -fdq -- source
# Shared, engine-independent gesture recognizer (also used by the touch demo app).
{ echo '#include "precompiled.h"'; echo; cat "$ROOT/touch/TouchGestures.cpp"; } > source/ps/TouchGestures.cpp
cp "$ROOT/touch/TouchGestures.h" source/ps/TouchGestures.h
# iOS-only extra sources (each must start with the precompiled header).
for f in "$ROOT"/ios/src/*.cpp; do
	{ echo '#include "precompiled.h"'; echo; cat "$f"; } > "source/ps/$(basename "$f")"
done
for p in "$ROOT"/patches/0ad/*.patch; do
	echo "Applying $(basename "$p")"
	git apply --whitespace=nowarn "$p"
done
git status --short
