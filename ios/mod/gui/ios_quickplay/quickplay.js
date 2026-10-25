/**
 * iOS port of 0 A.D. (GPL-2.0+): one-tap skirmish against the computer, modelled on
 * gui/autostart/autostart.js and autostart/cmd_line_args.js by Wildfire Games.
 * Defaults (all can be changed in user.cfg):
 *   ios.quickplay.map = "acropolis_bay_2p"   (a small 2-player skirmish map)
 *   ios.quickplay.aidifficulty = 1           (0 sandbox ... 5 very hard)
 */
function init()
{
	try
	{
		const map = Engine.ConfigDB_GetValue("user", "ios.quickplay.map") || "acropolis_bay_2p";
		const difficulty = +(Engine.ConfigDB_GetValue("user", "ios.quickplay.aidifficulty") || 1);

		const settings = new GameSettings().init();
		settings.map.setType("skirmish");
		settings.map.selectMap("maps/skirmishes/" + map);
		for (let i = 1; i < settings.playerCount.nbPlayers; ++i)
			settings.playerAI.set(i, {
				"bot": "petra",
				"difficulty": difficulty,
				"behavior": "balanced"
			});

		// CI App Store screenshot scene (gui/session/ios_shots.js) needs the stock cheats.
		if (Engine.ConfigDB_GetValue("user", "ios.shots") == "true")
			settings.cheats.setEnabled(true);

		const playerAssignments = {
			"local": {
				"player": 1,
				"name": Engine.ConfigDB_GetValue("user", "playername.singleplayer") || Engine.GetSystemUsername()
			}
		};
		log("iOS: quick play on " + map + ", AI difficulty " + difficulty);
		settings.launchGame(playerAssignments, true);
		Engine.SwitchGuiPage("page_loading.xml", {
			"attribs": settings.finalizedAttributes,
			"playerAssignments": playerAssignments
		});
	}
	catch (e)
	{
		error("iOS quick play failed: " + e + "\n" + e.stack);
		Engine.SwitchGuiPage("page_pregame.xml");
	}
}
