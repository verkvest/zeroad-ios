#!/usr/bin/env python3
"""Builds the small "ios" mod that sits on top of "public": a copy of 0 A.D.'s own
gui/session/input.js (GPL-2.0+, (c) Wildfire Games) with a touch hook added, so that
a tap with own units selected issues the context command (move / attack / gather /
build ...), exactly like a right click on desktop.
Usage: make-ios-mod.py <public.zip> <out-mod-dir>"""
import json, os, re, sys, zipfile

src, out = sys.argv[1], sys.argv[2]
ZIP = zipfile.ZipFile(src)
js = ZIP.read("gui/session/input.js").decode("utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))


def write(rel, text):
    path = os.path.join(out, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def patch(text, old, new, what):
    assert text.count(old) == 1, what + ": anchor not found"
    return text.replace(old, new)

HOOK_FN = r'''
// --- iOS port: touch taps ------------------------------------------------------------
// The engine marks synthesized left clicks that come from a finger tap with ev.touchtap.
// With own units selected, a tap on anything that is not one of our own entities is
// turned into a right click, i.e. the context command (move, attack, gather, build...).
// Tapping an own unit/building still selects it; long-press is always a right click.
var g_TouchTapAsCommand = false;

function touchTapToCommand(ev)
{
	if ((ev.type != "mousebuttondown" && ev.type != "mousebuttonup") || ev.button != SDL_BUTTON_LEFT)
		return;
	if (ev.type == "mousebuttonup")
	{
		if (g_TouchTapAsCommand)
			ev.button = SDL_BUTTON_RIGHT;
		g_TouchTapAsCommand = false;
		return;
	}
	g_TouchTapAsCommand = false;
	if (!ev.touchtap || inputState != INPUT_NORMAL || !g_Selection.size() || !controlsPlayer(g_ViewedPlayer))
		return;
	if (!g_Selection.toList().every(ownsEntity))
		return;
	const target = Engine.PickEntityAtPoint(ev.x, ev.y);
	if (target != INVALID_ENTITY && ownsEntity(target))
		return;
	const action = determineAction(ev.x, ev.y);
	if (!action || action.type == "none")
		return;
	ev.button = SDL_BUTTON_RIGHT;
	g_TouchTapAsCommand = true;
	log("iOS touch: tap -> command '" + action.type + "' for " + g_Selection.size() + " selected");
}
// --------------------------------------------------------------------------------------

'''
anchor = "function handleInputAfterGui(ev)\n{\n"
assert js.count(anchor) == 1, "handleInputAfterGui not found"
js = js.replace(anchor, HOOK_FN.lstrip("\n") + anchor + "\ttouchTapToCommand(ev);\n\n")
# The GUI is laid out inside the safe area (engine patch 0010): convert the screen
# coordinates of the selection band box into GUI units relative to that area.
js = patch(js, """	const scale = +Engine.ConfigDB_GetValue("user", "gui.scale");
	const vMin = Vector2D.min(g_DragStart, ev);
	const vMax = Vector2D.max(g_DragStart, ev);

	bandbox.size = {
		"left": vMin.x / scale,
		"top": vMin.y / scale,
		"right": vMax.x / scale,
		"bottom": vMax.y / scale
	};""", """	const scale = +(Engine.ConfigDB_GetValue("user", "ios.gui.scale") || Engine.ConfigDB_GetValue("user", "gui.scale"));
	const insetLeft = +(Engine.ConfigDB_GetValue("user", "ios.gui.insetleft") || 0);
	const insetTop = +(Engine.ConfigDB_GetValue("user", "ios.gui.insettop") || 0);
	const vMin = Vector2D.min(g_DragStart, ev);
	const vMax = Vector2D.max(g_DragStart, ev);

	bandbox.size = {
		"left": vMin.x / scale - insetLeft,
		"top": vMin.y / scale - insetTop,
		"right": vMax.x / scale - insetLeft,
		"bottom": vMax.y / scale - insetTop
	};""", "updateBandbox")
# Fat-finger tolerance: a tap that misses every unit retries in two rings around the point.
js = js.replace("Engine.PickEntityAtPoint(", "iosPickEntityAtPoint(")
js = js.replace(HOOK_FN.lstrip("\n")[:40], """// --- iOS port: tap tolerance --------------------------------------------------------
function iosPickEntityAtPoint(x, y)
{
	const ent = Engine.PickEntityAtPoint(x, y);
	if (ent)
		return ent;
	const scale = +(Engine.ConfigDB_GetValue("user", "ios.gui.scale") || 1);
	const radius = +(Engine.ConfigDB_GetValue("user", "ios.taptolerance") || 16) * scale;
	for (const r of [radius / 2, radius])
		for (let a = 0; a < 8; ++a)
		{
			const hit = Engine.PickEntityAtPoint(Math.round(x + r * Math.cos(a * Math.PI / 4)), Math.round(y + r * Math.sin(a * Math.PI / 4)));
			if (hit)
				return hit;
		}
	return 0;
}

""" + HOOK_FN.lstrip("\n")[:40], 1)
write("gui/session/input.js", js)

# --- Main menu: one-tap "Quick Play vs AI" ----------------------------------------------
items = ZIP.read("gui/pregame/MainMenuItems.js").decode("utf-8")
items = patch(items, "export const mainMenuItems = [\n", """export const mainMenuItems = [
	// iOS port: start a 1v1 skirmish against an easy AI in one tap.
	{
		"caption": translate("Quick Play vs AI"),
		"tooltip": translate("Start a 1v1 skirmish on a small map against an easy computer opponent."),
		"onPress": () => {
			Engine.SwitchGuiPage("page_ios_quickplay.xml");
		}
	},
""", "mainMenuItems")
write("gui/pregame/MainMenuItems.js", items)

mainmenu = ZIP.read("gui/pregame/mainmenu.js").decode("utf-8")
mainmenu = patch(mainmenu, """	Engine.GetGUIObjectByName("userReport").onTick = updateUserReportStatus;
""", """	Engine.GetGUIObjectByName("userReport").onTick = updateUserReportStatus;

	// iOS port CI self-test: press "Quick Play vs AI" automatically.
	if (Engine.ConfigDB_GetValue("user", "ios.autoquickplay") == "true")
	{
		let ticks = 0;
		Engine.GetGUIObjectByName("userReport").onTick = () => {
			updateUserReportStatus();
			if (++ticks == 120)
			{
				log("iOS: auto quick play");
				Engine.SwitchGuiPage("page_ios_quickplay.xml");
			}
		};
	}
""", "mainmenu init")
write("gui/pregame/mainmenu.js", mainmenu)

# --- Phone HUD: enlarge the desktop session panels ------------------------------------
import re

def scale_sizes(text, k, attrs=("size",)):
    """Multiply every pixel offset (not the percentages) in size="..." attributes by k."""
    def tok(t):
        m = re.match(r"^(-?\d+(?:\.\d+)?%)?([+-]?\d+(?:\.\d+)?)?$", t)
        if not m or not m.group(2):
            return t
        v = int(round(float(m.group(2)) * k))
        return (m.group(1) or "") + (("+" if v >= 0 else "") + str(v) if m.group(1) else str(v))
    def fix(value):
        return " ".join(tok(t) for t in value.split())
    for attr in attrs:
        text = re.sub(r'(\s%s=")([^"]*)(")' % attr, lambda m: m.group(1) + fix(m.group(2)) + m.group(3), text)
    return text

ICON_K = 2.2  # 38px desktop icons -> 84 GUI units = 56pt at the phone GUI scale (2.0 on 3x)
TOP_K = 1.4
names = ZIP.namelist()
for name in names:
    if re.match(r"gui/session/selection_panels_(left|right)/[^/]+\.xml$", name) or name in (
            "gui/session/selection_panels_middle/unit_commands.xml",
            "gui/session/selection_panels_middle/multiple_details_area.xml"):
        write(name, scale_sizes(ZIP.read(name).decode("utf-8"), ICON_K))
for name in names:
    if re.match(r"gui/session/top_panel/(IconButtons/)?[^/]+\.xml$", name) or name in (
            "gui/session/TopPanel.xml", "gui/session/PanelEntities.xml"):
        text = scale_sizes(ZIP.read(name).decode("utf-8"), TOP_K)
        if name.endswith("Counters.xml"):
            text = patch(text, 'size="0 0 50%-199 100%" name="resourceCounts"', 'size="0 0 100%-430 100%" name="resourceCounts"', "counters")
        write(name, text)
# In-game menu: 54-unit (36pt) items, wider panel, bigger font (all items fit in 603 units).
menu = ZIP.read("gui/session/Menu.xml").decode("utf-8")
menu = patch(menu, 'size="100%-164 0 100% 0"', 'size="100%-300 0 100% 0"', "menu panel")
menu = patch(menu, 'size="4 4 100%-4 32"', 'size="4 4 100%-4 54"\n\t\t\tfont="sans-bold-20"', "menu button")
write("gui/session/Menu.xml", menu)
single = ZIP.read("gui/session/selection_panels_middle/single_details_area.xml").decode("utf-8")
write("gui/session/selection_panels_middle/single_details_area.xml",
      patch(single, 'size="4 4 100%-4 100%-44"', 'size="4 4 100%-4 100%-92"', "single details"))

# Paged 6-column build / train grid (ios_hud.js): let iosPanelPosition place those buttons.
uc = ZIP.read("gui/session/unit_commands.js").decode("utf-8")
uc = patch(uc, "function setPanelObjectPosition(object, index, rowLength, vMargin = 1, hMargin = 1)\n{\n",
           "function setPanelObjectPosition(object, index, rowLength, vMargin = 1, hMargin = 1)\n{\n"
           "\tif (typeof iosPanelPosition == \"function\" && iosPanelPosition(object, index, rowLength))\n\t\treturn;\n",
           "setPanelObjectPosition")
write("gui/session/unit_commands.js", uc)
styles = ZIP.read("gui/session/styles.xml").decode("utf-8")
styles = patch(styles, '<style name="resourceText"\n\t\ttextcolor="white"\n\t\tfont="sans-bold-stroke-14"',
               '<style name="resourceText"\n\t\ttextcolor="white"\n\t\tfont="sans-bold-stroke-20"', "resourceText")
styles = patch(styles, '<style name="gathererCounts"\n\t\ttextcolor="200 200 200"\n\t\tfont="sans-bold-stroke-13"',
               '<style name="gathererCounts"\n\t\ttextcolor="200 200 200"\n\t\tfont="sans-bold-stroke-16"', "gathererCounts")
write("gui/session/styles.xml", styles)

# Main menu: taller buttons with a bigger font, wider panel.
handler = ZIP.read("gui/pregame/MainMenuItemHandler.js").decode("utf-8")
handler = patch(handler, "MainMenuItemHandler.prototype.ButtonHeight = 28;", "MainMenuItemHandler.prototype.ButtonHeight = 44;", "ButtonHeight")
handler = patch(handler, "MainMenuItemHandler.prototype.Margin = 4;", "MainMenuItemHandler.prototype.Margin = 5;", "Margin")
write("gui/pregame/MainMenuItemHandler.js", handler)
panel = ZIP.read("gui/pregame/menupanel.xml").decode("utf-8")
panel = patch(panel, 'size="60 -2 300 100%+2" z="50"', 'size="40 -2 380 100%+2" z="50"', "mainMenu size")
panel = patch(panel, '<object name="mainMenuButtons" size="8 146 100%-8 346" z="60">', '<object name="mainMenuButtons" size="10 146 100%-10 100%-4" z="60">', "buttons size")
panel = patch(panel, '<object name="mainMenuButton[n]" type="button" style="StoneButtonFancy" tooltip_style="pgToolTip"/>',
              '<object name="mainMenuButton[n]" type="button" style="StoneButtonFancy" font="sans-bold-20" tooltip_style="pgToolTip"/>', "button font")
panel = patch(panel, '<object type="button" style="StoneButtonFancy" tooltip_style="pgToolTip"/>',
              '<object type="button" style="StoneButtonFancy" font="sans-bold-20" tooltip_style="pgToolTip"/>', "submenu font")
panel = patch(panel, 'style="SubmenuPanel" size="60 0 300 0%"', 'style="SubmenuPanel" size="40 0 380 0%"', "submenu size")
write("gui/pregame/menupanel.xml", panel)

for name in ("page_ios_quickplay.xml", "ios_quickplay/quickplay.xml", "ios_quickplay/quickplay.js",
             "session/session_objects/ios_toolbar.xml", "session/ios_toolbar.js", "session/ios_hud.js"):
    write("gui/" + name, open(os.path.join(HERE, "mod", "gui", name), encoding="utf-8").read())
# --- Dialogs: fit the phone screen (~1125 x 603 GUI units inside the safe area) and make the
# close / back / cancel buttons at least 66 units (44pt) tall, growing upwards from their bottom edge.
MAX_HALF_W, MAX_HALF_H, MIN_BUTTON_H = 545, 292, 66


def current(name):
    path = os.path.join(out, name)
    if os.path.exists(path):
        return open(path, encoding="utf-8").read()
    return ZIP.read(name).decode("utf-8")


def clamp_dialog(m):
    a, b, c, d = (int(m.group(i)) for i in range(1, 5))
    kx = min(1.0, MAX_HALF_W / max(a, c))
    ky = min(1.0, MAX_HALF_H / max(b, d))
    if kx == 1.0 and ky == 1.0:
        return m.group(0)
    return 'size="50%%-%d 50%%-%d 50%%+%d 50%%+%d"' % (a * kx, b * ky, c * kx, d * ky)


def split_offset(t):
    m = re.match(r"^(-?\d+(?:\.\d+)?%)?([+-]?\d+(?:\.\d+)?)?$", t)
    if not m:
        return None
    return m.group(1) or "", float(m.group(2) or 0)


CLOSE_CAPTION = re.compile(r'<translatableAttribute id="caption"[^>]*>\s*(Close|Back|Cancel|Quit|Return|Exit|OK|Main Menu)\s*<')


def grow_close_buttons(text):
    count = 0

    def fix(m):
        nonlocal count
        tag = m.group(0)
        if 'type="button"' not in tag:
            return tag
        after = text[m.end():m.end() + 400]
        after = after.split("<object", 1)[0]
        name = re.search(r'name="([^"]*)"', tag)
        if not ('hotkey="cancel"' in tag or (name and re.search(r"close|cancel|back|quit|exit|continue|replay", name.group(1), re.I))
                or CLOSE_CAPTION.search(after)):
            return tag
        size = re.search(r'size="([^"]*)"', tag)
        if not size:
            return tag
        parts = size.group(1).split()
        if len(parts) != 4:
            return tag
        top, bottom = split_offset(parts[1]), split_offset(parts[3])
        if not top or not bottom or top[0] != bottom[0] or bottom[1] - top[1] >= MIN_BUTTON_H:
            return tag
        v = bottom[1] - MIN_BUTTON_H
        parts[1] = bottom[0] + (("+" if v >= 0 else "") if bottom[0] else "") + str(int(v))
        count += 1
        return tag.replace(size.group(0), 'size="%s"' % " ".join(parts))

    text = re.sub(r"<object\b[^>]*>", fix, text)
    return text, count


dialogs = buttons = 0
for name in names:
    if not (name.startswith("gui/") and name.endswith(".xml")):
        continue
    text = current(name)
    new = re.sub(r'size="50%-(\d+) 50%-(\d+) 50%\+(\d+) 50%\+(\d+)"', clamp_dialog, text)
    # Credits: full height with a fixed half width of 473.
    new = new.replace('size="50%-473 24 50%+473 100%-24"', 'size="50%-545 8 50%+545 100%-8"')
    dialogs += new != text
    new, n = grow_close_buttons(new)
    buttons += n
    if new != text:
        write(name, new)
print("dialogs: %d files clamped to the phone screen, %d close buttons enlarged" % (dialogs, buttons))

json.dump({
    "name": "ios",
    "version": "0.28.0",
    "label": "0 A.D. iOS touch controls and phone layout",
    "url": "https://github.com/verkvest/zeroad-ios",
    "description": "iOS port: touch controls (tap = command with units selected), on-screen command buttons, Quick Play. Based on 0 A.D. GUI code (GPL-2.0+, (c) Wildfire Games).",
    "dependencies": ["0ad=0.28.0"],
}, open(os.path.join(out, "mod.json"), "w"), indent="\t")
print("ios mod written to", out)
