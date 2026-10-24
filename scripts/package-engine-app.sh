#!/bin/bash
# Wraps the cross-compiled pyrogenesis binary into an iOS .app with the small
# official game data (engine "mod" + mobile-repacked "public") so the full game runs.
# Usage: PLATFORM=iphonesimulator scripts/package-engine-app.sh <out-dir>
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTDIR="${1:-$ROOT/out}"
Z="$ROOT/build/0ad"
BIN="$(find "$Z/binaries/system" -maxdepth 1 -name 'pyrogenesis*' -type f | head -1)"
[ -n "$BIN" ] || { echo "pyrogenesis not linked"; exit 1; }
APP="$ROOT/build/Pyrogenesis.app"
rm -rf "$APP"; mkdir -p "$APP/data/mods" "$OUTDIR"
# copy the binary first: 'git sparse-checkout add' below prunes untracked files outside the cone (binaries/system)
cp "$BIN" "$APP/pyrogenesis"

# engine data: config + l10n from git (no LFS); game data from the repo's "mobile-data" release:
#   mod.zip           official engine mod (GUI, shaders, fonts), unmodified from 0ad-0.28.0-unix-data.tar.xz
#   public-mobile.zip official 'public' mod repacked for phones by scripts/pack-mobile-data.py
(
	cd "$Z"
	GIT_LFS_SKIP_SMUDGE=1 git sparse-checkout add binaries/data/config binaries/data/l10n
)
cp -R "$Z/binaries/data/config" "$Z/binaries/data/l10n" "$APP/data/"
python3 "$ROOT/ios/ios-config.py" "$APP/data/config/default.cfg"
DATA_REL="${ZEROAD_DATA_RELEASE:-https://github.com/verkvest/zeroad-ios/releases/download/mobile-data-0.28.0-v1}"
D="$ROOT/build/data"; mkdir -p "$D"
for f in mod.zip public-mobile.zip SHA256SUMS; do
	[ -s "$D/$f" ] || curl -fsSL --retry 5 -o "$D/$f" "$DATA_REL/$f"
done
(cd "$D" && shasum -a 256 -c SHA256SUMS)
mkdir -p "$APP/data/mods/mod" "$APP/data/mods/public"
cp "$D/mod.zip" "$APP/data/mods/mod/mod.zip"
if [ "${ZEROAD_ENGINE_ONLY:-0}" != 1 ]; then
	cp "$D/public-mobile.zip" "$APP/data/mods/public/public.zip"
	cat > "$APP/data/mods/public/mod.json" <<'JSON'
{
	"name": "0ad",
	"version": "0.28.0",
	"label": "0 A.D. Empires Ascendant",
	"url": "https://play0ad.com",
	"description": "A free, open-source, historical RTS game.",
	"dependencies": []
}
JSON
fi
cp "$ROOT/ios/CREDITS.txt" "$APP/CREDITS.txt"
du -sh "$APP/data"

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
