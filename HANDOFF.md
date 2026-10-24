# HANDOFF — 0 A.D. iOS port (state notes for the next agent)

Updated: 2026-10-24 11:15 (Europe/Madrid)

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
2. If device engine job succeeded: tag `testflight-engine-5` (build number = ios-testflight run_number,
   CFBundleVersion set automatically) -> milestone "skirmish playable".
3. Then: real-device perf feedback from Aleksandr, touch UI polish (bigger GUI scale option).

## Notes
- Next free TestFlight tag: testflight-engine-5.
- Pushing to feature/ios-prototype cancels the running ios-build (concurrency); use "[skip ci]" for doc commits.
- PR-triggered duplicate runs are cancelled manually to save macOS runners.
- Patches 0001..0008 in patches/0ad; regenerate a patch by committing tmp in build/0ad, editing, `git diff HEAD -- source`, then `git reset --mixed a2cae4d`.
