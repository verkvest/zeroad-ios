#!/usr/bin/env python3
"""Launch an .app in the iOS Simulator for N seconds, capture its stdout/stderr and a screenshot.
Usage: sim-launch.py <App.app> <bundle-id> <out-dir> [seconds] [app args...]"""
import json, os, subprocess, sys, time

app, bundle, out = sys.argv[1:4]
secs = int(sys.argv[4]) if len(sys.argv) > 4 else 60
args = sys.argv[5:]
every = int(os.environ.get("SHOT_EVERY", "60"))
os.makedirs(out, exist_ok=True)

def run(*a, check=False, **kw):
    print("+", " ".join(a), flush=True)
    return subprocess.run(list(a), check=check, text=True, **kw)

devs = json.loads(subprocess.check_output(["xcrun", "simctl", "list", "devices", "available", "-j"], text=True))["devices"]
cands = sorted((rt, d["name"], d["udid"]) for rt, lst in devs.items() if "iOS" in rt for d in lst if d["name"].startswith("iPad" if "iPad" in os.environ.get("SIM_DEVICE", "") else "iPhone"))
# Prefer a current notched/Dynamic Island phone (safe areas), e.g. "iPhone 17 Pro"; SIM_DEVICE overrides.
import re
pat = re.compile(os.environ.get("SIM_DEVICE", r"^iPhone \d+ Pro$"))
pref = [c for c in cands if pat.search(c[1])]
runtime, name, udid = (sorted(pref, key=lambda c: (c[0], int(re.sub(r"\D", "", c[1]) or 0)))[-1] if pref else cands[-1])
print(f"Using simulator {name} ({runtime})", flush=True)
run("xcrun", "simctl", "boot", udid)
run("xcrun", "simctl", "bootstatus", udid, "-b", check=True)
run("xcrun", "simctl", "install", udid, app, check=True)
logf = open(os.path.join(out, "engine-run.log"), "w")
def launch():
    return subprocess.Popen(["xcrun", "simctl", "launch", "--console-pty", "--terminate-running-process", udid, bundle] + args,
                            stdout=logf, stderr=subprocess.STDOUT)
p = launch()
relaunched = False
for i in range(secs):
    time.sleep(1)
    # A freshly booted simulator (still migrating data) sometimes never starts the app: no engine
    # output after 20 s -> launch once more.
    if i == 20 and not relaunched and os.path.getsize(os.path.join(out, "engine-run.log")) < 300:
        print("no engine output after 20 s, relaunching", flush=True)
        relaunched = True
        run("xcrun", "simctl", "terminate", udid, bundle)
        p.kill()
        p = launch()
    if p.poll() is not None:
        print(f"app exited after ~{i+1}s with {p.returncode}", flush=True)
        break
    if i in (15, 45, 90) or (i % every == every - 1) or i == secs - 2:
        run("xcrun", "simctl", "io", udid, "screenshot", os.path.join(out, f"engine-{i+1:03d}s.png"))
run("xcrun", "simctl", "terminate", udid, bundle)
time.sleep(1)
if p.poll() is None:
    p.kill()
logf.close()
# copy the engine's own logs (mainlog.html, crashlog) from the app sandbox
cont = subprocess.run(["xcrun", "simctl", "get_app_container", udid, bundle, "data"], text=True, capture_output=True).stdout.strip()
if cont:
    run("bash", "-c", f'find "{cont}" -name "*.html" -o -name "*.txt" -o -name "*.log" | head -20 | while read f; do cp "$f" "{out}/" ; done')
print(open(os.path.join(out, "engine-run.log")).read()[-6000:])
