#!/bin/bash
# Common cross-compilation environment for iOS.
# Usage: PLATFORM=iphonesimulator|iphoneos . ios/env.sh
set -e
export PLATFORM="${PLATFORM:-iphonesimulator}"
export IOS_MIN="${IOS_MIN:-15.0}"
export IOS_ARCH="${IOS_ARCH:-arm64}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
export DEPS_PREFIX="${DEPS_PREFIX:-$ROOT/build/deps/$PLATFORM}"
export DEPS_SRC="${DEPS_SRC:-$ROOT/build/deps-src}"
export SDK_PATH="$(xcrun --sdk "$PLATFORM" --show-sdk-path)"
if [ "$PLATFORM" = "iphonesimulator" ]; then
	export MIN_FLAG="-mios-simulator-version-min=$IOS_MIN"
	export TARGET_TRIPLE="arm64-apple-ios$IOS_MIN-simulator"
	export RUST_TARGET="aarch64-apple-ios-sim"
	export MOZ_TARGET="aarch64-apple-ios-sim"
else
	export MIN_FLAG="-miphoneos-version-min=$IOS_MIN"
	export TARGET_TRIPLE="arm64-apple-ios$IOS_MIN"
	export RUST_TARGET="aarch64-apple-ios"
	export MOZ_TARGET="aarch64-apple-ios"
fi
# autotools: a host != build triple forces cross-compilation mode
export AC_HOST="arm-apple-darwin"
export CC="$(xcrun --sdk "$PLATFORM" -f clang)"
export CXX="$(xcrun --sdk "$PLATFORM" -f clang++)"
export AR="$(xcrun --sdk "$PLATFORM" -f ar)"
export RANLIB="$(xcrun --sdk "$PLATFORM" -f ranlib)"
export BASE_FLAGS="-arch $IOS_ARCH -isysroot $SDK_PATH $MIN_FLAG -fvisibility=hidden -O2"
export CFLAGS="$BASE_FLAGS"
export CXXFLAGS="$BASE_FLAGS -std=c++17 -stdlib=libc++"
export LDFLAGS="-arch $IOS_ARCH -isysroot $SDK_PATH $MIN_FLAG"
export CPPFLAGS="-I$DEPS_PREFIX/include"
export PKG_CONFIG_PATH="$DEPS_PREFIX/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="$DEPS_PREFIX/lib/pkgconfig"
export CMAKE_IOS_FLAGS="-DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=$PLATFORM -DCMAKE_OSX_ARCHITECTURES=$IOS_ARCH -DCMAKE_OSX_DEPLOYMENT_TARGET=$IOS_MIN -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=$DEPS_PREFIX -DCMAKE_PREFIX_PATH=$DEPS_PREFIX -DBUILD_SHARED_LIBS=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5"
export JOBS="${JOBS:-$(sysctl -n hw.ncpu 2>/dev/null || echo 4)}"
mkdir -p "$DEPS_PREFIX/lib/pkgconfig" "$DEPS_PREFIX/include" "$DEPS_SRC"
