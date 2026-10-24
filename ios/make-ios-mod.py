#!/usr/bin/env python3
"""Builds the small "ios" mod that sits on top of "public": a copy of 0 A.D.'s own
gui/session/input.js (GPL-2.0+, (c) Wildfire Games) with a touch hook added, so that
a tap with own units selected issues the context command (move / attack / gather /
build ...), exactly like a right click on desktop.
Usage: make-ios-mod.py <public.zip> <out-mod-dir>"""
import json, os, sys, zipfile

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

for name in ("page_ios_quickplay.xml", "ios_quickplay/quickplay.xml", "ios_quickplay/quickplay.js",
             "session/session_objects/ios_toolbar.xml", "session/ios_toolbar.js"):
    write("gui/" + name, open(os.path.join(HERE, "mod", "gui", name), encoding="utf-8").read())
json.dump({
    "name": "ios",
    "version": "0.28.0",
    "label": "0 A.D. iOS touch controls and phone layout",
    "url": "https://github.com/verkvest/zeroad-ios",
    "description": "iOS port: touch controls (tap = command with units selected), on-screen command buttons, Quick Play. Based on 0 A.D. GUI code (GPL-2.0+, (c) Wildfire Games).",
    "dependencies": ["0ad=0.28.0"],
}, open(os.path.join(out, "mod.json"), "w"), indent="\t")
print("ios mod written to", out)
