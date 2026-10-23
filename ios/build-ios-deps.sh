#!/bin/bash
# Cross-compiles 0 A.D. third-party dependencies as static libraries for iOS.
# Versions follow libraries/build-macos-libs.sh of 0 A.D. v0.28.0 where possible.
#
# Usage: PLATFORM=iphonesimulator ios/build-ios-deps.sh [lib ...]
#   default: all libs in $ALL_LIBS order.
# Provided by the iOS SDK (not built): zlib, libiconv, libxml2 (.tbd), OpenGLES, Metal.
set -eo pipefail
. "$(dirname "$0")/env.sh"

SDL2_VERSION="2.30.9"
PNG_VERSION="1.6.44"
FREETYPE_VERSION="2.13.3"
OGG_VERSION="1.3.5"
VORBIS_VERSION="1.3.7"
FMT_VERSION="7.1.3"
ENET_VERSION="1.3.18"
SODIUM_VERSION="1.0.20"
BOOST_VERSION="1.81.0"
OPENAL_VERSION="1.24.2"
CURL_VERSION="8.10.1"
ICU_VERSION="69-1"

ALL_LIBS="sdl2 libpng freetype ogg vorbis fmt enet sodium boost openal curl icu"

log() { echo "::group::$*"; }
endlog() { echo "::endgroup::"; }

fetch() { # url file
	local url="$1" file="$DEPS_SRC/$2"
	[ -s "$file" ] || curl -fsSL --retry 3 -o "$file" "$url"
	echo "$file"
}

stamp() { [ -e "$DEPS_PREFIX/.built-$1" ]; }
mark() { touch "$DEPS_PREFIX/.built-$1"; }

unpack() { # archive dir
	rm -rf "$DEPS_SRC/$2"
	tar -xf "$1" -C "$DEPS_SRC"
	cd "$DEPS_SRC/$2"
}

