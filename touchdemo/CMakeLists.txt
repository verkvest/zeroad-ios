cmake_minimum_required(VERSION 3.20)
project(zeroad_touchdemo C CXX)
set(CMAKE_CXX_STANDARD 17)
find_package(SDL2 REQUIRED CONFIG)

add_executable(touchdemo MACOSX_BUNDLE main.cpp ../touch/TouchGestures.cpp)
target_link_libraries(touchdemo PRIVATE SDL2::SDL2main SDL2::SDL2-static)
target_link_libraries(touchdemo PRIVATE
	"-framework UIKit" "-framework Foundation" "-framework CoreGraphics" "-framework QuartzCore"
	"-framework Metal" "-framework OpenGLES" "-framework AVFoundation" "-framework AudioToolbox"
	"-framework CoreAudio" "-framework CoreMotion" "-framework GameController" "-framework CoreHaptics"
	"-framework CoreBluetooth" "-framework CoreFoundation" "-framework Security")
set_target_properties(touchdemo PROPERTIES
	OUTPUT_NAME "ZeroADTouch"
	MACOSX_BUNDLE_INFO_PLIST "${CMAKE_CURRENT_SOURCE_DIR}/Info.plist.in"
	MACOSX_BUNDLE_GUI_IDENTIFIER "es.verkvest.zeroad.touchdemo"
	MACOSX_BUNDLE_BUNDLE_NAME "ZeroADTouch"
	MACOSX_BUNDLE_SHORT_VERSION_STRING "0.1.0"
	MACOSX_BUNDLE_BUNDLE_VERSION "1")
