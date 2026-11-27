"""Build site/boards-ardupilot.json from the official ArduPilot firmware manifest.

The browser cannot read firmware.ardupilot.org directly (no CORS headers), so this
runs on a schedule (or by hand) and the website reads the small JSON instead.
Only the NEWEST stable Copter release is kept, and only the boards that have it.
When ArduPilot publishes 4.7.4 the next run switches the whole site to 4.7.4.
"""
import gzip, io, json, re, sys, urllib.request, datetime

URL = "https://firmware.ardupilot.org/manifest.json.gz"
OUT = sys.argv[1] if len(sys.argv) > 1 else "site/boards-ardupilot.json"

raw = urllib.request.urlopen(URL, timeout=120).read()
fw = json.load(gzip.open(io.BytesIO(raw)))["firmware"]

def vkey(v): return tuple(int(p) for p in v.split("."))

stable = []
for x in fw:
    if x.get("vehicletype") != "Copter" or x.get("format") != "apj":
        continue
    if re.fullmatch(r"STABLE-\d+\.\d+\.\d+", x.get("mav-firmware-version-type", "")):
        stable.append(x)

newest = max((x["mav-firmware-version"] for x in stable), key=vkey)
boards = {}
for x in stable:
    if x["mav-firmware-version"] == newest:
        boards[x["platform"]] = {"id": x.get("board_id")}

# Per-board feature flags from the official build (features.txt): is scripting / the OSD compiled in?
# Low-flash boards leave scripting out, so the VTX power script cannot run on them.
import concurrent.futures

def features(board):
    url = f"https://firmware.ardupilot.org/Copter/stable-{newest}/{board}/features.txt"
    try:
        feats = set(urllib.request.urlopen(url, timeout=30).read().decode().split())
    except Exception:
        return board, None
    return board, {"s": int("AP_SCRIPTING_ENABLED" in feats), "o": int("OSD_ENABLED" in feats)}

with concurrent.futures.ThreadPoolExecutor(max_workers=16) as ex:
    for name, f in ex.map(features, list(boards)):
        if f:
            boards[name].update(f)

out = {
    "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "source": URL,
    "vehicle": "Copter",
    "version": newest,
    "boards": dict(sorted(boards.items(), key=lambda kv: kv[0].lower())),
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"))
noscript = sum(1 for b in boards.values() if b.get("s") == 0)
print(f"wrote {OUT}: Copter {newest}, {len(boards)} boards, {noscript} without scripting")
