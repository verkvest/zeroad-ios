/**
 * iOS port of 0 A.D. (GPL-2.0+): phone layout for the session HUD.
 * The desktop bottom panel is a centred 1024x204 strip of 38px icons. On a phone that
 * is far too small to touch, so the iOS mod scales the icon grids by 2.2 (make-ios-mod.py:
 * 84 GUI units = 56pt at the phone GUI scale) and this file re-arranges the panels:
 *   top left      the iOS toolbar (ios_toolbar.js), 7 x 2 buttons of 48pt
 *   bottom left   minimap (toggle "Map"); right of it formations + stances (3 per row)
 *                 or the garrison grid; above them the command row (garrison, delete, ...)
 *                 with an X to deselect
 *   bottom right  build / train grid, 6 columns x 2 rows per page (page button on its left),
 *                 research (2 rows) below, production queue (6) above
 *   top right     the selection details card when "Info" is on
 * Disable with ios.hud=false.
 */
var g_IOSHud = {
	"enabled": Engine.ConfigDB_GetValue("user", "ios.hud") != "false",
	"wrapped": false,
	"map": Engine.ConfigDB_GetValue("user", "ios.minimap.hidden") != "true",
	"info": false,
	"columns": 6,
	"rowsPerPage": 2,
	"cell": 85,
	"mapSize": 200,
	"detailsWidth": 440,
	"infoWidth": 470,
	"infoHeight": 300,
	"supplementalWidth": 310,
	"page": 0,
	"pages": 1,
	"selectionKey": "",
	"armed": "",
	"ringUntil": 0
};

var g_IOSRightPanelButton = /^unit(Construction|Training|Gate|Pack|Upgrade)Button\[\d+\]$/;

/**
 * Called first by setPanelObjectPosition (unit_commands.js, patched by make-ios-mod.py).
 * Build / train buttons are paged: only the current page is shown, in a 6-column grid.
 */
function iosPanelPosition(object, index, rowLength)
{
	if (!g_IOSHud.enabled || !g_IOSRightPanelButton.test(object.name))
		return false;
	const perPage = g_IOSHud.columns * g_IOSHud.rowsPerPage;
	const first = g_IOSHud.page * perPage;
	if (index < first || index >= first + perPage)
	{
		object.hidden = true;
		return true;
	}
	index -= first;
	const oWidth = object.size.right - object.size.left;
	const oHeight = object.size.bottom - object.size.top;
	const left = (index % g_IOSHud.columns) * (oWidth + 1);
	const top = Math.floor(index / g_IOSHud.columns) * (oHeight + 1);
	Object.assign(object.size, { "left": left, "right": left + oWidth, "top": top, "bottom": top + oHeight });
	return true;
}

function iosHudInit()
{
	if (!g_IOSHud.enabled || g_IOSHud.wrapped)
		return;
	g_IOSHud.wrapped = true;

	for (const name of ["Construction", "Training", "Research", "Upgrade", "Gate", "Pack", "Queue"])
		g_SelectionPanels[name].rowLength = g_IOSHud.columns;
	g_SelectionPanels.Research.getMaxNumberOfItems = () => g_IOSHud.columns;
	g_SelectionPanels.Queue.getMaxNumberOfItems = () => g_IOSHud.columns;
	// Formations: the first three; stances 3 per row (2 rows); garrison 3 x 2; portraits 4 x 2.
	g_SelectionPanels.Formation.getMaxNumberOfItems = () => 3;
	g_SelectionPanels.Formation.rowLength = 3;
	g_SelectionPanels.Stance.rowLength = 3;
	g_SelectionPanels.Garrison.rowLength = 3;
	g_SelectionPanels.Garrison.getMaxNumberOfItems = () => 6;
	g_SelectionPanels.Selection.getMaxNumberOfItems = () => 8;

	const updateDetails = updateSelectionDetails;
	updateSelectionDetails = function()
	{
		// New selection: back to the first page of the build / train grid.
		const key = g_Selection.toList().join(",");
		if (key != g_IOSHud.selectionKey)
		{
			g_IOSHud.selectionKey = key;
			g_IOSHud.page = 0;
		}
		updateDetails();
		iosHudLayout();
	};

	for (const name of ["civIcon", "buildLabel"])
	{
		const obj = Engine.TryGetGUIObjectByName(name);
		if (obj)
			obj.hidden = true;
	}

	const bottom = Engine.GetGUIObjectByName("supplementalSelectionDetails").parent;
	bottom.size = "0 0 100% 100%";
	// Hero / group buttons: top right, under the top bar.
	const entities = Engine.TryGetGUIObjectByName("panelEntityButtons");
	if (entities)
		entities.size = "100%-76 56 100%-4 300";
	iosHudLayout();
	log("iOS HUD: phone layout on");
}

function iosHudToggle(what)
{
	g_IOSHud[what] = !g_IOSHud[what];
	updateSelectionDetails();
	iosHudLayout();
}

