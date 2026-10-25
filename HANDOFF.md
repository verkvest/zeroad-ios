# HANDOFF — 0 A.D. iOS port (state notes for the next agent)

Updated: 2026-10-24 11:22 (Europe/Madrid)

## Milestones
- M1 main menu: DONE. CI sim screenshots: shots/m1-mainmenu/. TestFlight build 9 (tag testflight-engine-4,
  ios-testflight run 40076677038, from ios-build run 40075219813). Upload succeeded.
- M2 skirmish: world renders in Simulator (Acropolis Bay vs Petra), shots/m2-skirmish/ (run 40078973413).
  Fix that made it render: view.scroll.mouse.detectdistance=0 (camera was edge-scrolling into a corner).
  Touch self-test (patch 0008, -conf=ios.touchtest:true) running in ios-build run 40080912107 (commit c5e9547).

## Next steps
1. When 40080912107 finishes: `gh run download 40080912107 -n engine-iphonesimulator-log`, check
   out/skirmish/mainlog.html for "iOS touchtest:", "iOS touch: action", "tap -> command", camera pivot
   changes; copy PNGs to shots/m2-touchtest/.
2. DONE: tag testflight-engine-5 -> TestFlight build 10 (ios-testflight run 40081193988, uploaded OK,
   app from ios-build run 40078973413 = camera fix + tap-command mod). Next tag: testflight-engine-6.
3. Then: real-device perf feedback from Aleksandr, touch UI polish (bigger GUI scale option).

## Notes
- Next free TestFlight tag: testflight-engine-6. Tag a commit WITHOUT [skip ci] in its message, or the tag push is skipped.
- Pushing to feature/ios-prototype cancels the running ios-build (concurrency); use "[skip ci]" for doc commits.
- PR-triggered duplicate runs are cancelled manually to save macOS runners.
- Patches 0001..0008 in patches/0ad; regenerate a patch by committing tmp in build/0ad, editing, `git diff HEAD -- source`, then `git reset --mixed a2cae4d`.

## Update 2026-10-24 12:10 (Europe/Madrid)
- Builds 8, 9, 10 were all REJECTED in ASC processing: ITMS-91017 (BrowserEngineCore framework not allowed) + ITMS-90683 warning (NSBluetoothAlwaysUsageDescription). They never showed up in TestFlight.
- Fix: ios/src/BrowserEngineStubs.cpp (no-op be_memory_inline_jit_* stubs, JIT is off anyway), patch 0009 drops the weak BrowserEngineCore link, plist gets the Bluetooth string, and make-engine-xcarchive.sh fails if BrowserEngine is still linked. ios-build run 40084376304.
- Touch self-test run 40080912107 OK: box select picked 9 units, tap gave a 'move' command, two-finger pan and pinch (zoom 120->50) worked. Shots are in shots/m2-touchtest/.
- ASC (app 6826514754): user 90528@list.ru can now see the app. Internal group "0 A.D. interno" 86f5a074-bd0e-435d-819a-e76751598387 (all builds) and external group "0 A.D. testers" 5768bd13-a0ef-492c-9b81-3a66a3231711 both have tester 90528@list.ru. Beta review details and the en-US beta localization are filled in.
- Automation: /workspace/asc/pipeline.sh (log /workspace/asc/pipeline.log) waits for the device job, tags testflight-engine-6, waits for the upload and for VALID, adds the build to both groups and submits for Beta App Review.
- Next: check pipeline.log. After beta approval, enable publicLinkEnabled on the external group to get a public link.

## Update 2026-10-24 12:30 (Europe/Madrid): device crash of build 11
- Build 11 (testflight-engine-6, run 40084918525) passed Apple processing. Internal: IN_BETA_TESTING. External: WAITING_FOR_BETA_REVIEW. Adding a build to the internal group by API returns 422, which is expected because the group has access to all builds.
- The build crashed on iPhone17,1 / iOS 27.2 about 0.1 s after launch. Crash log: ASC betaFeedbackCrashSubmissions AHcZzlSkutZCRDxPU9LJuYs, saved to /workspace/asc/crash11.txt.
  Symbolicated with llvm-symbolizer against the unstripped binary from the engine-iphoneos-log artifact: ScriptContext::CreateContext -> js::Thread::create -> MOZ_RELEASE_ASSERT(!r) (PosixThread.cpp:54), i.e. pthread_attr_setstacksize EINVAL.
  Cause: the SpiderMonkey helper stack size is 2 MiB - 2*4 KiB, which is not a multiple of the 16 KiB device page size.
