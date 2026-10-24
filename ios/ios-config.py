#!/usr/bin/env python3
"""Applies iOS defaults to the bundled config/default.cfg (in place). The player's own
settings (user.cfg in the app sandbox) still override these.
Usage: ios-config.py <default.cfg>"""
import re, sys

SETTINGS = {
    # (section, key): value      section "" = top of file
    ("", "hidpi"): "true",
    ("", "shadows"): "false",
    ("", "watereffects"): "true",
    ("", "waterfancyeffects"): "false",
    ("", "waterrealdepth"): "false",
    ("", "waterrefraction"): "false",
    ("", "waterreflection"): "false",
    ("", "silhouettes"): "false",
    ("", "postproc"): "false",
    ("", "renderer.scale"): "1.0",
    ("", "renderer.upscale.technique"): '"bilinear"',
    ("", "gpuskinning"): "false",
    ("", "smoothlos"): "false",
    ("", "textures.quality"): "2",
    ("", "textures.maxanisotropy"): "2",
    ("", "materialmgr.quality"): "2.0",
    ("", "pauseonfocusloss"): "true",
    ("adaptivefps", "menu"): "30",
    ("adaptivefps", "session"): "60",
    ("gui.splashscreen", "enable"): "false",
    ("gui.session", "dragdelta"): "12",
    ("mod", "enabledmods"): '"mod public ios"',
}

path = sys.argv[1]
lines = open(path, encoding="utf-8").read().split("\n")
section = ""
done = set()
out = []
for line in lines:
    m = re.match(r"\s*\[([^\]]*)\]", line)
    if m:
        section = m.group(1).strip()
    else:
        m = re.match(r"(\s*)([A-Za-z0-9_.]+)(\s*=\s*)", line)
        if m and (section, m.group(2)) in SETTINGS:
            key = (section, m.group(2))
            line = f"{m.group(1)}{m.group(2)}{m.group(3)}{SETTINGS[key]} ; iOS port default"
            done.add(key)
    out.append(line)
# keys not present in the file: add right after the matching section header
for (sec, key), val in SETTINGS.items():
    if (sec, key) in done:
        continue
    if sec == "":
        idx = 0
    else:
        idx = next(i for i, l in enumerate(out) if re.match(r"\s*\[" + re.escape(sec) + r"\]", l)) + 1
    out.insert(idx, f"{key} = {val} ; iOS port default")
open(path, "w", encoding="utf-8").write("\n".join(out))
print("iOS config applied:", len(done), "changed,", len(SETTINGS) - len(done), "added")
