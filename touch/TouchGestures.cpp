/* Copyright (C) 2026 verkvest. Licensed under GPLv2 or later (same as 0 A.D.). */
#include "TouchGestures.h"

#include <cmath>

namespace touch
{

static float Dist(float ax, float ay, float bx, float by)
{
	return std::sqrt((ax - bx) * (ax - bx) + (ay - by) * (ay - by));
}

Gestures::Finger* Gestures::Find(int64_t id)
{
	for (Finger& f : m_Fingers)
		if (f.down && f.id == id)
			return &f;
	return nullptr;
}

Gestures::Finger* Gestures::Alloc(int64_t id)
{
	for (Finger& f : m_Fingers)
		if (!f.down)
		{
			f = Finger();
			f.down = true;
			f.id = id;
			return &f;
		}
	return nullptr;
}

int Gestures::ActiveFingers() const
{
	int n = 0;
	for (const Finger& f : m_Fingers)
		n += f.down ? 1 : 0;
	return n;
}

void Gestures::Centroid(float& cx, float& cy) const
{
	cx = cy = 0;
	int n = 0;
	for (const Finger& f : m_Fingers)
		if (f.down)
		{
			cx += f.x;
			cy += f.y;
			++n;
		}
	if (n)
	{
		cx /= n;
		cy /= n;
	}
}

float Gestures::Spread() const
{
	float d = Dist(m_Fingers[0].x, m_Fingers[0].y, m_Fingers[1].x, m_Fingers[1].y);
	return d < 1.f ? 1.f : d;
}

void Gestures::Emit(Action::Type type, float x, float y, bool box)
{
	Action a;
	a.type = type;
	a.x = x;
	a.y = y;
	a.box = box;
	m_Actions.push_back(a);
}

void Gestures::FingerDown(int64_t id, float x, float y, double t)
{
	if (Find(id))
		return;
	Finger* f = Alloc(id);
	if (!f)
		return; // 3rd+ finger: ignored
	f->x = f->startX = x;
	f->y = f->startY = y;

	switch (m_State)
	{
	case IDLE:
		m_State = ONE_PENDING;
		m_StartTime = t;
		break;
	case ONE_PENDING:
	case ONE_ARMED:
	case ONE_DRAG:
	{
		if (m_State == ONE_DRAG)
		{
			// Turning a drag into a two-finger gesture: release the drag first.
			for (const Finger& o : m_Fingers)
				if (o.down && o.id != id)
					Emit(Action::DragEnd, o.x, o.y, m_DragBox);
		}
		m_State = TWO;
		m_StartTime = t;
		Centroid(m_StartCx, m_StartCy);
		m_LastCx = m_StartCx;
		m_LastCy = m_StartCy;
		m_StartSpread = m_LastSpread = Spread();
		m_Panning = m_Pinching = false;
		break;
	}
	case TWO:
	case ENDING:
		break;
	}
}

void Gestures::FingerMotion(int64_t id, float x, float y, double t)
{
	// A long press may have elapsed without an Update() call in between (slow frame).
	Update(t);
	Finger* f = Find(id);
	if (!f)
		return;
	f->x = x;
	f->y = y;

	switch (m_State)
	{
	case ONE_PENDING:
	case ONE_ARMED:
		if (Dist(x, y, f->startX, f->startY) > m_Cfg.tapMaxMove)
		{
			m_DragBox = m_State == ONE_ARMED;
			m_State = ONE_DRAG;
			Emit(Action::DragStart, f->startX, f->startY, m_DragBox);
			Emit(Action::DragMove, x, y, m_DragBox);
		}
		break;
	case ONE_DRAG:
		Emit(Action::DragMove, x, y, m_DragBox);
		break;
	case TWO:
	{
		float cx, cy;
		Centroid(cx, cy);
		const float spread = Spread();
		if (!m_Panning && Dist(cx, cy, m_StartCx, m_StartCy) > m_Cfg.panThreshold)
			m_Panning = true;
		if (!m_Pinching && std::fabs(spread / m_StartSpread - 1.f) > m_Cfg.pinchThreshold)
			m_Pinching = true;
		if (m_Panning && (cx != m_LastCx || cy != m_LastCy))
		{
			Action a;
			a.type = Action::Pan;
			a.x = cx;
			a.y = cy;
			a.dx = cx - m_LastCx;
			a.dy = cy - m_LastCy;
			m_Actions.push_back(a);
		}
		if (m_Pinching && spread != m_LastSpread)
		{
			Action a;
			a.type = Action::Zoom;
			a.x = cx;
			a.y = cy;
			a.scale = spread / m_LastSpread;
			m_Actions.push_back(a);
		}
		m_LastCx = cx;
		m_LastCy = cy;
		m_LastSpread = spread;
		break;
	}
	case IDLE:
	case ENDING:
		break;
	}
}

void Gestures::FingerUp(int64_t id, float x, float y, double t)
{
	Update(t);
	Finger* f = Find(id);
	if (!f)
		return;
	f->x = x;
	f->y = y;

	switch (m_State)
	{
	case ONE_PENDING:
		if (t - m_StartTime < m_Cfg.longPressTime && Dist(x, y, f->startX, f->startY) <= m_Cfg.tapMaxMove)
			Emit(Action::LeftClick, f->startX, f->startY);
		break;
	case ONE_ARMED:
		Emit(Action::RightClick, f->startX, f->startY);
		break;
	case ONE_DRAG:
		Emit(Action::DragEnd, x, y, m_DragBox);
		break;
	case TWO:
	{
		float cx, cy;
		Centroid(cx, cy);
		const bool still = !m_Panning && !m_Pinching &&
			Dist(cx, cy, m_StartCx, m_StartCy) <= m_Cfg.twoFingerTapMaxMove &&
			std::fabs(Spread() - m_StartSpread) <= m_Cfg.twoFingerTapMaxMove;
		if (still && t - m_StartTime <= m_Cfg.twoFingerTapMaxTime)
			Emit(Action::RightClick, m_StartCx, m_StartCy);
		break;
	}
	case IDLE:
	case ENDING:
		break;
	}

	f->down = false;
	m_State = ActiveFingers() == 0 ? IDLE : ENDING;
}

void Gestures::Update(double t)
{
	if (m_State != ONE_PENDING || t - m_StartTime < m_Cfg.longPressTime)
		return;
	for (const Finger& f : m_Fingers)
		if (f.down)
		{
			Emit(Action::LongPressArmed, f.startX, f.startY);
			break;
		}
	m_State = ONE_ARMED;
}

void Gestures::Cancel()
{
	if (m_State == ONE_DRAG)
		for (const Finger& f : m_Fingers)
			if (f.down)
				Emit(Action::DragEnd, f.x, f.y, m_DragBox);
	for (Finger& f : m_Fingers)
		f.down = false;
	m_State = IDLE;
}

std::vector<Action> Gestures::Poll()
{
	std::vector<Action> out;
	out.swap(m_Actions);
	return out;
}

} // namespace touch
