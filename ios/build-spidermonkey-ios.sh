#!/bin/bash
# Builds SpiderMonkey (mozjs 128, as pinned by 0 A.D.) for iOS, interpreter-only:
# iOS forbids JIT (no W^X pages for third-party apps), so we use the
# Portable Baseline Interpreter (--enable-portable-baseline-interp, implies --disable-jit).
# Usage: PLATFORM=iphonesimulator|iphoneos ios/build-spidermonkey-ios.sh
set -eo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM="${PLATFORM:-iphonesimulator}"
IOS_MIN="${IOS_MIN:-15.0}"
OUT="${MOZJS_PREFIX:-$ROOT/build/mozjs/$PLATFORM}"
SMDIR="$ROOT/build/0ad/libraries/source/spidermonkey"
PV=128.13.0
FOLDER="mozjs-$PV"
if [ "$PLATFORM" = "iphonesimulator" ]; then TARGET=aarch64-apple-ios-sim; else TARGET=aarch64-apple-ios; fi
SDK="$(xcrun --sdk "$PLATFORM" --show-sdk-path)"

[ -d "$SMDIR" ] || "$ROOT/scripts/fetch-0ad.sh"
cd "$SMDIR"
[ -s "$FOLDER.tar.xz" ] || curl -fL --retry 3 -o "$FOLDER.tar.xz" "https://releases.wildfiregames.com/libs/$FOLDER.tar.xz"
rm -rf "$FOLDER"
tar xfJ "$FOLDER.tar.xz" --exclude=js/src/tests/non262 --exclude=js/src/tests/test262 --exclude=js/src/jit-test \
	--exclude=python/mozperftest --exclude=testing/web-platform --exclude=third_party/rust/mp4parse/link-u-avif-sample-images
(
	cd "$FOLDER"
	OS=Darwin . ../patches/patch.sh
	for p in "$ROOT"/patches/spidermonkey/*.patch; do
		[ -e "$p" ] || continue
		echo "Applying $(basename "$p")"
		patch -p1 <"$p"
	done
	# iOS devices use 16 KiB pages and pthread_attr_setstacksize() rejects sizes
	# that are not page multiples. Upstream's 2 MiB - 2*4 KiB helper stack size
	# trips MOZ_RELEASE_ASSERT(!r) in Thread::create at JS_NewContext (crash in TestFlight build 11).
	sed -i.bak 's/2048 \* 1024 - 2 \* 4096;/2048 * 1024 - 2 * 16384;/' js/src/vm/InternalThreadPool.cpp
	grep -q '2048 \* 1024 - 2 \* 16384;' js/src/vm/InternalThreadPool.cpp || { echo "helper stack size patch failed"; exit 1; }
)
cd "$FOLDER"
export MOZ_NOSPAM=1
export MACH_BUILD_PYTHON_NATIVE_PACKAGE_SOURCE=none
export MOZBUILD_STATE_PATH="$(pwd)/mozbuild-state"
unset CC CXX CFLAGS CXXFLAGS LDFLAGS CPPFLAGS
export CFLAGS="-w" CXXFLAGS="-w"
MOZCONFIG="$SMDIR/mozconfig" \
MOZCONFIG_OPTIONS="--target=$TARGET --enable-ios-target=$IOS_MIN --with-ios-sdk=$SDK \
	--enable-portable-baseline-interp --disable-jit --disable-shared-js --enable-optimize --disable-debug" \
BUILD_DIR="build-release" \
	./mach build -j"${JOBS:-$(sysctl -n hw.ncpu)}"
echo "mach build finished"
set -x

mkdir -p "$OUT/lib" "$OUT/include/mozjs-release"
cp -R -L build-release/dist/include/* "$OUT/include/mozjs-release/"
rm -f "$OUT/include/mozjs-release/"{zlib.h,zconf.h,mozzconf.h}
cp -L build-release/js/src/build/libjs_static.a "$OUT/lib/libmozjs128-release.a"
rust_path="$(find build-release -name libjsrust.a -not -path "*/deps/*" | head -1)"
echo "jsrust: $rust_path"
cp -L "$rust_path" "$OUT/lib/libmozjs128-rust.a"
# static js needs mozglue (moz_arena_*, MOZ_Crash*, MozWalkTheStack, memalign shim)
echo "--- static archives in build tree ---"
find build-release -name '*.a' -not -path '*/deps/*' -not -path '*/rust/*' | sed 's/^/  /' | head -50
# In a static (non-shared-js) build mozglue/memory/mfbt are left as loose objects for the final link.
glue_objs="$(find build-release/mozglue build-release/memory build-release/mfbt -name '*.o' -not -path '*/test*' -not -path '*/gtest/*' 2>/dev/null | sort -u)"
echo "glue objects:"; echo "$glue_objs" | sed 's/^/  /'
cat >memalign_shim.c <<'C'
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
/* iOS libc has no memalign(); mozjs falls back to it when jemalloc is disabled. */
void *memalign(size_t alignment, size_t size) {
	void *p = NULL;
	if (alignment < sizeof(void *)) alignment = sizeof(void *);
	return posix_memalign(&p, alignment, size) == 0 ? p : NULL;
}
C
xcrun --sdk "$PLATFORM" clang -isysroot "$SDK" -target "arm64-apple-ios$IOS_MIN$([ "$PLATFORM" = iphonesimulator ] && echo -simulator)" \
	-O2 -c memalign_shim.c -o memalign_shim.o
glue_a="$(find build-release -name 'libwrappers.a' -path '*mozglue*' | head -1)"
xcrun libtool -static -o "$OUT/lib/libmozjs128-glue.a" $glue_objs memalign_shim.o $glue_a
ls -la "$OUT/lib/"libmozjs128*
touch "$OUT/.built-spidermonkey"