build_sdl2() {
	local a; a=$(fetch "https://github.com/libsdl-org/SDL/releases/download/release-$SDL2_VERSION/SDL2-$SDL2_VERSION.tar.gz" "SDL2-$SDL2_VERSION.tar.gz")
	unpack "$a" "SDL2-$SDL2_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DSDL_SHARED=OFF -DSDL_STATIC=ON -DSDL_TEST=OFF
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_libpng() {
	local a; a=$(fetch "https://download.sourceforge.net/libpng/libpng-$PNG_VERSION.tar.gz" "libpng-$PNG_VERSION.tar.gz")
	unpack "$a" "libpng-$PNG_VERSION"
	# zlib from the SDK
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DPNG_SHARED=OFF -DPNG_STATIC=ON -DPNG_TESTS=OFF -DPNG_FRAMEWORK=OFF -DPNG_EXECUTABLES=OFF -DPNG_ARM_NEON=on
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_freetype() {
	local a; a=$(fetch "https://download.savannah.gnu.org/releases/freetype/freetype-$FREETYPE_VERSION.tar.xz" "freetype-$FREETYPE_VERSION.tar.xz")
	unpack "$a" "freetype-$FREETYPE_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DFT_DISABLE_BZIP2=ON -DFT_DISABLE_BROTLI=ON -DFT_DISABLE_HARFBUZZ=ON -DFT_REQUIRE_PNG=ON -DFT_REQUIRE_ZLIB=ON
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_ogg() {
	local a; a=$(fetch "https://downloads.xiph.org/releases/ogg/libogg-$OGG_VERSION.tar.gz" "libogg-$OGG_VERSION.tar.gz")
	unpack "$a" "libogg-$OGG_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DINSTALL_DOCS=OFF -DBUILD_TESTING=OFF
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_vorbis() {
	local a; a=$(fetch "https://downloads.xiph.org/releases/vorbis/libvorbis-$VORBIS_VERSION.tar.gz" "libvorbis-$VORBIS_VERSION.tar.gz")
	unpack "$a" "libvorbis-$VORBIS_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_fmt() {
	local a; a=$(fetch "https://github.com/fmtlib/fmt/archive/refs/tags/$FMT_VERSION.tar.gz" "fmt-$FMT_VERSION.tar.gz")
	unpack "$a" "fmt-$FMT_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DFMT_TEST=OFF -DFMT_DOC=OFF
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_enet() {
	local a; a=$(fetch "http://enet.bespin.org/download/enet-$ENET_VERSION.tar.gz" "enet-$ENET_VERSION.tar.gz")
	unpack "$a" "enet-$ENET_VERSION"
	./configure --host="$AC_HOST" --prefix="$DEPS_PREFIX" --enable-shared=no
	make -j "$JOBS"
	make install
}

build_sodium() {
	local a; a=$(fetch "https://download.libsodium.org/libsodium/releases/libsodium-$SODIUM_VERSION.tar.gz" "libsodium-$SODIUM_VERSION.tar.gz")
	unpack "$a" "libsodium-$SODIUM_VERSION"
	./configure --host="$AC_HOST" --prefix="$DEPS_PREFIX" --enable-shared=no --disable-pie --enable-minimal=no
	make -j "$JOBS"
	make install
}

build_boost() {
	# 0 A.D. uses header-only Boost (+ filesystem/system on some platforms); headers are enough for the prototype.
	local v="${BOOST_VERSION//./_}"
	local a; a=$(fetch "https://archives.boost.io/release/$BOOST_VERSION/source/boost_$v.tar.bz2" "boost_$v.tar.bz2")
	rm -rf "$DEPS_PREFIX/include/boost"
	tar -xf "$a" -C "$DEPS_SRC" "boost_$v/boost"
	cp -R "$DEPS_SRC/boost_$v/boost" "$DEPS_PREFIX/include/"
}

build_openal() {
	local a; a=$(fetch "https://github.com/kcat/openal-soft/archive/refs/tags/$OPENAL_VERSION.tar.gz" "openal-soft-$OPENAL_VERSION.tar.gz")
	unpack "$a" "openal-soft-$OPENAL_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DLIBTYPE=STATIC -DALSOFT_UTILS=OFF -DALSOFT_EXAMPLES=OFF -DALSOFT_TESTS=OFF \
		-DALSOFT_BACKEND_COREAUDIO=ON -DALSOFT_REQUIRE_COREAUDIO=ON -DALSOFT_INSTALL_HRTF_DATA=OFF -DALSOFT_INSTALL_AMBDEC_PRESETS=OFF
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_curl() {
	local a; a=$(fetch "https://curl.se/download/curl-$CURL_VERSION.tar.xz" "curl-$CURL_VERSION.tar.xz")
	unpack "$a" "curl-$CURL_VERSION"
	cmake -S . -B build -G Ninja $CMAKE_IOS_FLAGS -DBUILD_CURL_EXE=OFF -DBUILD_TESTING=OFF -DBUILD_STATIC_LIBS=ON \
		-DCURL_USE_SECTRANSP=ON -DCURL_USE_LIBPSL=OFF -DCURL_USE_LIBSSH2=OFF -DUSE_LIBIDN2=OFF -DUSE_NGHTTP2=OFF \
		-DCURL_DISABLE_LDAP=ON -DENABLE_UNIX_SOCKETS=ON -DCURL_ZSTD=OFF -DCURL_BROTLI=OFF
	cmake --build build -j "$JOBS"
	cmake --install build
}

build_icu() {
	local u="${ICU_VERSION//-/_}"
	local a; a=$(fetch "https://github.com/unicode-org/icu/releases/download/release-$ICU_VERSION/icu4c-${u}-src.tgz" "icu4c-${u}-src.tgz")
	rm -rf "$DEPS_SRC/icu" "$DEPS_SRC/icu-host"
	tar -xf "$a" -C "$DEPS_SRC"
	# 1) native host build (needed for data tools)
	mkdir -p "$DEPS_SRC/icu-host"
	(
		cd "$DEPS_SRC/icu-host"
		env -u CFLAGS -u CXXFLAGS -u LDFLAGS -u CPPFLAGS -u CC -u CXX -u AR -u RANLIB \
			CC=clang CXX=clang++ CXXFLAGS="-std=c++17" \
			"$DEPS_SRC/icu/source/configure" --disable-tests --disable-samples --disable-extras --disable-tools=no --enable-static --disable-shared
		env -u CFLAGS -u CXXFLAGS -u LDFLAGS -u CPPFLAGS -u CC -u CXX -u AR -u RANLIB make -j "$JOBS"
	)
	# 2) cross build
	mkdir -p "$DEPS_SRC/icu/build-ios"
	cd "$DEPS_SRC/icu/build-ios"
	CXXFLAGS="$CXXFLAGS -DUCONFIG_NO_FILE_IO=0" \
	../source/configure --host="$AC_HOST" --prefix="$DEPS_PREFIX" --with-cross-build="$DEPS_SRC/icu-host" \
		--enable-static --disable-shared --disable-tools --disable-tests --disable-samples --disable-extras \
		--with-data-packaging=static
	make -j "$JOBS"
	make install
}

LIBS="${*:-$ALL_LIBS}"
for lib in $LIBS; do
	if stamp "$lib"; then
		echo "== $lib: already built (cached)"
		continue
	fi
	log "Building $lib for $PLATFORM"
	( "build_$lib" ) 2>&1
	mark "$lib"
	endlog
done
echo "Built into $DEPS_PREFIX:"
ls -1 "$DEPS_PREFIX/lib"