- Fix (2280946): build-spidermonkey-ios.sh changes the size to 2 MiB - 2*16 KiB with sed and checks the result. This changes the cache key, so mozjs is rebuilt. ios-build run 40085967752.
- /workspace/asc/pipeline.sh 40085967752 testflight-engine-7 (log pipeline12.log) tags the commit, uploads build 12, and adds it to the external group with a review submission.
- To symbolicate the next crash: download the engine-iphoneos-log artifact, unzip Pyrogenesis.app/pyrogenesis, and run llvm-symbolizer --obj=pyrogenesis on 0x100000000+offset.

## Update 2026-10-24 (Europe/Madrid): iPhone adaptation (target build 13, tag testflight-engine-8)
- Engine patch 0010: GUI laid out inside the UIKit safe area (left/right insets; bottom via ios.safearea.bottom=true; off via ios.safearea=false),
  canvas translate + scissor offset + mouse offset in CGUI; auto GUI scale = min(safeH/600, safeW/1100) (ios.gui.minwidth/minheight); home indicator auto-hidden.
  Exposes ios.gui.scale / ios.gui.insetleft / ios.gui.insettop to JS (input.js band box uses them).
- ios mod: main menu "Quick Play vs AI" (page_ios_quickplay.xml: ios.quickplay.map default acropolis_bay_2p, 1 Petra easy/balanced);
  ios.autoquickplay=true presses it automatically (CI). Session right-edge toolbar (gui/session/ios_toolbar.js + session_objects/ios_toolbar.xml):
  Pause, Speed, Idle worker, Idle army, Army on screen, Home (CC), Stop, Back to work, Unload, Delete. Self-test presses them when ios.touchtest=true.
- Defaults: particles off, AI difficulty 1 (easy), tips off.
- CI: sim-launch.py prefers "iPhone N Pro" (SIM_DEVICE regex overrides); skirmish step is now main menu -> Quick Play + touch self-test.
- Not done yet: zoom-reset button, bigger minimap, simplified top bar.
- Result (CI run 40089479508, iPhone 17 Pro sim 2622x1206): safe insets 62pt L/R -> GUI scale 2.00, logical 1125x603; quick play + touch self-test + toolbar self-test pass.
  Screenshots (local box, shots/ is gitignored; also in CI artifact engine-iphonesimulator-log): shots/m3-iphone-mainmenu, shots/m3-iphone-quickplay, shots/m3-iphone-hud (rotated to landscape, JPEG).
- Build 13 (tag testflight-engine-8 @ af5a47f): VALID, internal testing; external submit blocked (build 11 still in beta review).
- Known: in build 13 the Home button finds no CC (skirmish CC template names differ) -> fixed in f0b7a23 (match CivCentre class); ship as testflight-engine-9 / build 14 after its CI.
- Self-test camera ends off-map after the two-finger pan (finger-follow pan near the horizon) -> world black in later screenshots; not a render bug.
- ASC crashes: only the build 11 one (2026-10-24 12:22 Madrid); none for builds 12/13 yet.

## Update 2026-10-24 ~14:40 (Europe/Madrid): phone HUD redesign + audio (target build 14, tag testflight-engine-9)
- Owner on device: "всё мелко и неудобно", no music.
- Audio: works on device (phone was on silent). Audio session patch and musicgain change dropped on owner's request; no audio code changes.
- HUD (ios mod, ios_hud.js + make-ios-mod.py):
  icon grids of all selection panels scaled 1.7x (38 -> 65 lu = ~43pt at GUI scale 2); right grid 8 columns, grows upwards;
  minimap 220 lu bottom-left (toolbar "Map" toggles), details card above it hidden by default (toolbar "Info"), only the command row stays;
  formations limited to one row; top bar 1.4x with bigger resource font, civ emblem + build label hidden; Menu dropdown 1.4x;
  toolbar = 12 icon buttons 72 lu (48pt) top-right (Idle army replaced by Info). Tap tolerance ring (ios.taptolerance, 16 lu).
  Main menu buttons 44 lu with 20px font. Camera default zoom 85 (was 120); Camera button resets angle/zoom.
