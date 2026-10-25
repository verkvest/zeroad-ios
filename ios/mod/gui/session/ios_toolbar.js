/**
 * iOS port of 0 A.D. (GPL-2.0+): on-screen buttons for actions that only have
 * keyboard hotkeys on desktop. They call the same functions as the hotkeys in
 * gui/session/hotkeys/*.xml (Wildfire Games).
 */
var g_IOSToolbarTicks = 0;

// CI self-test (-conf=ios.touchtest:true): press the toolbar buttons from script.
var g_IOSToolbarSelfTest = Engine.ConfigDB_GetValue("user", "ios.touchtest") == "true" ?
	[[104, "army"], [110, "stop"], [112, "idleworker"], [122, "page"], [130, "workers"], [134, "info"], [144, "info"],
	 [146, "home"], [156, "map"], [162, "map"], [164, "camera"], [166, "speed"], [168, "pause"], [172, "pause"], [174, "speed"],
	 [176, "test-diplomacy"], [194, "test-diplomacy-close"], [196, "deselect"], [198, "test-options"]] : [];
var g_IOSToolbarStart = 0;

function iosToolbarPress(action)
{
	log("iOS toolbar: " + action);
	switch (action)
	{
	case "pause":
		if (g_PauseControl.canPause(true))
			g_PauseControl.setPaused(!g_PauseControl.explicitPause, true);
		break;
	case "speed":
	{
		const speed = Engine.GetGUIObjectByName("gameSpeed");
		if (!g_IsNetworked && speed.list.length)
			speed.selected = (speed.selected + 1) % speed.list.length;
		break;
	}
	case "idleworker":
		findIdleUnit(g_WorkerTypes);
		break;
	case "idlearmy":
		findIdleUnit(g_MilitaryTypes);
		break;
	case "info":
		iosHudToggle("info");
		break;
	case "map":
		iosHudToggle("map");
		break;
	case "army":
		iosSelectOwn(["Soldier", "Siege", "Warship", "Hero", "Champion"], "army");
		break;
	case "workers":
		iosSelectOwn(["FemaleCitizen", "Citizen", "Worker"], "workers");
		break;
	case "deselect":
		g_Selection.reset();
		break;
	case "page":
		iosHudNextPage();
		break;
	case "test-diplomacy":
		g_DiplomacyDialog.open();
		break;
	case "test-diplomacy-close":
		g_DiplomacyDialog.close();
		break;
	case "test-options":
		Engine.OpenChildPage("page_options.xml");
		break;
	case "home":
		iosSelectCivicCentre();
		break;
	case "camera":
		iosResetCamera();
		break;
	case "stop":
		stopUnits(g_Selection.toList());
		break;
	case "work":
		backToWork();
		break;
	case "unload":
		unloadAll();
		break;
	case "delete":
		performCommand(g_Selection.toList().map(ent => GetEntityState(ent)), "delete");
		break;
	}
	iosToolbarUpdate();
}

// Select all own units (whole map) having one of the classes; structures excluded.
function iosSelectOwn(classes, what)
{
	if (g_ViewedPlayer <= 0)
		return;
	const ents = Engine.GuiInterfaceCall("GetPlayerEntities", g_ViewedPlayer).filter(ent => {
		const state = GetEntityState(ent);
		return state && state.identity && !hasClass(state, "Structure") && !state.foundation &&
			classes.some(cls => hasClass(state, cls));
	});
	log("iOS toolbar: " + ents.length + " " + what);
	if (!ents.length)
		return;
	g_Selection.reset();
	g_Selection.addList(ents);
}

// Default angle and zoom (view.* config), centred on the selection, else the current view.
function iosResetCamera()
{
	let pivot = Engine.GetCameraPivot();
	if (!pivot)
		return;
	let y = 0;
	const ent = g_Selection.getFirstSelected();
	const state = ent && GetEntityState(ent);
	if (state && state.position)
	{
		pivot = state.position;
		y = state.position.y;
	}
	const deg = Math.PI / 180;
	const rotX = (+Engine.ConfigDB_GetValue("user", "view.rotate.x.default") || 35) * deg;
	const rotY = (+Engine.ConfigDB_GetValue("user", "view.rotate.y.default") || 0) * deg;
	const zoom = +Engine.ConfigDB_GetValue("user", "view.zoom.default") || 120;
	log("iOS toolbar: camera reset at " + Math.round(pivot.x) + "," + Math.round(pivot.z));
	Engine.SetCameraData(pivot.x, y, pivot.z, rotX, rotY, zoom);
}

var g_IOSHomeIndex = 0;

// Select (and centre the camera on) the player's Civic Centre; repeated presses cycle through all of them.
// Skirmish maps place CCs under various template names, so match on the CivCentre class instead.
function iosSelectCivicCentre()
{
	if (g_ViewedPlayer <= 0)
		return;
	const ccs = Engine.GuiInterfaceCall("GetPlayerEntities", g_ViewedPlayer).filter(ent => {
		const state = GetEntityState(ent);
		return state && state.identity && state.identity.classes.indexOf("CivCentre") != -1 && !state.foundation;
	}).sort((a, b) => a - b);
	log("iOS toolbar: " + ccs.length + " civic centre(s)");
	if (!ccs.length)
		return;
	g_Selection.selectAndMoveTo(ccs[g_IOSHomeIndex++ % ccs.length]);
}

function iosToolbarUpdate()
{
	const hasSelection = g_Selection.size() > 0;
	Engine.GetGUIObjectByName("iosDeselect").hidden = !hasSelection;
	for (const action of ["stop", "work", "unload", "delete"])
		Engine.GetGUIObjectByName("iosButton_" + action).enabled = hasSelection;
	for (const action of ["stop", "work", "unload", "delete"])
	{
		const icon = Engine.TryGetGUIObjectByName("iosIcon_" + action);
		if (icon)
			icon.sprite = (hasSelection ? "" : "color:0 0 0 127:grayscale:") + icon.sprite.replace(/^color:0 0 0 127:grayscale:/, "");
	}
	Engine.GetGUIObjectByName("iosButton_pause").enabled = g_PauseControl.canPause(true);
	Engine.GetGUIObjectByName("iosLabel_pause").caption = g_PauseControl.explicitPause ? translate("Resume") : translate("Pause");
	Engine.GetGUIObjectByName("iosButton_speed").enabled = !g_IsNetworked;
	Engine.GetGUIObjectByName("iosLabel_speed").caption = "×" + (+Engine.GetSimRate().toFixed(2));
	Engine.GetGUIObjectByName("iosLabel_map").caption = g_IOSHud.map ? translate("Hide map") : translate("Map");
}

function iosToolbarTick()
{
	if (g_IOSToolbarTicks == 0)
	{
		iosHudInit();
		const size = Engine.GetGUIObjectByName("iosToolbar").getComputedSize();
		log("iOS toolbar: ready at " + Math.round(size.left) + "," + Math.round(size.top) + " - " + Math.round(size.right) + "," + Math.round(size.bottom));
	}
	if (!g_IOSToolbarStart)
		g_IOSToolbarStart = Date.now();
	if (g_IOSToolbarSelfTest.length && Date.now() - g_IOSToolbarStart >= g_IOSToolbarSelfTest[0][0] * 1000)
	{
		const action = g_IOSToolbarSelfTest.shift()[1];
		log("iOS toolbar self-test: " + action + " (selected " + g_Selection.size() + ")");
		iosToolbarPress(action);
	}
	iosHudTick();
	iosShotsTick();
	if (++g_IOSToolbarTicks % 15 == 0)
		iosToolbarUpdate();
}
