/**
 * iOS port of 0 A.D. (GPL-2.0+): on-screen buttons for actions that only have
 * keyboard hotkeys on desktop. They call the same functions as the hotkeys in
 * gui/session/hotkeys/*.xml (Wildfire Games).
 */
var g_IOSToolbarTicks = 0;

// CI self-test (-conf=ios.touchtest:true): press the toolbar buttons from script.
var g_IOSToolbarSelfTest = Engine.ConfigDB_GetValue("user", "ios.touchtest") == "true" ?
	[[115, "army"], [120, "stop"], [125, "home"], [130, "speed"], [135, "speed"], [140, "pause"], [146, "pause"]] : [];
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
	case "army":
		iosSelectArmyOnScreen();
		break;
	case "home":
		iosSelectCivicCentre();
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

function iosSelectArmyOnScreen()
{
	const military = ["Soldier", "Siege", "Warship", "Hero", "Champion"];
	const ents = Engine.PickPlayerEntitiesOnScreen(g_ViewedPlayer).filter(ent => {
		const state = GetEntityState(ent);
		return state && !hasClass(state, "Structure") && military.some(cls => hasClass(state, cls));
	});
	if (!ents.length)
		return;
	g_Selection.reset();
	g_Selection.addList(ents);
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
	for (const action of ["stop", "work", "unload", "delete"])
		Engine.GetGUIObjectByName("iosButton_" + action).enabled = hasSelection;
	const pause = Engine.GetGUIObjectByName("iosButton_pause");
	pause.enabled = g_PauseControl.canPause(true);
	pause.caption = g_PauseControl.explicitPause ? translate("Resume") : translate("Pause");
	const speed = Engine.GetGUIObjectByName("iosButton_speed");
	speed.enabled = !g_IsNetworked;
	speed.caption = sprintf(translate("Speed %(rate)s"), { "rate": "×" + (+Engine.GetSimRate().toFixed(2)) });
}

function iosToolbarTick()
{
	if (g_IOSToolbarTicks == 0)
	{
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
	if (++g_IOSToolbarTicks % 15 == 0)
		iosToolbarUpdate();
}
