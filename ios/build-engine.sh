#!/bin/bash
# Experimental: cross-compiles the 0 A.D. engine (pyrogenesis) for iOS using the
# upstream premake build with iOS compiler flags injected.
# Requires: build/deps/$PLATFORM with all libs from build-ios-deps.sh + SpiderMonkey.
# Output: build/engine-$PLATFORM.log (full compiler log), build/engine-summary.txt
set -o pipefail
. "$(dirname "$0")/env.sh"
set +e
Z="$ROOT/build/0ad"
[ -d "$Z" ] || "$ROOT/scripts/fetch-0ad.sh"
"$ROOT/scripts/apply-0ad-patches.sh" || exit 1

# 1) host premake (built natively, not for iOS)
(
	cd "$Z/libraries/source/premake-core"
	# premake derives its version from `git describe`; stop it from seeing 0ad's repo (v0.28.0)
	env -u CC -u CXX -u CFLAGS -u CXXFLAGS -u LDFLAGS -u CPPFLAGS -u AR -u RANLIB GIT_CEILING_DIRECTORIES="$PWD" JOBS="-j$JOBS" ./build.sh
) || { echo "premake build failed"; exit 1; }

# 2) present our iOS deps in the layout the macOS premake scripts expect
M="$Z/libraries/macos"
mkdir -p "$M/boost" "$M/iconv/include" "$M/iconv/lib"
ln -sfn "$DEPS_PREFIX/lib/pkgconfig" "$M/pkgconfig"
ln -sfn "$DEPS_PREFIX/include" "$M/boost/include"
# libs provided by the iOS SDK
cat > "$DEPS_PREFIX/lib/pkgconfig/zlib.pc" <<PC
Name: zlib
Description: zlib from the iOS SDK
Version: 1.2.12
Libs: -lz
Cflags:
PC
cat > "$DEPS_PREFIX/lib/pkgconfig/libxml-2.0.pc" <<PC
Name: libXML
Description: libxml2 from the iOS SDK
Version: 2.9.13
Libs: -lxml2
Cflags: -I$SDK_PATH/usr/include/libxml2
PC
SM="$Z/libraries/source/spidermonkey"
mkdir -p "$SM/lib"
MOZJS_PREFIX="${MOZJS_PREFIX:-$ROOT/build/mozjs/$PLATFORM}"
ln -sfn "$MOZJS_PREFIX/include/mozjs-release" "$SM/include-release"
cp -f "$MOZJS_PREFIX"/lib/libmozjs128-*.a "$SM/lib/" 2>/dev/null || echo "WARNING: SpiderMonkey for iOS not found in $MOZJS_PREFIX"

# 3) generate makefiles
cd "$Z/build/premake"
"$Z/libraries/source/premake-core/bin/premake5" --file=premake5.lua --outpath=../workspaces/ios \
	--gles --without-nvtt --without-lobby --without-miniupnpc --without-atlas --without-tests --without-pch --without-dap-interface \
	gmake || { echo "premake failed"; exit 1; }

# 4) compile, keep going to collect every error
cd ../workspaces/ios
LOG="$ROOT/build/engine-$PLATFORM.log"
make -k -j"$JOBS" config=release verbose=1 \
	CC="$CC" CXX="$CXX" AR="$AR" \
	CFLAGS="$CFLAGS -DGLES_SILENCE_DEPRECATION" CXXFLAGS="$BASE_FLAGS -DGLES_SILENCE_DEPRECATION" LDFLAGS="$LDFLAGS" \
	pyrogenesis >"$LOG" 2>&1
RC=$?

# 5) summary
{
	echo "make exit code: $RC"
	echo "object files compiled: $(find obj -name '*.o' | wc -l | tr -d ' ')"
	echo "static libs: $(find ../../../binaries/system -name '*.a' 2>/dev/null | xargs -n1 basename 2>/dev/null | tr '\n' ' ')"
	echo "files with errors: $(grep -E '^[^ ]+\.(cpp|mm|c|h):[0-9]+:[0-9]+: (fatal )?error:' "$LOG" | cut -d: -f1 | sort -u | wc -l | tr -d ' ')"
	echo "--- errors by directory ---"
	grep -E '^[^ ]+\.(cpp|mm|c|h):[0-9]+:[0-9]+: (fatal )?error:' "$LOG" | cut -d: -f1 | sed -E 's|.*/source/||; s|/[^/]+$||' | sort | uniq -c | sort -rn | head -40
	echo "--- first distinct errors ---"
	grep -E '(fatal )?error:' "$LOG" | sed -E 's|^.*/source/|source/|' | sort -u | head -80
} | tee "$ROOT/build/engine-summary.txt"
exit 0
