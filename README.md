# MGRS on OSD

Firmware builds for flight controllers. Run **Actions, Build firmware, Run workflow** and choose the firmware:

| Choice | What you get |
|---|---|
| **ArduPilot** | **Adjustable VTX power** (`vtx_power.lua`, 6-position switch) **and MGRS on the OSD** (replaces GPS latitude/longitude) |
| **Betaflight** | **MGRS on the OSD** (replaces GPS latitude/longitude). Betaflight handles VTX power by itself. |

Defaults: ArduPilot `Copter-4.7.2`, Betaflight `2026.6.2`, board `DAKEFPVH743`.

Full steps for building, flashing and setting it up are in `MGRS_OSD_BUILD_GUIDE.md` (kept outside this repo for now).