- GUI scale kept at ~2.0 for all pages (menus/dialogs need ~1100x600 logical); the session HUD is enlarged by layout instead.
- Not done: game-setup page redesign (Quick Play is the one-tap path), paging in grids (grid grows instead).

## Update 2026-10-24 ~16:10 (Madrid): touch rework, 56pt icons, dialogs (a1054b2)
- **Gestures** (touch/TouchGestures, patch 0011): one-finger drag on the 3D view = camera pan
  (`Action::box=false`; over a GUI control it is still a mouse drag, via new `CGUI::IsScreenPointOverObject`).
  Long press 0.45 s = `LongPressArmed` (light haptic via UIImpactFeedbackGenerator, config
  `ios.touch.armed` -> ring in ios_hud.js), then drag = box select; release without moving = right click.
  Two-finger tap = right click, double tap = same type on screen (unchanged). No "frame" toggle.
- **HUD** (ios_hud.js + gen_ios_overlay.py -> ios_toolbar.xml): ICON_K 2.2 (84 units = 56pt). Toolbar 7x2
  (48pt) top left incl. Workers / Army (whole map); build/train grid 6 columns x 2 rows per page + page
  button; research 2 rows below; queue 6; stances 3 per row; formations 3; garrison 3x2; X deselect
  button next to the command row; Info card top right.
- **Dialogs** (make-ios-mod.py): every `50%-A 50%-B 50%+C 50%+D` box clamped to 1090 x 584; buttons that
  close/cancel/back (hotkey cancel, name or caption) grown to 66 units (44pt). In-game menu items 54 units.
  Not done: tap-outside-to-close; mod "mod" msgbox not processed.
- Self-test: long press + drag box at t=20, one-finger pan t=52; toolbar self-test opens diplomacy (176 s)
  and the structure tree (188 s) for screenshots. Sim run 300 s.
- **Build 14** = tag testflight-engine-9 at a1054b2 (ios-build 40097922753, testflight run 40099486908):
  ASC VALID 16:02 Madrid, internal IN_BETA_TESTING; external submit blocked (build 11 still in review).
- 39e1d43: self-test only (sorted touch script, points off the HUD, diplomacy + options screenshots);
  first run showed toolbar quick-select OK (9 workers / 5 army / CC), but the touch script was unsorted
  and hit HUD buttons, and Engine.PushGuiPage is not available in 0.28 (use OpenChildPage).

## Update 2026-10-24 ~17:00 Madrid — build 15 work (tag testflight-engine-10)
- Tooltips (patch 0012): no hover/automatic tooltips on iOS; a long press on a GUI object shows its
  tooltip for 2 s, hidden on the next touch; no tooltip and no right click from map taps.
- Gestures: long press is armed on the next finger event too (slow frames); touchdemo self-test
  disables long press.
- Main menu (ios/mod/gui/pregame/MainMenuItemHandler.js + make-ios-mod.py): left panel 500 lu,
  logo 300x76, two columns of 72-lu (48pt) buttons centred vertically, submenu = one column to the
  right aligned with the pressed button and clamped on screen; no description/notice, community
  (Donate etc.), organisation logo, user-report panel, welcome splash, Scenario Editor or
  "Welcome Screen" item; background overscan.
- Message boxes (from mod.zip, next to public zip): 44pt buttons, fit the screen, tap on the
  faded background = first (cancel) button.
- Options page: full screen, title inside, 44-lu tabs, 36-lu rows in as many columns as needed,
  four equal 44pt buttons at the bottom.
- CI: main-menu sim run is 120 s with -conf=ios.menutest:true (Single-player submenu at 15 s,
  game setup at 40 s after the menu opens); sim-launch relaunches an app with no output after 20 s.
- Game setup: top panel 8..232, map preview 300 wide, tips hidden, settings/tabs from 240,
  44pt Back/Start.
