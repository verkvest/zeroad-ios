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
