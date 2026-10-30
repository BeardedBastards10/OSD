#!/usr/bin/env python3
"""Make ArduPilot's OSD show MGRS in place of GPS latitude/longitude.

Usage: apply_ardupilot.py <path to ardupilot checkout>

- Copies mgrs_core.h to libraries/AP_OSD/AP_OSD_MGRS.h
- draw_gps_latitude()  now draws the MGRS grid reference (enable OSDn_GPSLAT_EN)
- draw_gps_longitude() now draws nothing (leave OSDn_GPSLONG_EN off)
Fails loudly if the source layout is not what it expects.
"""
import pathlib
import re
import shutil
import sys

root = pathlib.Path(sys.argv[1])
here = pathlib.Path(__file__).resolve().parent
osd = root / "libraries" / "AP_OSD"
src = osd / "AP_OSD_Screen.cpp"

shutil.copyfile(here / "mgrs_core.h", osd / "AP_OSD_MGRS.h")

text = src.read_bytes().decode("utf-8")

# 1. include (once, after AP_OSD_Backend.h)
inc = '#include "AP_OSD_Backend.h"\n'
assert text.count(inc) == 1, "include anchor not found exactly once"
text = text.replace(inc, inc + '#include "AP_OSD_MGRS.h"\n')

NEW_LAT = '''void AP_OSD_Screen::draw_gps_latitude(uint8_t x, uint8_t y)
{
    // MGRS replaces latitude/longitude: this element shows the grid reference
    AP_GPS & gps = AP::gps();
    char buff[24];
    if (gps.status() >= AP_GPS::GPS_OK_FIX_3D) {
        const Location &loc = gps.location();
        if (mgrs_format(loc.lat, loc.lng, MGRS_DIGITS, buff, sizeof(buff))) {
            backend->write(x, y, false, "%s", buff);
            return;
        }
    }
    backend->write(x, y, false, "--- -- ---- ----");
}
'''
NEW_LON = '''void AP_OSD_Screen::draw_gps_longitude(uint8_t x, uint8_t y)
{
    // intentionally blank: MGRS is shown by the latitude element
    (void)x;
    (void)y;
}
'''

def swap(text, name, new):
    pat = re.compile(r"void AP_OSD_Screen::" + name + r"\(uint8_t x, uint8_t y\)\n\{.*?\n\}\n", re.S)
    matches = pat.findall(text)
    assert len(matches) == 1, f"{name}: expected 1 match, got {len(matches)}"
    return pat.sub(lambda m: new, text)

text = swap(text, "draw_gps_latitude", NEW_LAT)
text = swap(text, "draw_gps_longitude", NEW_LON)
src.write_bytes(text.encode("utf-8"))
print("ArduPilot OSD patched: GPSLAT element = MGRS, GPSLONG element = blank")