- **Build 15 = tag testflight-engine-10 at 9512f9c** (ios-build 40105949957, testflight
  40106540439): VALID 17:29 Madrid, internal IN_BETA_TESTING (group "0 A.D. interno");
  external beta submit still 422 ANOTHER_BUILD_IN_REVIEW (build 11 in review).
- Sim screenshots (landscape, half size, gitignored): shots/b15/mainmenu.jpg,
  mainmenu-singleplayer-submenu.jpg, gamesetup.jpg, options.jpg. Main menu and options are clean.
  Game setup is better but not perfect: the map preview and the right tabs/description column
  stick out ~70 lu past the page frame on the right, and a button fragment ("...aps") shows behind
  the description. Likely JS code mixing absolute getComputedSize (which includes the 93-lu
  safe-area inset) with relative sizes; to fix next.

## Update 2026-10-24 ~18:50 Madrid — build 16 (tag testflight-engine-11 at 2ce854a)
- Build 16: uploaded 18:24, VALID 18:29 Madrid, internal IN_BETA_TESTING ("0 A.D. interno"). External submit 422 ANOTHER_BUILD_IN_REVIEW (build 11 still in review).
- Changes: game setup settings columns laid out deterministically left of the tab column (removes the stray off-screen "…aps" column; GameSettingsPanel.js override in make-ios-mod.py) + map preview fits its box; options rows 40 lu / sans-bold-16, tab tooltips without keyboard hints; touch self-test taps an Options tab at 205 s (no tooltip seen); new AppIcon (hoplite, touchdemo/Assets.xcassets, single 1024 RGB universal, actool generates sizes); iPad: patch 0010 detects tablets (short side >= 600pt) and uses logical GUI >= 1400x880 (iPad Air 11 sim: scale 1.70, logical 1424x981; iPhone unchanged 2.00 / 1125x603); CI has an iPad landscape sim step (SIM_DEVICE "^iPad (Air|Pro) 11").
- Screens (run 40110433854): shots/b16/gamesetup.jpg, options-ingame.jpg, ipad-mainmenu.jpg, ipad-hud.jpg, ipad-options.jpg. Nothing clipped.
- Notes: the iPad simulator screenshot is portrait with the landscape app letterboxed (rows 635-1785 cropped). The sim .app has no compiled icon (only the TestFlight xcarchive runs actool). The iPad sim step needs ~relaunch on first boot.
- App name: CFBundleDisplayName/CFBundleName = "0 A.D.". ASC record name (appInfoLocalizations en-US) renamed 18:51 Madrid from "0 A.D. Verkvest" to "0 A.D. Mobile" ("0 A.D." rejected: 409 DUPLICATE.DIFFERENT_ACCOUNT, taken by another account).

## Update 2026-10-24 ~20:05 Madrid — App Store paid release prep (49.99 €), NOT submitted
- Draft metadata (names, subtitle, promo, EN/ES description with GPL/source + CC BY-SA Wildfire Games credit, keywords, category, age rating, privacy/support URLs, copyright): `docs/appstore-draft.md`. Nothing saved to ASC yet.
- ASC read-only: version 1.0 already exists (cce71224-…, PREPARE_FOR_SUBMISSION). ESP 49.99 price point exists (proceeds 35.04 € → looks like Small Business 85%). No price schedule/manual prices, no availability, no category, age rating unanswered, no review detail, no build attached, copyright empty, contentRights empty. Agreements/banking/tax/SBP not visible via API → check in ASC web UI (Business).
- verkvest.com/privacy and /support → 404 (privacy page must be published before submit). Repo has no LICENSE file detected by GitHub — add GPL-2.0+ LICENSE/COPYING before release.
- Screenshots: workflow `.github/workflows/appstore-shots.yml` (triggered by force-pushing branch `appstore-shots`; reuses app artifact of ios-build run 40110433854; `-conf=ios.shots:true` runs `gui/session/ios_shots.js` scene with stock cheats). Run 40116061338 OK. Output (gitignored): `shots/appstore/iphone69-0{1..4}-*.png` 2868x1320, `shots/appstore/ipad13-0{1..4}-*.png` 2752x2064 (iPad sim still letterboxed in portrait despite UIRequiresFullScreen → 2064x1548 crop upscaled ×1.33).
- Known shot-scene issues: all steps fire together at ~32 s (first session tick is late), camera moves don't seem to apply, army half hidden behind CC; own units die by ~120 s. Good enough for v1 set; improve camera placement for a nicer set later.
- Review risks: GPL vs App Store terms, "0 A.D." trademark (name + main-menu logo "0 A.D. Empires Ascendant"), "Exit" button in main menu (Apple dislikes app-quit), price 49.99 € for free software.

