/**
 * iOS port of 0 A.D. (GPL-2.0+): App Store screenshot scene, only with -conf=ios.shots:true
 * (CI tooling; quick play enables cheats only in that mode). Uses the stock cheat commands of
 * simulation/helpers/Cheat.js by Wildfire Games and normal walk orders: an army gathers at the
 * civic centre, marches into the open towards the enemy, then a second army walks past it and is
 * converted to player 2, so a battle starts in the open, in front of the camera.
 * Timing uses the simulation clock (the first session ticks can be very slow in the simulator).
 */
var g_IOSShots = { "enabled": undefined, "step": 0, "before": [], "army": [], "enemy": [], "cc": undefined, "dir": { "x": 0, "z": -1 }, "cam": undefined };

function iosShotsCheat(action, extra)
{
	Engine.PostNetworkCommand(Object.assign({ "type": "cheat", "player": Engine.GetPlayerID(), "action": action }, extra));
}

function iosShotsNew()
{
	const before = new Set(g_IOSShots.before);
	return Engine.GuiInterfaceCall("GetPlayerEntities").filter(ent => !before.has(ent));
}

function iosShotsPos(ent)
{
	const state = GetEntityState(ent);
	return state && state.position ? { "x": state.position.x, "z": state.position.z } : undefined;
}

function iosShotsCentre(ents)
{
	const ps = ents.map(iosShotsPos).filter(p => p);
	if (!ps.length)
		return iosShotsPos(g_IOSShots.cc);
	return { "x": ps.reduce((s, p) => s + p.x, 0) / ps.length, "z": ps.reduce((s, p) => s + p.z, 0) / ps.length };
}

function iosShotsAhead(p, d, side = 0)
{
	const dir = g_IOSShots.dir;
	return { "x": p.x + dir.x * d - dir.z * side, "z": p.z + dir.z * d + dir.x * side };
}

/** Look at the ground point p from distance zoom, turned by rotY (radians); corrected next tick. */
function iosShotsLook(p, zoom, rotY = 0.45, rotX = 0.62)
{
	if (!p)
		return;
	const inX = Math.cos(rotX) * Math.sin(rotY), inY = -Math.sin(rotX), inZ = Math.cos(rotX) * Math.cos(rotY);
	const y = 45;
	g_IOSShots.cam = { "target": p, "zoom": zoom, "rotX": rotX, "rotY": rotY,
		"pos": { "x": p.x - inX * zoom, "y": y - inY * zoom, "z": p.z - inZ * zoom }, "fix": 3 };
	const c = g_IOSShots.cam;
	Engine.SetCameraData(c.pos.x, c.pos.y, c.pos.z, rotX, rotY, zoom);
}

function iosShotsFixCamera()
{
	const c = g_IOSShots.cam;
	if (!c || !c.fix)
		return;
	--c.fix;
	const pivot = Engine.GetCameraPivot();
	if (!pivot)
		return;
	const dx = c.target.x - pivot.x, dz = c.target.z - pivot.z;
	if (Math.abs(dx) + Math.abs(dz) < 1)
		return;
	c.pos.x += dx;
	c.pos.z += dz;
	Engine.SetCameraData(c.pos.x, c.pos.y, c.pos.z, c.rotX, c.rotY, c.zoom);
}

