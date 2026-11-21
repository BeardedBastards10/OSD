"""Build site/boards-ardupilot.json from the official ArduPilot firmware manifest.

The browser cannot read firmware.ardupilot.org directly (no CORS headers), so this
runs on a schedule (or by hand) and the website reads the small JSON instead.
Only Copter stable releases are kept, because that is what the workflow builds.
"""
import gzip, io, json, re, sys, urllib.request, datetime

URL = "https://firmware.ardupilot.org/manifest.json.gz"
OUT = sys.argv[1] if len(sys.argv) > 1 else "site/boards-ardupilot.json"
MIN_VERSION = (4, 5, 0)

raw = urllib.request.urlopen(URL, timeout=120).read()
fw = json.load(gzip.open(io.BytesIO(raw)))["firmware"]

boards = {}
for x in fw:
    if x.get("vehicletype") != "Copter" or x.get("format") != "apj":
        continue
    m = re.fullmatch(r"STABLE-(\d+)\.(\d+)\.(\d+)", x.get("mav-firmware-version-type", ""))
    if not m or tuple(map(int, m.groups())) < MIN_VERSION:
        continue
    b = boards.setdefault(x["platform"], {"id": x.get("board_id"), "v": set()})
    b["v"].add(x["mav-firmware-version"])

def vkey(v): return tuple(int(p) for p in v.split("."))
versions = sorted({v for b in boards.values() for v in b["v"]}, key=vkey, reverse=True)
out = {
    "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "source": URL,
    "vehicle": "Copter",
    "versions": versions,
    "boards": {n: {"id": b["id"], "v": sorted(b["v"], key=vkey, reverse=True)} for n, b in sorted(boards.items(), key=lambda kv: kv[0].lower())},
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, separators=(",", ":"))
print(f"wrote {OUT}: {len(out['boards'])} boards, versions {versions[:4]}...")
