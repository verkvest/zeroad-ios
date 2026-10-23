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

# engine data: config + l10n from git (no LFS), and the engine-level 'mod' mod (GUI, shaders,
# fonts) as the official packed mod.zip from the release data tarball (gitea LFS is too slow).
# bsdtar --fast-read stops right after mod.zip, which precedes the 3.5 GB public.zip.
(
	cd "$Z"
	GIT_LFS_SKIP_SMUDGE=1 git sparse-checkout add binaries/data/config binaries/data/l10n
)
cp -R "$Z/binaries/data/config" "$Z/binaries/data/l10n" "$APP/data/"
DATA_URL="${ZEROAD_DATA_URL:-https://releases.wildfiregames.com/0ad-0.28.0-unix-data.tar.xz}"
mkdir -p "$ROOT/build/data"
if [ ! -f "$ROOT/build/data/mod.zip" ]; then
	# macOS bsdtar decompresses xz itself; -q (fast read) stops after mod.zip, so curl then gets EPIPE (ignored)
	curl -sSL --retry 3 "$DATA_URL" | \
		tar -xJ -q -v -C "$ROOT/build/data" --strip-components 5 -f - "0ad-0.28.0/binaries/data/mods/mod/mod.zip" || true
	ls -la "$ROOT/build/data" || true
fi
[ -s "$ROOT/build/data/mod.zip" ] || { echo "mod.zip download failed"; exit 1; }
mkdir -p "$APP/data/mods/mod"; cp "$ROOT/build/data/mod.zip" "$APP/data/mods/mod/"
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
