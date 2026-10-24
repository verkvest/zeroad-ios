cmake_minimum_required(VERSION 3.20)
project(zeroad_touchdemo C CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(SDL2 REQUIRED CONFIG)

set(APP_BUNDLE_ID "es.verkvest.zeroad.touchdemo" CACHE STRING "CFBundleIdentifier")
set(APP_VERSION "0.1.0" CACHE STRING "CFBundleShortVersionString")
set(APP_BUILD "1" CACHE STRING "CFBundleVersion")

set(ASSETS "")
if(CMAKE_GENERATOR STREQUAL "Xcode")
	# App icon (asset catalog compiled by actool; required for App Store / TestFlight).
	set(ASSETS "${CMAKE_CURRENT_SOURCE_DIR}/Assets.xcassets")
endif()

add_executable(touchdemo MACOSX_BUNDLE main.cpp ../touch/TouchGestures.cpp ${ASSETS})
target_link_libraries(touchdemo PRIVATE SDL2::SDL2main SDL2::SDL2-static)
target_link_libraries(touchdemo PRIVATE
	"-framework UIKit" "-framework Foundation" "-framework CoreGraphics" "-framework QuartzCore"
	"-framework Metal" "-framework OpenGLES" "-framework AVFoundation" "-framework AudioToolbox"
	"-framework CoreAudio" "-framework CoreMotion" "-framework GameController" "-framework CoreHaptics"
	"-framework CoreBluetooth" "-framework CoreFoundation" "-framework Security")
set_target_properties(touchdemo PROPERTIES
	OUTPUT_NAME "ZeroADTouch"
	MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"
	MACOSX_BUNDLE_GUI_IDENTIFIER "${APP_BUNDLE_ID}"
	MACOSX_BUNDLE_BUNDLE_NAME "ZeroADTouch"
	MACOSX_BUNDLE_SHORT_VERSION_STRING "${APP_VERSION}"
	MACOSX_BUNDLE_BUNDLE_VERSION "${APP_BUILD}"
	XCODE_ATTRIBUTE_PRODUCT_BUNDLE_IDENTIFIER "${APP_BUNDLE_ID}"
	XCODE_ATTRIBUTE_ASSETCATALOG_COMPILER_APPICON_NAME "AppIcon"
	XCODE_ATTRIBUTE_TARGETED_DEVICE_FAMILY "1,2"
	XCODE_ATTRIBUTE_IPHONEOS_DEPLOYMENT_TARGET "15.0")
if(ASSETS)
	set_source_files_properties(${ASSETS} PROPERTIES MACOSX_PACKAGE_LOCATION Resources)
endif()
