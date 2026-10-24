// Host unit tests for the gesture recognizer (no engine, no SDL).
#include "TouchGestures.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>

using touch::Action;
static int g_Fail = 0;
#define CHECK(c) do { if (!(c)) { std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c); ++g_Fail; } } while (0)

static int Count(const std::vector<Action>& v, Action::Type t)
{
	int n = 0;
	for (const Action& a : v)
		n += a.type == t;
	return n;
}

int main()
{
	{ // tap -> left click
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.FingerUp(1, 102, 101, 0.1);
		auto a = g.Poll();
		CHECK(a.size() == 1 && a[0].type == Action::LeftClick && a[0].x == 100);
	}
	{ // long press without Update(): nothing (no tap)
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.FingerUp(1, 100, 100, 2.0);
		CHECK(g.Poll().empty());
	}
	{ // long press arms (no right click yet); release without moving -> right click
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.Update(0.3);
		CHECK(g.Poll().empty());
		g.Update(0.5);
		auto a = g.Poll();
		CHECK(a.size() == 1 && a[0].type == Action::LongPressArmed && a[0].x == 100);
		g.FingerUp(1, 101, 100, 0.8);
		a = g.Poll();
		CHECK(a.size() == 1 && a[0].type == Action::RightClick && a[0].x == 100);
	}
	{ // long press then drag -> box drag, no right click
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.Update(0.5);
		g.Poll();
		g.FingerMotion(1, 140, 100, 0.7);
		g.FingerMotion(1, 180, 120, 0.8);
		g.FingerUp(1, 180, 120, 0.9);
		auto a = g.Poll();
		CHECK(Count(a, Action::DragStart) == 1 && a.front().box && a.front().x == 100);
		CHECK(Count(a, Action::DragEnd) == 1 && a.back().box);
		CHECK(Count(a, Action::RightClick) == 0);
	}
	{ // slow tap (0.40 s) still a left click
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.Update(0.35);
		g.FingerUp(1, 100, 100, 0.40);
		auto a = g.Poll();
		CHECK(a.size() == 1 && a[0].type == Action::LeftClick);
	}
	{ // drag
		touch::Gestures g;
		g.FingerDown(1, 10, 10, 0.0);
		g.FingerMotion(1, 50, 10, 0.1);
		g.FingerMotion(1, 90, 10, 0.2);
		g.FingerUp(1, 90, 10, 0.3);
		auto a = g.Poll();
		CHECK(Count(a, Action::DragStart) == 1);
		CHECK(Count(a, Action::DragMove) == 2);
		CHECK(Count(a, Action::DragEnd) == 1);
		CHECK(Count(a, Action::LeftClick) == 0);
		CHECK(a.front().x == 10 && a.back().x == 90);
		CHECK(!a.front().box && !a.back().box); // plain drag = camera pan in the engine
	}
	{ // two-finger tap -> right click at centroid
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.FingerDown(2, 200, 100, 0.02);
		g.FingerUp(1, 100, 100, 0.15);
		g.FingerUp(2, 200, 100, 0.16);
		auto a = g.Poll();
		CHECK(a.size() == 1 && a[0].type == Action::RightClick && a[0].x == 150 && a[0].y == 100);
	}
	{ // two-finger pan
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.FingerDown(2, 200, 100, 0.0);
		for (int i = 1; i <= 10; ++i)
		{
			g.FingerMotion(1, 100, 100 + i * 5, i * 0.02);
			g.FingerMotion(2, 200, 100 + i * 5, i * 0.02);
		}
		g.FingerUp(1, 100, 150, 0.3);
		g.FingerUp(2, 200, 150, 0.3);
		auto a = g.Poll();
		float dy = 0;
		for (const Action& x : a)
			if (x.type == Action::Pan)
				dy += x.dy;
		CHECK(Count(a, Action::Pan) > 0);
		CHECK(Count(a, Action::Zoom) == 0);
		CHECK(Count(a, Action::RightClick) == 0);
		CHECK(Count(a, Action::LeftClick) == 0);
		CHECK(dy > 35 && dy <= 50);
	}
	{ // pinch out -> zoom > 1
		touch::Gestures g;
		g.FingerDown(1, 100, 100, 0.0);
		g.FingerDown(2, 200, 100, 0.0);
		for (int i = 1; i <= 10; ++i)
		{
			g.FingerMotion(1, 100 - i * 5, 100, i * 0.02);
			g.FingerMotion(2, 200 + i * 5, 100, i * 0.02);
		}
		auto a = g.Poll();
		float s = 1;
		for (const Action& x : a)
			if (x.type == Action::Zoom)
				s *= x.scale;
		CHECK(Count(a, Action::Zoom) > 0);
		CHECK(std::fabs(s - 2.0f) < 0.15f); // 100 -> 200 px spread
		CHECK(Count(a, Action::Pan) == 0);
	}
	{ // drag then second finger -> drag end, then pan
		touch::Gestures g;
		g.FingerDown(1, 10, 10, 0.0);
		g.FingerMotion(1, 60, 10, 0.1);
		g.FingerDown(2, 100, 10, 0.2);
		g.FingerMotion(1, 60, 40, 0.3);
		g.FingerMotion(2, 100, 40, 0.3);
		auto a = g.Poll();
		CHECK(Count(a, Action::DragEnd) == 1);
		CHECK(Count(a, Action::Pan) > 0);
	}
	{ // third finger ignored, cancel resets
		touch::Gestures g;
		g.FingerDown(1, 0, 0, 0);
		g.FingerDown(2, 10, 0, 0);
		g.FingerDown(3, 20, 0, 0);
		CHECK(g.ActiveFingers() == 2);
		g.Cancel();
		CHECK(g.ActiveFingers() == 0);
		g.FingerDown(4, 5, 5, 1.0);
		g.FingerUp(4, 5, 5, 1.1);
		auto a = g.Poll();
		CHECK(a.size() == 1 && a[0].type == Action::LeftClick);
	}
	if (g_Fail)
	{
		std::printf("%d check(s) failed\n", g_Fail);
		return 1;
	}
	std::printf("All touch gesture tests passed\n");
	return 0;
}
