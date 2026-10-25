#!/usr/bin/env python3
"""Repack the official 0 A.D. 0.28.0 'public' mod archive for mobile (iOS).

Input : public.zip from the release data tarball (0ad-0.28.0-unix-data.tar.xz); art CC-BY-SA 3.0,
        code GPLv2+ (Wildfire Games, https://play0ad.com). File names are unchanged so the engine
        loads the result as the regular 'public' mod.
Changes:
  * DDS textures: top mip levels dropped so the largest side is <= CAP (terrain 512, normal/spec 128,
    others 256; GUI and cursor textures untouched). DXT data is kept (the engine decodes it in
    software when the GPU lacks S3TC, as on iOS).
  * music re-encoded to Vorbis q0 (~64 kbit/s) with ffmpeg;
  * Vulkan SPIR-V shaders dropped (the iOS build uses the GL ES backend);
  * campaign scenarios dropped, a set of small skirmish maps kept (all random maps kept);
  * everything except .ogg/.png is deflated.
Usage: pack-mobile-data.py <in public.zip> <out public.zip>
"""
import os, struct, subprocess, sys, tempfile, threading, zipfile
from concurrent.futures import ThreadPoolExecutor

KEEP_SKIRMISH = {
    "acropolis_bay_2p", "alpine_valleys_2p", "farmland_2p", "golden_oasis_2p", "greek_acropolis_2p",
    "mediterranean_cove_2p", "oceanside_2p", "sicilia_2p", "skirmish_demo_2p", "median_oasis_4p",
    "forest_battle_4p", "corinthian_isthmus_2p",
}

def cap_for(name):
    n = name.lower()
    if not n.startswith("art/textures/") or n.startswith(("art/textures/ui/", "art/textures/cursors/")):
        return None
    base = os.path.basename(n)
    if "_norm" in base or "_spec" in base or "normal" in base:
        return 128
    if n.startswith("art/textures/terrain/"):
        return 512
    return 256

def trim_dds(data, cap):
    if len(data) < 128 or data[:4] != b"DDS ":
        return data
    h, w = struct.unpack_from("<II", data, 12)
    mips = max(1, struct.unpack_from("<I", data, 28)[0])
    fourcc = data[84:88]
    if fourcc == b"DXT1":
        bs = 8
    elif fourcc in (b"DXT3", b"DXT5"):
        bs = 16
    else:
        return data
    def lsize(ww, hh):
        return max(1, (ww + 3) // 4) * max(1, (hh + 3) // 4) * bs
    drop = 0
    while max(w >> drop, h >> drop) > cap and mips - drop > 1:
        drop += 1
    if drop == 0:
        return data
    off = 128
    for i in range(drop):
        off += lsize(max(1, w >> i), max(1, h >> i))
    nw, nh = max(1, w >> drop), max(1, h >> drop)
    expected = sum(lsize(max(1, nw >> i), max(1, nh >> i)) for i in range(mips - drop))
    if len(data) - off != expected:
        return data  # unexpected layout: leave untouched
    hdr = bytearray(data[:128])
    struct.pack_into("<II", hdr, 12, nh, nw)
    struct.pack_into("<I", hdr, 20, lsize(nw, nh))
    struct.pack_into("<I", hdr, 28, mips - drop)
    return bytes(hdr) + data[off:]

def reencode_ogg(data):
    with tempfile.TemporaryDirectory() as d:
        i, o = os.path.join(d, "i.ogg"), os.path.join(d, "o.ogg")
        with open(i, "wb") as f:
            f.write(data)
        r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", i, "-map_metadata", "0",
                            "-c:a", "libvorbis", "-q:a", "0", o])
        if r.returncode == 0 and os.path.getsize(o) < len(data):
            with open(o, "rb") as f:
                return f.read()
    return data

def keep(name):
    if name.startswith(("shaders/spirv/", "maps/scenarios/")):
        return False
    if name.startswith("maps/skirmishes/"):
        return os.path.basename(name).split(".")[0] in KEEP_SKIRMISH
    return True

def main():
    src, dst = sys.argv[1], sys.argv[2]
    zin = zipfile.ZipFile(src)
    infos = [i for i in zin.infolist() if not i.is_dir() and keep(i.filename)]
    before = sum(i.file_size for i in zin.infolist())
    tl = threading.local()
    stats = {"dds_trimmed": 0, "ogg": 0}
    def job(info):
        if not hasattr(tl, "z"):
            tl.z = zipfile.ZipFile(src)
        name = info.filename
        data = tl.z.read(name)
        if name.endswith(".dds"):
            cap = cap_for(name)
            if cap:
                new = trim_dds(data, cap)
                if len(new) != len(data):
                    stats["dds_trimmed"] += 1
                data = new
        elif name.startswith("audio/music/") and name.endswith(".ogg"):
            data = reencode_ogg(data)
            stats["ogg"] += 1
        return name, data, info.date_time
    with zipfile.ZipFile(dst, "w") as zout, ThreadPoolExecutor(os.cpu_count() or 4) as ex:
        for name, data, dt in ex.map(job, infos, chunksize=32):
            zi = zipfile.ZipInfo(name, dt)
            zi.compress_type = zipfile.ZIP_STORED if name.endswith((".ogg", ".png")) else zipfile.ZIP_DEFLATED
            zout.writestr(zi, data, compresslevel=6)
    print(f"{len(infos)} files kept, {stats}, {before >> 20} MB -> {os.path.getsize(dst) >> 20} MB")

if __name__ == "__main__":
    main()
