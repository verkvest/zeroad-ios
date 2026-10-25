#!/usr/bin/env python3
"""Boot an iOS Simulator, install an .app, run it with --selftest, check the output, take a screenshot.
Usage: sim-run.py <App.app> <bundle-id> <out-dir>"""
import json, os, subprocess, sys, time

app, bundle, out = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(out, exist_ok=True)

def run(*a, **kw):
    print("+", " ".join(a), flush=True)
    return subprocess.run(list(a), check=kw.pop("check", True), text=True, **kw)

devs = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "-j"], text=True))["devices"]
cands = []
for runtime, lst in devs.items():
    if "iOS" not in runtime:
        continue
    for d in lst:
        if d["name"].startswith("iPhone"):
            cands.append((runtime, d["name"], d["udid"]))
if not cands:
    sys.exit("no iPhone simulator available")
cands.sort()
runtime, name, udid = cands[-1]
print(f"Using simulator {name} ({runtime}) {udid}", flush=True)
run("xcrun", "simctl", "boot", udid, check=False)
run("xcrun", "simctl", "bootstatus", udid, "-b")
run("xcrun", "simctl", "install", udid, app)

# 1) self-test run (app exits when done)
try:
    p = run("xcrun", "simctl", "launch", "--console-pty", "--terminate-running-process", udid, bundle, "--selftest",
            capture_output=True, timeout=180, check=False)
    log = (p.stdout or "") + (p.stderr or "")
except subprocess.TimeoutExpired as e:
    log = (e.stdout or b"").decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    log += "\n[timeout]"
open(os.path.join(out, "selftest.log"), "w").write(log)
print(log, flush=True)

# 2) interactive run with the self-test gestures replayed, then screenshot
env = dict(os.environ, SIMCTL_CHILD_TOUCHDEMO_SELFTEST="1", SIMCTL_CHILD_TOUCHDEMO_STAY="1")
run("xcrun", "simctl", "launch", "--terminate-running-process", udid, bundle, env=env, check=False)
time.sleep(8)
run("xcrun", "simctl", "io", udid, "screenshot", os.path.join(out, "screenshot.png"), check=False)
run("xcrun", "simctl", "terminate", udid, bundle, check=False)

if "SELFTEST PASS" not in log:
    sys.exit("self-test did not pass")
print("Simulator self-test passed")
