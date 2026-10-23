/* 0 A.D. iOS port - milestone app: SDL2 + touch gesture layer running on iOS.
 * Draws a fake "map" grid; two-finger pan moves it, pinch zooms it,
 * tap places a green marker (left click), two-finger tap a red marker (right click),
 * one-finger drag draws a blue selection box.
 *
 * Launch argument "--selftest" injects synthetic SDL finger events, verifies that the
 * gesture layer produced the expected actions, prints "TOUCHDEMO SELFTEST PASS/FAIL" and exits.
 */
#include "../touch/TouchGestures.h"

#include <SDL.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

namespace
{
struct Marker
{
	float wx, wy; // world coords
	bool right;
};

struct Camera
{
	float ox = 0, oy = 0; // world position at screen (0,0)
	float zoom = 1;
	float ToScreenX(float wx) const { return (wx - ox) * zoom; }
	float ToScreenY(float wy) const { return (wy - oy) * zoom; }
	float ToWorldX(float sx) const { return sx / zoom + ox; }
	float ToWorldY(float sy) const { return sy / zoom + oy; }
};

struct Stats
{
	int left = 0, right = 0, pan = 0, zoom = 0, dragStart = 0, dragEnd = 0;
	float panDy = 0;
};

double Now() { return SDL_GetPerformanceCounter() / double(SDL_GetPerformanceFrequency()); }

void PushFinger(Uint32 type, SDL_FingerID id, float nx, float ny)
{
	SDL_Event ev;
	SDL_zero(ev);
	ev.type = type;
	ev.tfinger.touchId = 1;
	ev.tfinger.fingerId = id;
	ev.tfinger.x = nx;
	ev.tfinger.y = ny;
	ev.tfinger.pressure = 1.f;
	SDL_PushEvent(&ev);
}

// Self-test script: each step runs on its own frame (~16ms apart).
bool SelfTestStep(int frame)
{
	switch (frame)
	{
	// tap
	case 5: PushFinger(SDL_FINGERDOWN, 1, 0.30f, 0.30f); break;
	case 7: PushFinger(SDL_FINGERUP, 1, 0.30f, 0.30f); break;
	// two-finger tap
	case 20: PushFinger(SDL_FINGERDOWN, 1, 0.40f, 0.50f); PushFinger(SDL_FINGERDOWN, 2, 0.60f, 0.50f); break;
	case 23: PushFinger(SDL_FINGERUP, 1, 0.40f, 0.50f); PushFinger(SDL_FINGERUP, 2, 0.60f, 0.50f); break;
	// two-finger pan
	case 40: PushFinger(SDL_FINGERDOWN, 1, 0.40f, 0.40f); PushFinger(SDL_FINGERDOWN, 2, 0.60f, 0.40f); break;
	case 41: case 42: case 43: case 44: case 45: case 46: case 47: case 48:
	{
		float y = 0.40f + (frame - 40) * 0.02f;
		PushFinger(SDL_FINGERMOTION, 1, 0.40f, y);
		PushFinger(SDL_FINGERMOTION, 2, 0.60f, y);
		break;
	}
	case 49: PushFinger(SDL_FINGERUP, 1, 0.40f, 0.56f); PushFinger(SDL_FINGERUP, 2, 0.60f, 0.56f); break;
	// pinch
	case 60: PushFinger(SDL_FINGERDOWN, 1, 0.45f, 0.5f); PushFinger(SDL_FINGERDOWN, 2, 0.55f, 0.5f); break;
	case 61: case 62: case 63: case 64: case 65: case 66:
	{
		float d = (frame - 60) * 0.03f;
		PushFinger(SDL_FINGERMOTION, 1, 0.45f - d, 0.5f);
		PushFinger(SDL_FINGERMOTION, 2, 0.55f + d, 0.5f);
		break;
	}
	case 67: PushFinger(SDL_FINGERUP, 1, 0.27f, 0.5f); PushFinger(SDL_FINGERUP, 2, 0.73f, 0.5f); break;
	// drag (selection box)
	case 80: PushFinger(SDL_FINGERDOWN, 1, 0.2f, 0.2f); break;
	case 81: case 82: case 83: case 84:
		PushFinger(SDL_FINGERMOTION, 1, 0.2f + (frame - 80) * 0.05f, 0.2f + (frame - 80) * 0.04f);
		break;
	case 85: PushFinger(SDL_FINGERUP, 1, 0.4f, 0.36f); break;
	case 100: return true; // done
	default: break;
	}
	return false;
}

void FillRect(SDL_Renderer* r, float x, float y, float w, float h)
{
	SDL_FRect rc{x, y, w, h};
	SDL_RenderFillRectF(r, &rc);
}
} // namespace

