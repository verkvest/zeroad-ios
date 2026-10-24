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
# Neutral title shown instead of the "0 A.D. Empires Ascendant" logo in the main menu
# (App Store trademark caution). Change it here (or set IOS_APP_TITLE) to the final app name.
APP_TITLE = os.environ.get("IOS_APP_TITLE", "Bronze Legions")


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
items = patch(items, '\t{\n\t\t"caption": translate("Scenario Editor"),', '\t{\n\t\t"iosHidden": true,\n\t\t"caption": translate("Scenario Editor"),', "hide editor")
items = patch(items, '\t\t\t\t"caption": translate("Welcome Screen"),', '\t\t\t\t"iosHidden": true,\n\t\t\t\t"caption": translate("Welcome Screen"),', "hide welcome")
# Apple review: apps must not offer a "quit" button on iOS.
items = patch(items, '\t{\n\t\t"caption": translate("Exit"),', '\t{\n\t\t"iosHidden": true,\n\t\t"caption": translate("Exit"),', "hide exit")
write("gui/pregame/MainMenuItems.js", items)

mainmenu = ZIP.read("gui/pregame/mainmenu.js").decode("utf-8")
mainmenu = patch(mainmenu, """	Engine.GetGUIObjectByName("userReport").onTick = updateUserReportStatus;
""", """	Engine.GetGUIObjectByName("userReport").onTick = updateUserReportStatus;

	// iOS port: no user-report panel on phones.
	Engine.GetGUIObjectByName("userReport").size = "-2000 -2000 -1700 -1850";

	// iOS port CI self-test: open the Single-player submenu, then the game setup page.
	if (Engine.ConfigDB_GetValue("user", "ios.menutest") == "true")
	{
		const start = Date.now();
		let step = 0;
		Engine.GetGUIObjectByName("userReport").onTick = () => {
			const t = (Date.now() - start) / 1000;
			if (step == 0 && t > 15)
			{
				++step;
				const button = Engine.GetGUIObjectByName("mainMenuButtons").children.find(b => !b.hidden && b.caption == translate("Single-player"));
				log("iOS menutest: open Single-player submenu");
				if (button)
					button.onPress();
			}
			else if (step == 1 && t > 40)
			{
				++step;
				log("iOS menutest: open game setup");
				Engine.SwitchGuiPage("page_gamesetup.xml");
			}
		};
	}

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

BG_OLD = '\t\t\tconst right = backgroundsSize.right / 2 + offset;\n\t\t\tthis.background.size = {\n\t\t\t\t"left": right - height,\n\t\t\t\t"top": backgroundsSize.top,\n\t\t\t\t"right": right + height,\n\t\t\t\t"bottom": backgroundsSize.bottom\n\t\t\t};\n'
BG_NEW = '\t\t\t// iOS port: scale up so a 19.5:9 screen is always covered.\n\t\t\tconst k = Math.max(1, 0.75 * (backgroundsSize.right - backgroundsSize.left) / height);\n\t\t\tconst right = backgroundsSize.right / 2 + offset;\n\t\t\tthis.background.size = {\n\t\t\t\t"left": right - height * k,\n\t\t\t\t"top": backgroundsSize.top - height * (k - 1) / 2,\n\t\t\t\t"right": right + height * k,\n\t\t\t\t"bottom": backgroundsSize.bottom + height * (k - 1) / 2\n\t\t\t};\n'
# Main menu (phone landscape): left panel with the logo and two columns of 72-unit (48pt)
# buttons, submenu to its right (ios/mod/gui/pregame/MainMenuItemHandler.js), no clutter.
panel = ZIP.read("gui/pregame/menupanel.xml").decode("utf-8")
panel = patch(panel, 'size="100%-313 25 100% 200"', 'size="100%-440 8 100%-8 220"', "tooltip size")
panel = patch(panel, 'size="60 -2 300 100%+2" z="50"', 'size="8 -2 508 100%+2" z="50"', "mainMenu size")
panel = patch(panel, '<object name="mainMenuButtons" size="8 146 100%-8 346" z="60">', '<object name="mainMenuButtons" size="12 84 100%-12 100%-30" z="60">', "buttons size")
panel = patch(panel, '<object name="mainMenuButton[n]" type="button" style="StoneButtonFancy" tooltip_style="pgToolTip"/>',
              '<object name="mainMenuButton[n]" type="button" style="StoneButtonFancy" font="sans-bold-20" tooltip_style="pgToolTip"/>', "button font")
panel = patch(panel, '<object type="button" style="StoneButtonFancy" tooltip_style="pgToolTip"/>',
              '<object type="button" style="StoneButtonFancy" font="sans-bold-20" tooltip_style="pgToolTip"/>', "submenu font")
panel = patch(panel, 'style="SubmenuPanel" size="60 0 300 0%"', 'style="SubmenuPanel" size="520 0 900 0%" z="60"', "submenu size")
panel = patch(panel, '<object name="submenuButtons" type="image" size="0 4 100%-4 100%-4"', '<object name="submenuButtons" type="image" size="6 6 100%-6 100%-6"', "submenu buttons")
write("gui/pregame/menupanel.xml", panel)
info = ZIP.read("gui/pregame/ProjectInformation.xml").decode("utf-8")
info = patch(info, '<object name="productLogo" type="image" ghost="true" size="50%-110 10 50%+110 110"/>',
             '<object name="productLogo" type="text" ghost="true" size="8 6 100%-8 80" font="sans-bold-stroke-40" textcolor="255 222 150" text_align="center" text_valign="center"/>', "logo")
info = patch(info, '<object type="image" style="TranslucentPanelThinBorder" size="8 100%-368 100%-8 100%-94">',
             '<object type="image" style="TranslucentPanelThinBorder" size="8 100%-368 100%-8 100%-94" hidden="true">', "description")
info = patch(info, '<object size="4 100%-84 100%-4 100%-56" ghost="true">', '<object size="4 100%-84 100%-4 100%-56" ghost="true" hidden="true">', "organization")
info = patch(info, 'name="productBuild" style="MediumTitleText" ghost="true" size="50%-128 100%-36 50%+128 100%"',
             'name="productBuild" style="MediumTitleText" ghost="true" size="8 100%-28 100%-8 100%-2"', "build")
write("gui/pregame/ProjectInformation.xml", info)
pinfo = ZIP.read("gui/pregame/ProjectInformation.js").decode("utf-8")
pinfo = patch(pinfo, '\t"productLogo": {\n\t\t"sprite": "0ADLogo"\n\t},', '\t"productLogo": {\n\t\t"caption": %s\n\t},' % json.dumps(APP_TITLE), "title")
write("gui/pregame/ProjectInformation.js", pinfo)
# No product logo as an empty-state placeholder in the load-game and replay pages either.
for name, old in (("gui/loadgame/load.xml", '<object name="invalidGame" size="650 105 870 205" type="image" sprite="0ADLogo" />'),
                  ("gui/replaymenu/replay_menu.xml", '<object name="logo" size="50%-110 40 50%+110 140" type="image" sprite="0ADLogo"/>')):
    write(name, patch(ZIP.read(name).decode("utf-8"), old, old.replace('sprite="0ADLogo"', 'sprite=""'), name))
# No welcome splash screen on phones (its desktop layout does not fit).
splash = ZIP.read("gui/pregame/SplashscreenHandler.js").decode("utf-8")
splash = patch(splash, "\t\tif (this.showSplashScreen)\n\t\t\tthis.openPage();", "\t\t// iOS port: no welcome screen.", "splash")
write("gui/pregame/SplashscreenHandler.js", splash)
# Background layers: 2 x height wide on desktop leaves the edges visible on a 19.5:9 phone.
bg = ZIP.read("gui/pregame/BackgroundHandler.js").decode("utf-8")
bg = patch(bg, BG_OLD, BG_NEW, "background")
bg = patch(bg, """				"left": left,
				"top": backgroundsSize.top,
				"right": backgroundsSize.right,""", """				"left": left,
				"top": backgroundsSize.top,
				"right": backgroundsSize.right + 400, // iOS port: cover the right safe-area strip""", "background tiling")
write("gui/pregame/BackgroundHandler.js", bg)


for name in ("page_ios_quickplay.xml", "ios_quickplay/quickplay.xml", "ios_quickplay/quickplay.js",
             "session/session_objects/ios_toolbar.xml", "session/ios_toolbar.js", "session/ios_hud.js", "session/ios_shots.js",
             "pregame/MainMenuItemHandler.js"):
    write("gui/" + name, open(os.path.join(HERE, "mod", "gui", name), encoding="utf-8").read())
# --- Dialogs: fit the phone screen (~1125 x 603 GUI units inside the safe area) and make the
# close / back / cancel buttons at least 66 units (44pt) tall, growing upwards from their bottom edge.
MAX_HALF_W, MAX_HALF_H, MIN_BUTTON_H = 545, 292, 66


# Message boxes from the "mod" mod (mod.zip next to the public archive): fit the phone screen,
# 44pt buttons, and a tap on the faded background presses the first ("cancel") button.
MODZIP_PATH = os.path.join(os.path.dirname(os.path.abspath(src)), "mod.zip")
if os.path.exists(MODZIP_PATH):
    MODZIP = zipfile.ZipFile(MODZIP_PATH)
    util = MODZIP.read("gui/common/utilities.js").decode("utf-8")
    util = patch(util, '\tconst y1 = "100%-46";', '\tconst y1 = "100%-84"; // iOS port: 44pt buttons', "msgbox buttons")
    write("gui/common/utilities.js", util)
    mb = MODZIP.read("gui/msgbox/msgbox.xml").decode("utf-8")
    mb = patch(mb, '<object sprite="ModernFade" type="image"/>',
               '<object sprite="ModernFade" sprite_over="ModernFade" sprite_pressed="ModernFade" type="button">\n'
               '\t\t<action on="Press">const cancel = Engine.GetGUIObjectByName("mbCancelHotkey"); if (cancel.onPress) cancel.onPress();</action>\n'
               '\t</object>', "msgbox tap outside")
    mb = patch(mb, 'size="18 18 100%-18 100%-64"', 'size="18 18 100%-18 100%-92"', "msgbox text")
    write("gui/msgbox/msgbox.xml", mb)
    mbjs = MODZIP.read("gui/msgbox/msgbox.js").decode("utf-8")
    mbjs = patch(mbjs, "\tconst mbLRDiff = data.width / 2;\n\tconst mbUDDiff = data.height / 2;",
                 "\t// iOS port: room for 44pt buttons, never larger than the phone screen.\n"
                 "\tconst mbLRDiff = Math.min(data.width, 1090) / 2;\n"
                 "\tconst mbUDDiff = Math.min(data.height + 38, 584) / 2;", "msgbox size")
    write("gui/msgbox/msgbox.js", mbjs)
    print("msgbox: patched from", MODZIP_PATH)
else:
    print("msgbox: no mod.zip next to", src)

# Options page: full phone screen, title inside, 44pt bottom buttons, bigger tabs and rows,
# options laid out in two columns when a category has more than fit in one.
opt = ZIP.read("gui/options/options.xml").decode("utf-8")
opt = patch(opt, 'size="50%-400 50%-374 50%+400 50%+374"', 'size="50%-545 8 50%+545 100%-8"', "options size")
opt = patch(opt, 'type="text" size="50%-128 -16 50%+128 16"', 'type="text" size="50%-128 2 50%+128 30"', "options title")
opt = patch(opt, '<object size="15 16 230 100%-52">', '<object size="12 32 232 100%-84">', "options tabs")
opt = patch(opt, 'sprite="ModernDarkBoxGold" size="240 16 785 100%-52"', 'sprite="ModernDarkBoxGold" size="240 32 100%-12 100%-84"', "options controls")
for old, new in (("50%-339 100%-44 50%-177 100%-16", "12 100%-78 25%-6 100%-12"),
                 ("50%-167 100%-44 50%-5 100%-16", "25%+2 100%-78 50%-4 100%-12"),
                 ("50%+5 100%-44 50%+167 100%-16", "50%+4 100%-78 75%-2 100%-12"),
                 ("50%+177 100%-44 50%+339 100%-16", "75%+6 100%-78 100%-12 100%-12")):
    opt = patch(opt, 'size="%s"' % old, 'size="%s"' % new, "options button")
opt = patch(opt, '<object name="option_label[n]" size="0 0 65%-10 100%" type="text" style="ModernLeftLabelText"/>',
            '<object name="option_label[n]" size="0 0 65%-10 100%" type="text" style="ModernLeftLabelText" font="sans-bold-16"/>', "option label font")
write("gui/options/options.xml", opt)
ojs = ZIP.read("gui/options/options.js").decode("utf-8")
ojs = patch(ojs, "var g_TabButtonHeight = 34;", "var g_TabButtonHeight = 44; // iOS port", "tab height")
ojs = patch(ojs, "var g_OptionControlHeight = 26;", "var g_OptionControlHeight = 40; // iOS port", "row height")
ojs = patch(ojs, """		body.size.top = g_OptionControlOffset + i * (g_OptionControlHeight + g_OptionControlDist);
		body.size.bottom = body.size.top + g_OptionControlHeight;""", """		// iOS port: as many columns as needed to fit the phone screen.
		const area = Engine.GetGUIObjectByName("option_controls").getComputedSize();
		const perColumn = Math.max(1, Math.floor((area.bottom - area.top - 2 * g_OptionControlOffset) / (g_OptionControlHeight + g_OptionControlDist)));
		const count = g_Options[g_TabCategorySelected].options.length;
		const columns = Math.ceil(count / perColumn);
		const column = Math.floor(i / perColumn);
		const row = i % perColumn;
		body.size = {
			"left": 8,
			"rleft": 100 * column / columns,
			"right": -8,
			"rright": 100 * (column + 1) / columns,
			"top": g_OptionControlOffset + row * (g_OptionControlHeight + g_OptionControlDist),
			"bottom": g_OptionControlOffset + row * (g_OptionControlHeight + g_OptionControlDist) + g_OptionControlHeight
		};""", "option columns")
write("gui/options/options.js", ojs)
# Tab buttons: no keyboard / mouse-wheel hints in their tooltips on a phone.
tabs = ZIP.read("gui/common/tab_buttons.js").decode("utf-8")
i = tabs.index("\t\tbutton.tooltip = (categoriesData[category].tooltip")
j = tabs.index("\n\n", i)
tabs = tabs[:i] + "\t\t// iOS port: no keyboard hints.\n\t\tbutton.tooltip = categoriesData[category].tooltip || \"\";" + tabs[j:]
write("gui/common/tab_buttons.js", tabs)

# Game setup page on a 603-unit-high phone screen: lower top panel, smaller map preview,
# no tips panel, more room for the settings, 44pt Back / Start buttons.
gs = ZIP.read("gui/gamesetup/Pages/GameSetupPage/GameSetupPage.xml").decode("utf-8")
for old, new, what in (
        ('name="topPanel" size="24 40 100%-24 336"', 'name="topPanel" size="8 36 100%-8 232"', "top panel"),
        ('<object size="0 0 100%-416 100%">', '<object size="0 0 100%-282 100%">', "players"),
        ('<object size="100%-402 0 100% 100%">', '<object size="100%-272 0 100% 100%">', "map preview"),
        ('name="centerPanel" size="0 0 100% 100%-64"', 'name="centerPanel" size="0 0 100% 100%-80"', "center panel"),
        ('name="centerLeftPanel" size="24 0 100% 100%"', 'name="centerLeftPanel" size="8 0 100% 100%"', "center left"),
        ('<object size="0 346 100%-795-24 100%">', '<object size="0 240 100%-795-24 100%">', "chat"),
        ('<object size="0 370 500-24 560">', '<object size="0 370 500-24 560" hidden="true">', "tips"),
        ('name="centerCenterPanel" size="100%-315 346 100%-315 100%"', 'name="centerCenterPanel" size="100%-315 240 100%-315 100%"', "settings"),
        ('name="centerRightPanel" size="100%-315 346 100% 100%"', 'name="centerRightPanel" size="100%-315 240 100%-8 100%"', "tabs"),
        ('name="bottomPanel" size="0 0 100% 100%-22"', 'name="bottomPanel" size="0 0 100%-8 100%-8"', "bottom panel"),
        ('<object size="20 100%-32-10 100%-664 100%+9">', '<object size="8 100%-66 100%-664 100%">', "tooltip"),
        ('<object size="100%-656 100%-32 100%-486 100%">', '<object size="100%-656 100%-50 100%-486 100%-18">', "warning"),
        ('<object size="100%-470 100%-32 100%-330 100%">', '<object size="100%-470 100%-50 100%-330 100%-18">', "saved game"),
        ('name="bottomRightPanel" size="100%-314 100%-32 100% 100%"', 'name="bottomRightPanel" size="100%-314 100%-66 100% 100%"', "buttons"),
        ('<object size="0 0 140 100%">', '<object size="0 0 150 100%">', "cancel"),
        ('<object size="150 0 290 100%">', '<object size="158 0 100% 100%">', "start")):
    gs = patch(gs, old, new, "gamesetup " + what)
write("gui/gamesetup/Pages/GameSetupPage/GameSetupPage.xml", gs)
# The settings columns: the desktop panel slides out from under the tab column and its
# columns can stick out past the right edge on a phone. Lay them out in the room left of
# the tab column instead, every column inside the screen, and hide the panel with no tab.
gsp = ZIP.read("gui/gamesetup/Pages/GameSetupPage/Panels/GameSettingsPanel.js").decode("utf-8")
gsp += """
// iOS port (GPL-2.0+): deterministic settings layout that always fits left of the tab column.
GameSettingsPanel.prototype.positionSettings = function()
{
	const selectedTab = g_GameSettingsLayout[g_TabCategorySelected];
	this.settingsPanelFrame.hidden = !selectedTab;
	if (!selectedTab)
		return;
	const frames = [];
	for (const name of selectedTab.settings)
	{
		const frame = this.gameSettingControlManager.gameSettingControls[name].frame;
		if (!frame.hidden)
			frames.push(frame);
	}
	const centre = Engine.GetGUIObjectByName("centerCenterPanel").getComputedSize();
	const left = Engine.GetGUIObjectByName("centerLeftPanel").getComputedSize();
	const panel = this.settingsPanel.getComputedSize();
	const maxPerColumn = Math.max(1, Math.floor((panel.bottom - panel.top) / this.SettingHeight));
	const columns = Math.max(1, Math.ceil(frames.length / maxPerColumn));
	const perColumn = Math.max(1, Math.ceil(frames.length / columns));
	const columnWidth = Math.floor(Math.min(this.MaxColumnWidth, Math.max(150, centre.left - left.left - 8) / columns));
	frames.forEach((frame, i) => {
		const column = Math.floor(i / perColumn);
		const row = i % perColumn;
		frame.size = {
			"left": columnWidth * column,
			"top": this.SettingMarginBottom + row * this.SettingHeight,
			"right": columnWidth * (column + 1) - this.SettingMarginRight,
			"bottom": (row + 1) * this.SettingHeight
		};
	});
	this.settingsPanelFrame.size = (-columns * columnWidth) + " 0 0 100%";
};

GameSettingsPanel.prototype.onTick = function()
{
	delete this.settingsPanelFrame.onTick;
	this.lastTickTime = undefined;
	this.triggerResizeHandlers();
};
"""
write("gui/gamesetup/Pages/GameSetupPage/Panels/GameSettingsPanel.js", gsp)
# The map preview image has a fixed 400x293 size: fit it to its (smaller) box.
mp = ZIP.read("gui/gamesetup/Pages/GameSetupPage/Panels/MapPreview.xml").decode("utf-8")
mp = patch(mp, 'name="mapPreview" type="image" size="1 1 401 294"', 'name="mapPreview" type="image" size="1 1 100%-1 100%-1"', "map preview image")
write("gui/gamesetup/Pages/GameSetupPage/Panels/MapPreview.xml", mp)
# CI self-test (-conf=ios.menutest:true): log every visible object that sticks out of the screen.
gsjs = ZIP.read("gui/gamesetup/gamesetup.js").decode("utf-8")
gsjs = patch(gsjs, "\tg_SetupWindow = new SetupWindow(initData, hotloadData);\n", """\tg_SetupWindow = new SetupWindow(initData, hotloadData);
	if (Engine.ConfigDB_GetValue("user", "ios.menutest") == "true")
	{
		const start = Date.now();
		const root = Engine.GetGUIObjectByName("setupWindow");
		const previous = root.onTick;
		root.onTick = () => {
			if (previous)
				previous();
			if (Date.now() - start < 12000)
				return;
			root.onTick = previous;
			const screen = root.getComputedSize();
			let count = 0;
			const walk = (object, path) => {
				if (object.hidden)
					return;
				const size = object.getComputedSize();
				const name = path + "/" + (object.name || "?");
				if (size.right > screen.right + 1 || size.left < screen.left - 1 || size.bottom > screen.bottom + 1 || size.top < screen.top - 1)
					if (count++ < 40)
						warn("iOS layoutcheck: " + name + " " + Math.round(size.left) + " " + Math.round(size.top) + " " + Math.round(size.right) + " " + Math.round(size.bottom) + " (screen " + Math.round(screen.left) + ".." + Math.round(screen.right) + ")");
				for (const child of object.children)
					walk(child, name);
			};
			walk(root, "");
			log("iOS layoutcheck: " + count + " objects outside the screen");
		};
	}
""", "gamesetup layout check")
write("gui/gamesetup/gamesetup.js", gsjs)

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
