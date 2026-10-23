#!/bin/bash
# Wraps the cross-compiled pyrogenesis binary into an iOS .app with the small
# engine-only "mod" data mod (no game art) so it can be launched in the Simulator.
# Usage: PLATFORM=iphonesimulator scripts/package-engine-app.sh <out-dir>
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="${1:-$ROOT/out}"
Z="$ROOT/build/0ad"
BIN="$(find "$Z/binaries/system" -maxdepth 1 -name 'pyrogenesis*' -type f | head -1)"
[ -n "$BIN" ] || { echo "pyrogenesis not linked"; exit 1; }
APP="$ROOT/build/Pyrogenesis.app"
rm -rf "$APP"; mkdir -p "$APP/data/mods" "$OUTDIR"

# engine data: config, l10n and the engine-level 'mod' mod (GUI, shaders, fonts), with its LFS files
(
	cd "$Z"
	git sparse-checkout add binaries/data/config binaries/data/l10n binaries/data/mods/mod
	git lfs install --local >/dev/null 2>&1 || true
	git lfs pull --include="binaries/data/mods/mod/**,binaries/data/l10n/**,binaries/data/config/**" || echo "WARNING: git lfs pull failed"
)
cp -R "$Z/binaries/data/config" "$Z/binaries/data/l10n" "$APP/data/"
cp -R "$Z/binaries/data/mods/mod" "$APP/data/mods/"
du -sh "$APP/data"

cp "$BIN" "$APP/pyrogenesis"
sed -e 's/${MACOSX_BUNDLE_EXECUTABLE_NAME}/pyrogenesis/' \
    -e 's/${MACOSX_BUNDLE_GUI_IDENTIFIER}/es.verkvest.zeroad/' \
    -e 's/${MACOSX_BUNDLE_BUNDLE_NAME}/0 A.D./' \
    -e 's/${MACOSX_BUNDLE_SHORT_VERSION_STRING}/0.1.0/' \
    -e 's/${MACOSX_BUNDLE_BUNDLE_VERSION}/1/' \
    -e 's/0 A.D. Touch/0 A.D./' \
    "$ROOT/touchdemo/Info.plist.in" > "$APP/Info.plist"
plutil -lint "$APP/Info.plist"
codesign --force --sign - "$APP"
ls -la "$APP"; file "$APP/pyrogenesis"
ditto -c -k --keepParent "$APP" "$OUTDIR/Pyrogenesis-$PLATFORM.app.zip"