int main(int argc, char* argv[])
{
	bool selftest = false;
	for (int i = 1; i < argc; ++i)
		if (!std::strcmp(argv[i], "--selftest"))
			selftest = true;
	if (SDL_getenv("TOUCHDEMO_SELFTEST"))
		selftest = true;

	// The engine wants raw touches; don't let SDL synthesize mouse events from them.
	SDL_SetHint(SDL_HINT_TOUCH_MOUSE_EVENTS, "0");
	SDL_SetHint(SDL_HINT_IOS_HIDE_HOME_INDICATOR, "2");
	SDL_SetHint(SDL_HINT_ORIENTATIONS, "LandscapeLeft LandscapeRight");

	if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_EVENTS) != 0)
	{
		std::printf("SDL_Init failed: %s\n", SDL_GetError());
		return 1;
	}
	SDL_Window* win = SDL_CreateWindow("0 A.D. touch demo", 0, 0, 0, 0,
		SDL_WINDOW_FULLSCREEN | SDL_WINDOW_ALLOW_HIGHDPI | SDL_WINDOW_SHOWN);
	if (!win)
	{
		std::printf("SDL_CreateWindow failed: %s\n", SDL_GetError());
		return 1;
	}
	SDL_Renderer* ren = SDL_CreateRenderer(win, -1, SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
	if (!ren)
		ren = SDL_CreateRenderer(win, -1, 0);
	SDL_RendererInfo info;
	SDL_GetRendererInfo(ren, &info);
	int ww, wh, pw, ph;
	SDL_GetWindowSize(win, &ww, &wh);
	SDL_GetRendererOutputSize(ren, &pw, &ph);
	std::printf("TOUCHDEMO window %dx%d pt, %dx%d px, renderer %s, SDL %d.%d.%d\n", ww, wh, pw, ph, info.name,
		SDL_MAJOR_VERSION, SDL_MINOR_VERSION, SDL_PATCHLEVEL);
	std::fflush(stdout);

	touch::Gestures gestures;
	Camera cam;
	Stats st;
	std::vector<Marker> markers;
	bool dragging = false;
	float dragX0 = 0, dragY0 = 0, dragX1 = 0, dragY1 = 0;
	bool running = true;
	int frame = 0;
	int exitCode = 0;

	while (running)
	{
		if (selftest && SelfTestStep(frame))
		{
			const bool ok = st.left == 1 && st.right == 1 && st.pan > 0 && st.zoom > 0 && st.dragStart == 1 &&
				st.dragEnd == 1 && cam.zoom > 1.5f && st.panDy > 30.f;
			std::printf("TOUCHDEMO SELFTEST %s left=%d right=%d pan=%d zoom=%d drag=%d/%d camZoom=%.2f panDy=%.1f\n",
				ok ? "PASS" : "FAIL", st.left, st.right, st.pan, st.zoom, st.dragStart, st.dragEnd, cam.zoom, st.panDy);
			std::fflush(stdout);
			exitCode = ok ? 0 : 3;
			if (!SDL_getenv("TOUCHDEMO_STAY"))
				running = false;
			selftest = false;
		}

		SDL_Event ev;
		while (SDL_PollEvent(&ev))
		{
			const double t = Now();
			switch (ev.type)
			{
			case SDL_QUIT: running = false; break;
			case SDL_FINGERDOWN: gestures.FingerDown(ev.tfinger.fingerId, ev.tfinger.x * ww, ev.tfinger.y * wh, t); break;
			case SDL_FINGERMOTION: gestures.FingerMotion(ev.tfinger.fingerId, ev.tfinger.x * ww, ev.tfinger.y * wh, t); break;
			case SDL_FINGERUP: gestures.FingerUp(ev.tfinger.fingerId, ev.tfinger.x * ww, ev.tfinger.y * wh, t); break;
			case SDL_APP_WILLENTERBACKGROUND: gestures.Cancel(); break;
			default: break;
			}
		}

		for (const touch::Action& a : gestures.Poll())
		{
			switch (a.type)
			{
			case touch::Action::LeftClick: ++st.left; markers.push_back({cam.ToWorldX(a.x), cam.ToWorldY(a.y), false}); break;
			case touch::Action::RightClick: ++st.right; markers.push_back({cam.ToWorldX(a.x), cam.ToWorldY(a.y), true}); break;
			case touch::Action::Pan: ++st.pan; st.panDy += a.dy; cam.ox -= a.dx / cam.zoom; cam.oy -= a.dy / cam.zoom; break;
			case touch::Action::Zoom:
			{
				++st.zoom;
				// zoom around the gesture centroid
				const float wx = cam.ToWorldX(a.x), wy = cam.ToWorldY(a.y);
				cam.zoom = std::fmax(0.25f, std::fmin(8.f, cam.zoom * a.scale));
				cam.ox = wx - a.x / cam.zoom;
				cam.oy = wy - a.y / cam.zoom;
				break;
			}
			case touch::Action::DragStart: ++st.dragStart; dragging = true; dragX0 = dragX1 = a.x; dragY0 = dragY1 = a.y; break;
			case touch::Action::DragMove: dragX1 = a.x; dragY1 = a.y; break;
			case touch::Action::DragEnd: ++st.dragEnd; dragging = false; break;
			}
		}

		// render (in points; scale to pixels)
		SDL_RenderSetScale(ren, float(pw) / ww, float(ph) / wh);
		SDL_SetRenderDrawColor(ren, 58, 92, 46, 255); // grass
		SDL_RenderClear(ren);
		SDL_SetRenderDrawColor(ren, 80, 120, 64, 255);
		const float cell = 64.f;
		const float x0 = std::floor(cam.ox / cell) * cell, y0 = std::floor(cam.oy / cell) * cell;
		for (float x = x0; cam.ToScreenX(x) < ww; x += cell)
			SDL_RenderDrawLineF(ren, cam.ToScreenX(x), 0, cam.ToScreenX(x), float(wh));
		for (float y = y0; cam.ToScreenY(y) < wh; y += cell)
			SDL_RenderDrawLineF(ren, 0, cam.ToScreenY(y), float(ww), cam.ToScreenY(y));
		// a "town centre" at world origin
		SDL_SetRenderDrawColor(ren, 170, 130, 80, 255);
		FillRect(ren, cam.ToScreenX(200), cam.ToScreenY(150), 96 * cam.zoom, 96 * cam.zoom);
		for (const Marker& m : markers)
		{
			if (m.right)
				SDL_SetRenderDrawColor(ren, 220, 40, 40, 255);
			else
				SDL_SetRenderDrawColor(ren, 40, 230, 80, 255);
			FillRect(ren, cam.ToScreenX(m.wx) - 8, cam.ToScreenY(m.wy) - 8, 16, 16);
		}
		if (dragging)
		{
			SDL_SetRenderDrawColor(ren, 80, 160, 255, 255);
			SDL_FRect rc{std::fmin(dragX0, dragX1), std::fmin(dragY0, dragY1), std::fabs(dragX1 - dragX0), std::fabs(dragY1 - dragY0)};
			SDL_RenderDrawRectF(ren, &rc);
		}
		// status bar: counters as bars (no font yet)
		const int counts[4] = {st.left, st.right, st.pan, st.zoom};
		const Uint8 col[4][3] = {{40, 230, 80}, {220, 40, 40}, {240, 240, 240}, {240, 200, 40}};
		for (int i = 0; i < 4; ++i)
		{
			SDL_SetRenderDrawColor(ren, col[i][0], col[i][1], col[i][2], 255);
			FillRect(ren, 20, 20 + i * 14.f, 8.f + std::fmin(300.f, counts[i] * 8.f), 10);
		}
		SDL_RenderPresent(ren);
		++frame;
		if (!selftest)
			SDL_Delay(1);
	}

	SDL_DestroyRenderer(ren);
	SDL_DestroyWindow(win);
	SDL_Quit();
	return exitCode;
}
