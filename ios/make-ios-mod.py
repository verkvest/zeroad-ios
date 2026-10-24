#!/usr/bin/env python3
"""Builds the small "ios" mod that sits on top of "public": a copy of 0 A.D.'s own
gui/session/input.js (GPL-2.0+, (c) Wildfire Games) with a touch hook added, so that
a tap with own units selected issues the context command (move / attack / gather /
build ...), exactly like a right click on desktop.
Usage: make-ios-mod.py <public.zip> <out-mod-dir>"""
import json, os, sys, zipfile

src, out = sys.argv[1], sys.argv[2]
js = zipfile.ZipFile(src).read("gui/session/input.js").decode("utf-8")

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
os.makedirs(os.path.join(out, "gui", "session"), exist_ok=True)
open(os.path.join(out, "gui", "session", "input.js"), "w", encoding="utf-8").write(js)
json.dump({
    "name": "ios",
    "version": "0.28.0",
    "label": "0 A.D. iOS touch controls",
    "url": "https://github.com/verkvest/zeroad-ios",
    "description": "Touch controls for the iOS port (tap = command with units selected).",
    "dependencies": ["0ad=0.28.0"],
}, open(os.path.join(out, "mod.json"), "w"), indent="\t")
print("ios mod written to", out)