function iosShotsTick()
{
	if (g_IOSShots.enabled === undefined)
		g_IOSShots.enabled = Engine.ConfigDB_GetValue("user", "ios.shots") == "true";
	if (!g_IOSShots.enabled)
		return;
	iosShotsFixCamera();
	const t = (GetSimState().timeElapsed || 0) / 1000;
	const all = () => g_IOSShots.army.concat(g_IOSShots.enemy);
	const steps = [
		[1, () => {
			const isCC = (ent, owner) => {
				const state = GetEntityState(ent);
				return state && state.identity && state.identity.classes.indexOf("CivCentre") != -1 && (owner === undefined || state.player == owner);
			};
			g_IOSShots.cc = Engine.GuiInterfaceCall("GetPlayerEntities").find(ent => isCC(ent));
			const enemyCC = Engine.GuiInterfaceCall("GetNonGaiaEntities").find(ent => isCC(ent, 2));
			const a = iosShotsPos(g_IOSShots.cc), b = enemyCC && iosShotsPos(enemyCC);
			if (a && b)
			{
				const len = Math.hypot(b.x - a.x, b.z - a.z) || 1;
				g_IOSShots.dir = { "x": (b.x - a.x) / len, "z": (b.z - a.z) / len };
			}
			log("iOS shots: CC " + JSON.stringify(a) + " enemy CC " + JSON.stringify(b) + " dir " + JSON.stringify(g_IOSShots.dir));
			g_IOSShots.before = Engine.GuiInterfaceCall("GetPlayerEntities");
			iosShotsCheat("revealmap", {});
			iosShotsCheat("maxpopulation", {});
		}],
		[2, () => {
			if (g_IOSShots.cc)
				iosShotsCheat("createunits", {
					"selected": [g_IOSShots.cc],
					"parameter": 40,
					"templates": ["units/athen/infantry_spearman_b", "units/athen/infantry_spearman_b", "units/athen/infantry_archer_b",
						"units/athen/cavalry_javelineer_b", "units/athen/champion_infantry", "units/athen/infantry_spearman_a",
						"units/athen/infantry_javelineer_b", "units/athen/cavalry_swordsman_b"]
				});
		}],
		// Base view: the civic centre with the new army around it.
		[5, () => {
			g_IOSShots.army = iosShotsNew();
			log("iOS shots: army of " + g_IOSShots.army.length);
			iosShotsLook(iosShotsPos(g_IOSShots.cc), 95, 0.6);
		}],
		// The army marches into the open towards the enemy.
		[16, () => {
			const p = iosShotsAhead(iosShotsPos(g_IOSShots.cc), 55);
			Engine.PostNetworkCommand({ "type": "walk", "entities": g_IOSShots.army, "x": p.x, "z": p.z, "queued": false, "pushFront": false });
			g_Selection.reset();
			g_Selection.addList(g_IOSShots.army);
			iosShotsLook(iosShotsCentre(g_IOSShots.army), 75, 0.35);
		}],
		[22, () => iosShotsLook(iosShotsCentre(g_IOSShots.army), 62, 0.35)],
		[28, () => iosShotsLook(iosShotsCentre(g_IOSShots.army), 62, 0.35)],
		[32, () => {
			g_IOSShots.before = Engine.GuiInterfaceCall("GetPlayerEntities");
			iosShotsCheat("createunits", {
				"selected": [g_IOSShots.cc],
				"parameter": 36,
				"templates": ["units/pers/infantry_spearman_b", "units/pers/infantry_archer_b", "units/pers/cavalry_archer_b",
					"units/pers/champion_infantry", "units/pers/cavalry_javelineer_b", "units/pers/infantry_javelineer_b"]
			});
		}],
		[35, () => {
			g_IOSShots.enemy = iosShotsNew().filter(ent => g_IOSShots.army.indexOf(ent) == -1);
			log("iOS shots: enemy of " + g_IOSShots.enemy.length);
			const p = iosShotsAhead(iosShotsCentre(g_IOSShots.army), 40, 10);
			Engine.PostNetworkCommand({ "type": "walk", "entities": g_IOSShots.enemy, "x": p.x, "z": p.z, "queued": false, "pushFront": false });
			iosShotsLook(iosShotsCentre(g_IOSShots.army), 70, 0.35);
		}],
		[44, () => iosShotsLook(iosShotsCentre(all()), 72, 0.5)],
		// Battle: the second army becomes player 2's, right next to ours.
		[52, () => {
			iosShotsCheat("convertunit", { "selected": g_IOSShots.enemy, "parameter": 2 });
			g_Selection.reset();
			g_Selection.addList(g_IOSShots.army);
			iosShotsLook(iosShotsCentre(all()), 66, 0.5);
		}],
		[58, () => iosShotsLook(iosShotsCentre(all()), 62, 0.5)],
		[64, () => iosShotsLook(iosShotsCentre(all()), 62, 0.6)],
		[70, () => iosShotsLook(iosShotsCentre(all()), 62, 0.6)],
		[76, () => iosShotsLook(iosShotsCentre(all()), 66, 0.6)],
		// Overview: wider view of the field and the base, nothing selected.
		[84, () => {
			g_Selection.reset();
			if (!g_IOSHud.map)
				iosHudToggle("map");
			iosShotsLook(iosShotsAhead(iosShotsPos(g_IOSShots.cc), 25), 120, 0.3, 0.75);
		}]
	];
	while (g_IOSShots.step < steps.length && t >= steps[g_IOSShots.step][0])
	{
		log("iOS shots: step " + g_IOSShots.step + " at sim " + Math.round(t) + " s");
		steps[g_IOSShots.step++][1]();
	}
}
