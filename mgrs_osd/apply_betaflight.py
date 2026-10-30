#!/usr/bin/env python3
"""Make Betaflight's OSD show MGRS in place of GPS latitude/longitude.

Usage: apply_betaflight.py <path to betaflight checkout>

- Copies mgrs_core.h to src/main/osd/mgrs_core.h
- The GPS Latitude element now shows the MGRS grid reference (whatever variant
  is selected); the GPS Longitude element shows nothing.
- The conversion runs at most once per second and only when the position
  changed, because it uses double-precision maths (slow on F4 targets).
Fails loudly if the source layout is not what it expects.
"""
import pathlib
import shutil
import sys

root = pathlib.Path(sys.argv[1])
here = pathlib.Path(__file__).resolve().parent
osd = root / "src" / "main" / "osd"
src = osd / "osd_elements.c"

shutil.copyfile(here / "mgrs_core.h", osd / "mgrs_core.h")

text = src.read_bytes().decode("utf-8")

inc = '#include "osd/osd_elements.h"\n'
assert text.count(inc) == 1, "include anchor not found exactly once"
text = text.replace(inc, inc + '\n#ifdef USE_GPS\n#include "osd/mgrs_core.h"\n#endif\n')

OLD = '''    osdFormatCoordinate(element->buff, coordinateType, element->type);
    if (STATE(GPS_FIX_EVER) && !STATE(GPS_FIX)) {'''
NEW = '''    osdFormatCoordinate(element->buff, coordinateType, element->type);
    // MGRS replaces latitude/longitude: latitude shows the grid reference, longitude is blank
    if (coordinateType == GPS_LONGITUDE) {
        element->buff[0] = '\\0';
    } else if (STATE(GPS_FIX_EVER)) {
        static char mgrsText[24] = "";
        static int32_t mgrsLat, mgrsLon;
        static uint32_t mgrsAtMs;
        const uint32_t nowMs = millis();
        if (mgrsText[0] == '\\0' || ((gpsSol.llh.lat != mgrsLat || gpsSol.llh.lon != mgrsLon) && (nowMs - mgrsAtMs) >= 1000)) {
            if (!mgrsFormat(gpsSol.llh.lat, gpsSol.llh.lon, MGRS_DIGITS, mgrsText, sizeof(mgrsText))) {
                mgrsText[0] = '\\0';
            }
            mgrsLat = gpsSol.llh.lat;
            mgrsLon = gpsSol.llh.lon;
            mgrsAtMs = nowMs;
        }
        strcpy(element->buff, mgrsText[0] ? mgrsText : "--- -- ---- ----");
    } else {
        strcpy(element->buff, "--- -- ---- ----");
    }
    if (STATE(GPS_FIX_EVER) && !STATE(GPS_FIX)) {'''
assert text.count(OLD) == 1, "osdElementGpsCoordinate body not found exactly once"
text = text.replace(OLD, NEW)
# the shared header names its function mgrs_format; use that name here
text = text.replace("mgrsFormat(", "mgrs_format(")
src.write_bytes(text.encode("utf-8"))
print("Betaflight OSD patched: GPS LAT element = MGRS, GPS LON element = blank")
