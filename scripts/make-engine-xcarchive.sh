#!/bin/bash
# Turns the cross-compiled device Pyrogenesis.app into an App Store-ready (unsigned) .xcarchive:
# compiles the app icon with actool, adds the DT* platform keys App Store validation expects,
# sets bundle id / version / build number. Signing happens later at -exportArchive (cloud signing).
# Usage: scripts/make-engine-xcarchive.sh <Pyrogenesis.app> <out.xcarchive> <bundle-id> <version> <build>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$1"; ARCH="$2"; BID="$3"; VER="$4"; BUILD="$5"
rm -rf "$ARCH"; mkdir -p "$ARCH/Products/Applications"
APP="$ARCH/Products/Applications/Pyrogenesis.app"
cp -R "$SRC" "$APP"
rm -rf "$APP/_CodeSignature"
PB=/usr/libexec/PlistBuddy
P="$APP/Info.plist"
set_kv() { $PB -c "Set :$1 $3" "$P" 2>/dev/null || $PB -c "Add :$1 $2 $3" "$P"; }
xcrun actool "$ROOT/touchdemo/Assets.xcassets" --compile "$APP" --platform iphoneos \
	--minimum-deployment-target 15.0 --app-icon AppIcon --target-device iphone --target-device ipad \
	--output-partial-info-plist "$RUNNER_TEMP/icon.plist" >/dev/null
$PB -c "Merge $RUNNER_TEMP/icon.plist" "$P"
SDKV=$(xcrun --sdk iphoneos --show-sdk-version)
SDKB=$(xcrun --sdk iphoneos --show-sdk-build-version)
XV=$(xcodebuild -version | awk '/Xcode/{print $2}' | tr -d .); XB=$(xcodebuild -version | awk '/Build version/{print $3}')
while [ ${#XV} -lt 4 ]; do XV="${XV}0"; done
set_kv CFBundleIdentifier string "$BID"
set_kv CFBundleShortVersionString string "$VER"
set_kv CFBundleVersion string "$BUILD"
set_kv CFBundleDisplayName string "0 A.D."
$PB -c "Delete :CFBundleSupportedPlatforms" "$P" 2>/dev/null || true; $PB -c "Add :CFBundleSupportedPlatforms array" -c "Add :CFBundleSupportedPlatforms:0 string iPhoneOS" "$P"
set_kv DTPlatformName string iphoneos
set_kv DTPlatformVersion string "$SDKV"
set_kv DTSDKName string "iphoneos$SDKV"
set_kv DTSDKBuild string "$SDKB"
set_kv DTPlatformBuild string "$SDKB"
set_kv DTCompiler string com.apple.compilers.llvm.clang.1_0
set_kv DTXcode string "$XV"
set_kv DTXcodeBuild string "$XB"
$PB -c "Delete :UIRequiredDeviceCapabilities" "$P" 2>/dev/null || true
$PB -c "Add :UIRequiredDeviceCapabilities array" -c "Add :UIRequiredDeviceCapabilities:0 string arm64" "$P"
plutil -convert binary1 "$P"
file "$APP/pyrogenesis"
xcrun vtool -show-build "$APP/pyrogenesis" | head -8 || true
cat > "$ARCH/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>ApplicationProperties</key><dict>
    <key>ApplicationPath</key><string>Applications/Pyrogenesis.app</string>
    <key>Architectures</key><array><string>arm64</string></array>
    <key>CFBundleIdentifier</key><string>$BID</string>
    <key>CFBundleShortVersionString</key><string>$VER</string>
    <key>CFBundleVersion</key><string>$BUILD</string>
  </dict>
  <key>ArchiveVersion</key><integer>2</integer>
  <key>CreationDate</key><date>$(date -u +%Y-%m-%dT%H:%M:%SZ)</date>
  <key>Name</key><string>Pyrogenesis</string>
  <key>SchemeName</key><string>Pyrogenesis</string>
</dict></plist>
PL
echo "archive ready: $ARCH"; du -sh "$APP"