## Update 2026-10-24 ~21:20 Madrid — build 17 "Bronze Legions" (tag testflight-engine-12), App Store shots v3
- Build 17: ios-testflight run 40122947315 (workflow_dispatch on tag testflight-engine-12, app=engine; the tag push itself was
  skipped because the tagged commit message had [skip ci] — don't tag [skip ci] commits). Engine from ios-build run 40120025647 (47d3ecb).
  ASC: VALID, IN_BETA_TESTING, in internal group "0 A.D. interno" (21:02 Madrid).
- Review-risk fixes (ios/make-ios-mod.py): Exit hidden on iOS (iosHidden); the "0 A.D. Empires Ascendant" logo replaced by a text title
  from ONE constant `APP_TITLE` (env IOS_APP_TITLE overrides) = "Bronze Legions"; 0ADLogo sprites removed from load/replay screens.
  CFBundleDisplayName / window title also read APP_TITLE (package-engine-app.sh, make-engine-xcarchive.sh). Credits screen untouched.
  Bundle id unchanged (es.verkvest.zeroad).
- ASC en-US appInfoLocalization name = "Bronze Legions: Ancient RTS" (set via API with owner approval; was "0 A.D. Mobile").
  Nothing else saved; nothing submitted; no price set.
- Screenshots (shots/appstore/, gitignored): iphone69-01-mainmenu / 02-base-army / 03-battle / 04-overview (2868x1320),
  ipad13-01..04 same names (2752x2064). From appstore-shots run 40122318499.
  * Workflow: push an empty commit to branch appstore-shots (force); matrix of 2 jobs (iPhone Pro Max, iPad Pro 13 on runtime iOS-18
    so it is truly landscape — iPadOS 26 letterboxes). Scene = ios/mod/gui/session/ios_shots.js, timeline in SIM seconds
    (the sim runs ~0.1–0.2x real time: 520–560 s runs reach ~sim 41 s).
  * iPhone Dynamic Island pill is baked into simctl screenshots even with --mask=ignored: menu shot = crop x≥160 + upscale;
    in-game shots = pill area filled with a mirrored neighbour strip (x 30–166, y 455–865 of the rotated 2868x1320 frame).
  * Known cosmetics: a stray "1/2 >" build-grid page button stays visible after deselecting (HUD bug, fix later);
    palms near the CC partly cover the battle; civ differs per run (iPad got a different civ than iPhone).
- Open review risk: on real iPadOS 26 the landscape-only app can be letterboxed (UIRequiresFullScreen deprecated).

## Update 2026-10-24 ~23:10 Madrid — App Store preview videos + listing texts (NOT uploaded)
- appstore-shots run 40130706770 (SIM_VIDEO=1 → out/<dev>/run.mp4 via simctl recordVideo; engine app from ios-build 40120025647 = build 17).
  The simulator renders ~1 fps, so the preview is a time-lapse (segments sped up ~13–35x).
- scripts/make-preview-video.py → shots/appstore/preview-iphone69.mp4 (1920x886) and preview-ipad13.mp4 (1600x1200):
  H.264 High@4.0, 30 fps, ~10.7 Mbps, 27–28 s, silent AAC 256k stereo 48 kHz. Captions: Build your city / Raise your legions /
  Command epic battles / Ancient RTS for iPhone and iPad. Poster frame suggestion: 00:00:15 (preview-*-poster.png). Check frames in shots/appstore/preview-frames/.
- HUD fix: the build-grid page button ("1/2 >") is hidden when nothing is selected (ios_hud.js).
- docs/appstore-listing.md: EN/ES subtitle, promo, description, keywords, screenshot captions with character counts.

## Build 18 / home-screen name (2026-10-24 ~23:40 Madrid)
- User saw hoplite icon + label "0 A.D.": that is build 16 (tag testflight-engine-11, icon came in 43dd9ca, DisplayName still "0 A.D."; its IPA was named "0 A.D..ipa").
  Build 17 already had DisplayName "Bronze Legions" (IPA "Bronze Legions.ipa").
- ios-testflight.yml now unzips the exported IPA and fails before upload unless CFBundleDisplayName == IOS_APP_TITLE.
- testflight-engine-13 (dispatch run 40133851195, ios-build 40130705674 with HUD page-button fix) -> build 18:
  IPA CFBundleDisplayName=Bronze Legions, CFBundleName=Bronze Legions; ASC VALID / IN_BETA_TESTING.
- ASC listing uploads (screens/previews/localizations) still paused; nothing uploaded yet.

## ASC listing uploaded (2026-10-25 ~07:15 Madrid) — NOT submitted, no price
- appInfoLocalizations en-US + es-ES: name "Bronze Legions: Ancient RTS", subtitle, privacyPolicyUrl https://verkvest.com/privacy/bronze-legions (page still 404).
- Version 1.0 loc en-US + es-ES (es id 3781e3d2-…): description, keywords, promo text from docs/appstore-listing.md; supportUrl github issues, marketingUrl repo; copyright "2026 VERKVEST SL". Build 18 attached.
- Screenshots 4×APP_IPHONE_67 (2868x1320) + 4×APP_IPAD_PRO_3GEN_129 (2752x2064) per locale, all COMPLETE. Stills re-cut from post-HUD-fix shots run 40130706770
  (iPhone 016/070/250/420 s, iPad 016/060/330/540 s; iPhone pill patched with a feathered copy of the area to its right).
- Previews (from the same post-fix run): en-US preview-*.mp4, es-ES preview-*-es.mp4 (Spanish captions, last "Para iPhone y iPad"); all COMPLETE, poster 00:00:15:00.
- Paid Applications Agreement accepted 2026-10-24 20:32 Madrid (email); "active"/bank/tax status not visible via API.
- Remaining: privacy page, LICENSE file in repo, App Privacy, age rating questionnaire, category, price/availability, review contact details, submit.

## Pre-submission items (2026-10-25 ~07:20 Madrid) — still NOT submitted
- LICENSE (GPL-2.0 text) + LICENSING.md (code GPL-2.0-or-later, art CC BY-SA 3.0, icon CC BY-SA) on feature/ios-prototype (5ded254) and main (dec9163).
- Privacy page: GitHub Pages (branch gh-pages) https://verkvest.github.io/zeroad-ios/privacy/bronze-legions/ (200, EN/ES, "no data collected").
  verkvest.com A -> 156.67.26.239 (Contabo) — not touched. privacyPolicyUrl switched in en-US and es-ES.
- Age rating declaration filled -> 12+ (realistic violence + weapons infrequent/mild, messagingAndChat=true for direct-MP chat, rest none/false).
- Categories: Games / Strategy + Simulation. Review detail 987dec95-…: Aleksandr Verkhovod, +34 711 070 470, verkvest@gmail.com, no demo account, notes.
- Price schedule: base ESP, manual price 49.99 € (proceeds 34.96). Availability: all 175 territories, new territories on.
  Territory status: CANNOT_SELL everywhere (Paid Apps agreement/bank/tax not in effect yet) + TRADER_STATUS_NOT_PROVIDED in 27 EU territories (DSA trader declaration, web UI).
- Copyright changed to "2026 Aleksandr Verkhovod" (account is Individual, not VERKVEST SL).
- Web-UI only: App Privacy ("Data Not Collected"), DSA trader status, agreements/bank/tax.

## Submitted for review (2026-10-25 07:25 Madrid)
- reviewSubmission 95f57f46-a380-43da-8f36-98326e15d736: version 1.0 + build 18, state WAITING_FOR_REVIEW, release AFTER_APPROVAL. contentRightsDeclaration=USES_THIRD_PARTY_CONTENT. Owner approval: question card t473s1698.