function iosHudNextPage()
{
	g_IOSHud.page = (g_IOSHud.page + 1) % Math.max(1, g_IOSHud.pages);
	updateSelectionDetails();
}

function iosHudLayout()
{
	if (!g_IOSHud.enabled)
		return;
	const cell = g_IOSHud.cell;

	const minimap = Engine.GetGUIObjectByName("minimapPanel").parent;
	minimap.hidden = !g_IOSHud.map;
	minimap.size = "0 100%-" + g_IOSHud.mapSize + " " + g_IOSHud.mapSize + " 100%";
	const left = g_IOSHud.map ? g_IOSHud.mapSize + 4 : 0;

	// Formations (1 row) + stances (2 rows), or the garrison grid (2 rows) + alert row.
	const supplemental = Engine.GetGUIObjectByName("supplementalSelectionDetails");
	const supplementalHeight = 3 * cell + 40;
	supplemental.size = left + " 100%-" + supplementalHeight + " " + (left + g_IOSHud.supplementalWidth) + " 100%";
	const stance = Engine.TryGetGUIObjectByName("unitStancePanel");
	if (stance)
		stance.size = "9 100%-" + (2 * cell + 14) + " 100%-9 100%-9";

	// Details: the command row above formations/stances; the full card (top right) with "Info".
	const details = Engine.GetGUIObjectByName("selectionDetails");
	const rowBottom = supplementalHeight + 4;
	const rowHeight = 96;
	if (g_IOSHud.info)
		details.size = "100%-" + (g_IOSHud.infoWidth + 84) + " 56 100%-84 " + (56 + g_IOSHud.infoHeight);
	else
	{
		details.size = "0 100%-" + (rowBottom + rowHeight) + " " + g_IOSHud.detailsWidth + " 100%-" + rowBottom;
		for (const name of ["detailsAreaSingle", "detailsAreaMultiple"])
			Engine.GetGUIObjectByName(name).hidden = true;
	}

	// X to deselect, right of the command row.
	const deselect = Engine.GetGUIObjectByName("iosDeselect");
	deselect.hidden = !g_Selection.size();
	deselect.size = (g_IOSHud.detailsWidth + 4) + " 100%-" + (rowBottom + 70) + " " + (g_IOSHud.detailsWidth + 70) + " 100%-" + (rowBottom + 4);

	// Right grid: one page (2 rows) of build/train items, research (2 rows for pairs) below.
	const total = getNumberOfRightPanelButtons();
	const perPage = g_IOSHud.columns * g_IOSHud.rowsPerPage;
	g_IOSHud.pages = Math.max(1, Math.ceil(total / perPage));
	if (g_IOSHud.page >= g_IOSHud.pages)
		g_IOSHud.page = 0;
	const rows = Math.max(1, Math.min(g_IOSHud.rowsPerPage, Math.ceil(total / g_IOSHud.columns)));
	const commandsHeight = rows * cell + (g_SelectionPanels.Research.used ? 2 * cell + 8 : 0) + 18;
	const commandsWidth = g_IOSHud.columns * cell + 16;
	Engine.GetGUIObjectByName("unitCommands").size =
		"100%-" + commandsWidth + " 100%-" + commandsHeight + " 100% 100%";

	const page = Engine.GetGUIObjectByName("iosPageButton");
	page.hidden = g_IOSHud.pages < 2 || !g_Selection.size();
	page.size = "100%-" + (commandsWidth + 76) + " 100%-" + (commandsHeight) + " 100%-" + (commandsWidth + 4) + " 100%-" + (commandsHeight - 72);
	Engine.GetGUIObjectByName("iosPageLabel").caption = (g_IOSHud.page + 1) + "/" + g_IOSHud.pages + " >";
}

/** Ring under the finger when a long press arms box selection (engine sets ios.touch.armed). */
function iosHudTick()
{
	const ring = Engine.GetGUIObjectByName("iosArmedRing");
	const armed = Engine.ConfigDB_GetValue("user", "ios.touch.armed");
	if (armed && armed != g_IOSHud.armed)
	{
		const first = !g_IOSHud.armed;
		g_IOSHud.armed = armed;
		const [, px, py] = armed.split(" ").map(Number);
		if (!first || g_IOSHud.ringUntil == 0)
		{
			const scale = +Engine.ConfigDB_GetValue("user", "ios.gui.scale") || 1;
			const x = px / scale - (+Engine.ConfigDB_GetValue("user", "ios.gui.insetleft") || 0);
			const y = py / scale - (+Engine.ConfigDB_GetValue("user", "ios.gui.insettop") || 0);
			ring.size = (x - 48) + " " + (y - 48) + " " + (x + 48) + " " + (y + 48);
			ring.hidden = false;
			g_IOSHud.ringUntil = Date.now() + 600;
			log("iOS HUD: long press ring at " + Math.round(x) + "," + Math.round(y));
		}
	}
	if (!ring.hidden && Date.now() > g_IOSHud.ringUntil)
		ring.hidden = true;
}
