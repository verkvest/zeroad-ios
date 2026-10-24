/**
 * iOS port of 0 A.D. (GPL-2.0+): phone layout for the session HUD.
 * The desktop bottom panel is a centred 1024x204 strip of 38px icons. On a phone that
 * is far too small to touch, so the iOS mod scales the icon grids by 1.7 (make-ios-mod.py)
 * and this file re-arranges the panels into the screen corners:
 *   bottom left   minimap (toggle "Map"), above it the selection details (toggle "Info",
 *                 collapsed to the command row: garrison/unload/delete/... by default)
 *   bottom middle formations and stances (one row each)
 *   bottom right  build / train / research grid, 8 columns, grows upwards as needed
 *   top right     the iOS toolbar (ios_toolbar.js)
 * Disable with ios.hud=false.
 */
var g_IOSHud = {
	"enabled": Engine.ConfigDB_GetValue("user", "ios.hud") != "false",
	"wrapped": false,
	"map": Engine.ConfigDB_GetValue("user", "ios.minimap.hidden") != "true",
	"info": false,
	"columns": 8,
	"cell": 66,
	"mapSize": 220,
	"detailsWidth": 350,
	"supplementalWidth": 350
};

function iosHudInit()
{
	if (!g_IOSHud.enabled || g_IOSHud.wrapped)
		return;
	g_IOSHud.wrapped = true;

	for (const name of ["Construction", "Training", "Research", "Upgrade", "Gate", "Pack"])
		g_SelectionPanels[name].rowLength = g_IOSHud.columns;
	g_SelectionPanels.Research.getMaxNumberOfItems = () => g_IOSHud.columns;
	// Formations: one row (the first five) on phones.
	g_SelectionPanels.Formation.getMaxNumberOfItems = () => 5;

	const updateDetails = updateSelectionDetails;
	updateSelectionDetails = function()
	{
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
	iosHudLayout();
	log("iOS HUD: phone layout on");
}

function iosHudToggle(what)
{
	g_IOSHud[what] = !g_IOSHud[what];
	updateSelectionDetails();
	iosHudLayout();
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

	// Formation + stance rows, or the garrison grid (3 rows) for ships and buildings.
	const supplemental = Engine.GetGUIObjectByName("supplementalSelectionDetails");
	const supplementalHeight = g_SelectionPanels.Garrison.used ? 3 * cell + 20 : 2 * cell + 22;
	supplemental.size = left + " 100%-" + supplementalHeight + " " + (left + g_IOSHud.supplementalWidth) + " 100%";

	// Details: full card when "Info" is on, else only the command row (delete, garrison, ...).
	const details = Engine.GetGUIObjectByName("selectionDetails");
	const detailsBottom = g_IOSHud.map ? g_IOSHud.mapSize + 4 : supplementalHeight + 4;
	const detailsHeight = g_IOSHud.info ? 230 : 70;
	details.size = "0 100%-" + (detailsBottom + detailsHeight) + " " + g_IOSHud.detailsWidth + " 100%-" + detailsBottom;
	if (!g_IOSHud.info)
		for (const name of ["detailsAreaSingle", "detailsAreaMultiple"])
			Engine.GetGUIObjectByName(name).hidden = true;

	// Right grid: as many rows as the build/train items need, research (2 rows for pairs) below.
	const rows = Math.max(1, Math.ceil(getNumberOfRightPanelButtons() / g_IOSHud.columns));
	const commandsHeight = rows * cell + (g_SelectionPanels.Research.used ? 2 * cell + 8 : 0) + 18;
	Engine.GetGUIObjectByName("unitCommands").size =
		"100%-" + (g_IOSHud.columns * cell + 16) + " 100%-" + commandsHeight + " 100% 100%";
}
