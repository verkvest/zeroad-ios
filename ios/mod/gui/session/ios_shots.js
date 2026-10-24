/**
 * iOS port of 0 A.D. (GPL-2.0+): App Store screenshot scene, only with -conf=ios.shots:true
 * (CI tooling; quick play enables cheats only in that mode). Uses the stock cheat commands of
 * simulation/helpers/Cheat.js by Wildfire Games: reveal the map, give the player an army next
 * to the civic centre, then spawn and convert an enemy army so a battle starts.
 */
var g_IOSShots = { "enabled": undefined, "start": 0, "step": 0, "before": [], "army": [], "enemy": [], "cc": undefined };

function iosShotsCheat(action, extra)
{
	Engine.PostNetworkCommand(Object.assign({ "type": "cheat", "player": Engine.GetPlayerID(), "action": action }, extra));
}

function iosShotsNew()
{
	const before = new Set(g_IOSShots.before);
	return Engine.GuiInterfaceCall("GetPlayerEntities").filter(ent => !before.has(ent));
}

function iosShotsCamera(dx = 0, dz = 0)
{
	const state = g_IOSShots.cc && GetEntityState(g_IOSShots.cc);
	if (state && state.position)
		Engine.CameraMoveTo(state.position.x + dx, state.position.z + dz);
}

function iosShotsTick()
{
	if (g_IOSShots.enabled === undefined)
		g_IOSShots.enabled = Engine.ConfigDB_GetValue("user", "ios.shots") == "true";
	if (!g_IOSShots.enabled)
		return;
	if (!g_IOSShots.start)
		g_IOSShots.start = Date.now();
	const t = (Date.now() - g_IOSShots.start) / 1000;
	const steps = [
		[3, () => {
			g_IOSShots.cc = Engine.GuiInterfaceCall("GetPlayerEntities").find(ent => {
				const state = GetEntityState(ent);
				return state && state.identity && state.identity.classes.indexOf("CivCentre") != -1;
			});
			g_IOSShots.before = Engine.GuiInterfaceCall("GetPlayerEntities");
			iosShotsCheat("revealmap", {});
			if (g_IOSShots.cc)
				iosShotsCheat("createunits", {
					"selected": [g_IOSShots.cc],
					"parameter": 28,
					"templates": ["units/athen/infantry_spearman_b", "units/athen/infantry_spearman_b", "units/athen/infantry_archer_b",
						"units/athen/cavalry_javelineer_b", "units/athen/champion_infantry", "units/athen/infantry_javelineer_b"]
				});
		}],
		[6, () => {
			g_IOSShots.army = iosShotsNew();
			g_Selection.reset();
			g_Selection.addList(g_IOSShots.army);
			iosShotsCamera(0, -12);
		}],
		[30, () => {
			g_IOSShots.before = Engine.GuiInterfaceCall("GetPlayerEntities");
			iosShotsCheat("createunits", {
				"selected": [g_IOSShots.cc],
				"parameter": 24,
				"templates": ["units/pers/infantry_spearman_b", "units/pers/infantry_archer_b", "units/pers/cavalry_archer_b",
					"units/pers/champion_infantry", "units/pers/cavalry_javelineer_b"]
			});
		}],
		[32, () => {
			g_IOSShots.enemy = iosShotsNew().filter(ent => g_IOSShots.army.indexOf(ent) == -1);
			iosShotsCheat("convertunit", { "selected": g_IOSShots.enemy, "parameter": 2 });
			g_Selection.reset();
			g_Selection.addList(g_IOSShots.army);
			iosShotsCamera();
		}],
		[40, () => iosShotsCamera()],
		[62, () => {
			g_Selection.reset();
			if (!g_IOSHud.map)
				iosHudToggle("map");
			iosShotsCamera(30, 30);
		}]
	];
	while (g_IOSShots.step < steps.length && t >= steps[g_IOSShots.step][0])
	{
		log("iOS shots: step " + g_IOSShots.step + " at " + Math.round(t) + " s");
		steps[g_IOSShots.step++][1]();
	}
}
