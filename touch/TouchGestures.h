/* Copyright (C) 2026 verkvest. Licensed under GPLv2 or later (same as 0 A.D.).
 *
 * Engine-independent touch gesture recognizer for the 0 A.D. iOS port.
 *
 *  - one-finger tap          -> LeftClick
 *  - one-finger drag         -> DragStart / DragMove / DragEnd with box = false (the engine pans the camera)
 *  - long press, then drag   -> LongPressArmed when the press arms (needs Update()), then
 *                               DragStart / DragMove / DragEnd with box = true (selection box)
 *  - long press and release  -> RightClick (when the finger lifts without moving)
 *  - two-finger tap          -> RightClick (at the centroid)
 *  - two-finger pan          -> Pan (centroid delta, pixels)
 *  - pinch                   -> Zoom (scale factor relative to previous frame, > 1 = fingers spread)
 *
 * Coordinates are in window pixels/points (caller converts SDL's normalized 0..1).
 * Time is in seconds (any monotonic clock).
 */
#ifndef ZEROAD_IOS_TOUCHGESTURES_H
#define ZEROAD_IOS_TOUCHGESTURES_H

#include <cstdint>
#include <vector>

namespace touch
{

struct Action
{
	enum Type
	{
		LeftClick,
		RightClick,
		DragStart,
		DragMove,
		DragEnd,
		Pan,
		Zoom,
		LongPressArmed
	};
	Type type;
	float x = 0.f, y = 0.f;   // position (click / drag point / gesture centroid)
	float dx = 0.f, dy = 0.f; // Pan delta
	float scale = 1.f;        // Zoom factor (current distance / previous distance)
	bool box = false;         // Drag*: started after a long press (selection box)
};

struct Config
{
	double tapMaxTime = 0.35;         // s, max duration of a 1-finger tap
	double longPressTime = 0.45;      // s, holding still this long arms box select / right click
	float tapMaxMove = 12.f;          // px, max movement of a tap
	double twoFingerTapMaxTime = 0.40; // s
	float twoFingerTapMaxMove = 16.f;  // px (centroid movement and finger spread change)
	float panThreshold = 6.f;          // px of centroid movement before pan starts
	float pinchThreshold = 0.04f;      // relative distance change before zoom starts
};

class Gestures
{
public:
	explicit Gestures(const Config& cfg = Config()) : m_Cfg(cfg) {}

	void FingerDown(int64_t id, float x, float y, double t);
	void FingerMotion(int64_t id, float x, float y, double t);
	void FingerUp(int64_t id, float x, float y, double t);
	/// Call every frame with the current time (long-press detection).
	void Update(double t);
	/// Call when the app loses focus / touches are cancelled.
	void Cancel();

	/// Returns and clears pending actions.
	std::vector<Action> Poll();

	int ActiveFingers() const;

private:
	enum State
	{
		IDLE,
		ONE_PENDING, // 1 finger down, could become tap or drag
		ONE_ARMED,   // long press reached: release = right click, move = box drag
		ONE_DRAG,
		TWO,         // 2 fingers: tap, pan or pinch
		ENDING       // gesture finished, wait until all fingers lifted
	};

	struct Finger
	{
		bool down = false;
		int64_t id = 0;
		float x = 0, y = 0;
		float startX = 0, startY = 0;
	};

	Finger* Find(int64_t id);
	Finger* Alloc(int64_t id);
	void Centroid(float& cx, float& cy) const;
	float Spread() const;
	void Emit(Action::Type type, float x, float y, bool box = false);

	Config m_Cfg;
	State m_State = IDLE;
	static constexpr int MAX_FINGERS = 2;
	Finger m_Fingers[MAX_FINGERS];
	double m_StartTime = 0;
	// TWO state
	float m_StartCx = 0, m_StartCy = 0, m_LastCx = 0, m_LastCy = 0;
	float m_StartSpread = 1, m_LastSpread = 1;
	bool m_Panning = false, m_Pinching = false;
	bool m_DragBox = false;
	std::vector<Action> m_Actions;
};

} // namespace touch

#endif
