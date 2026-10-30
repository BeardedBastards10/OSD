# MGRS on OSD - build and flash guide

Last updated 30 Oct 2026. Covers ArduPilot (Copter) and Betaflight, step by step, using GitHub to build the firmware.

Status: built and compile-checked on GitHub. Reported working on the owner's ArduPilot and Betaflight drones (30 Oct 2026).

## 1. What this does

| Firmware | What the build contains | What you see on the OSD |
|---|---|---|
| **ArduPilot** (Copter) | **Adjustable VTX power** (the 6-position switch script, vtx_power.lua) **and MGRS on OSD** | The GPS Latitude element shows MGRS. The Longitude element is blank. |
| **Betaflight** | **MGRS on OSD**, built with your saved cloud-build options | The GPS Latitude element shows MGRS. The Longitude element is blank. |

Example of what the OSD shows: `18S UJ 2339 0739` (grid zone, 100 km square, then 4 digits east and 4 digits north = 10 m precision).

Before a 3D GPS fix the OSD shows `--- -- ---- ----`.

## 2. Why it is built on GitHub

Neither firmware has an MGRS setting. You cannot add it with the CLI, parameters, or a script: ArduPilot Lua cannot draw OSD elements, and Betaflight has no scripting. So this repo patches the firmware's OSD code and GitHub builds the firmware in the cloud. You download it and flash it like any custom firmware. Nothing to install on your PC.

The build always uses the **newest stable release** of ArduPilot or Betaflight, found automatically each time you run it.

## 3. What you need

- Your GitHub login, and this repo: github.com/ericma1991-dot/mgrs-on-osd (private, only you can see it).
- Mission Planner (ArduPilot) and/or Betaflight Configurator.
- A USB cable, and the drone.
- Your board name (Step 1 below).

## 4. Step 1 - find your board name

The board name must match your flight controller. A wrong one will not run properly.

- **ArduPilot:** Mission Planner, Data screen, Messages tab. Reboot the board and read the boot messages. The line after `ChibiOS:` starts with the board name, for example `DAKEFPVH743 001C002A ...`. The first word is the board.
- **Betaflight:** Configurator, CLI tab, type `diff all`. Find the line `board_name ...`, for example `board_name DAKEFPVH743`.

## 5. Step 2 - back up your settings

Do this before every flash.

- **ArduPilot:** Mission Planner, Config, Full Parameter List, **Save to file**. Name it with the drone, version and date, for example `10inch_ardu_4.7.2_2026-10-30.param`.
- **Betaflight:** CLI tab, type `diff all`, then save the output with the **Save to File** button (or copy it into a text file). Use `diff all`, not `dump`.

Your settings live in the flight controller, apart from the firmware. A normal update keeps them. A big version jump can reset some, which is why you back up and check afterwards.

## 6. Step 3 - run the build on GitHub

1. Sign in at github.com and open the repo **ericma1991-dot/mgrs-on-osd**.
2. Click the **Actions** tab.
3. On the left, click **Build firmware (Betaflight or ArduPilot)**.
4. Click **Run workflow** (right side, grey button).
5. **STEP 1 - FIRMWARE:** choose **ArduPilot** or **Betaflight**.
6. **STEP 2 - BOARD:** type your board name (it defaults to DAKEFPVH743).
7. Click the green **Run workflow** button.
8. Refresh the page and open the new run. Yellow means running, a green tick means done, a red cross means it failed.

How long it takes: ArduPilot about 20 minutes. Betaflight about 2 to 10 minutes.

If the board name is wrong, the build stops within seconds and lists similar names in the log. Fix the name and run it again.

**Download the firmware:** on the finished run page, scroll to **Artifacts** and click the file name. It downloads a zip. Unzip it.

| Firmware | Download name | File you need |
|---|---|---|
| ArduPilot | `ardupilot-<version>-<board>-vtx-power-and-mgrs` | `arducopter.apj` |
| Betaflight | `betaflight-<version>-<board>-mgrs` | the `.hex` file |

## 7. Step 4A - flash ArduPilot

1. Back up your parameters (Step 2).
2. Plug the board in by USB and open Mission Planner. Leave it disconnected (do not click Connect) and go to the Setup tab.
3. Setup, **Install Firmware**, then at the bottom click **Load custom firmware**.
4. Pick `arducopter.apj` from the unzipped download.
5. Wait for it to finish. Do not unplug the cable.
6. Reconnect. Your parameters normally stay in place. If anything looks reset, use Config, Full Parameter List, **Load from file**, choose your backup, then **Write Params** and reboot.
7. Check the Messages tab shows `VTXA: serial open, 9600 baud, Tramp`. That confirms the VTX power script is running.

## 8. Step 4B - flash Betaflight

1. Back up with `diff all` (Step 2) and check `board_name` matches the build you downloaded.
2. Close the CLI and disconnect from the drone in Configurator.
3. Open the **Firmware Flasher** tab.
4. Click **Load Firmware [Local]** and pick the `.hex` file.
5. Leave **Full chip erase** switched **off**. This keeps your settings.
6. Click **Flash Firmware** and wait for it to finish.
7. If the board is not found, put it in DFU mode: hold the boot button while plugging in USB. On Windows you may need the ImpulseRC Driver Fixer (or Zadig) once.
8. Connect again. If anything did not carry over, open the CLI, paste your saved `diff all`, and type `save`.

## 9. Step 5 - turn MGRS on in the OSD

One element shows MGRS: the **latitude** element. The longitude element stays blank, so leave it off.

**ArduPilot:** in Mission Planner, Config, Full Parameter List, set these and Write Params:

| Parameter | Value |
|---|---|
| `OSD_TYPE` | 1 (analog MAX7456 OSD; keep what already works for you) |
| `OSD1_ENABLE` | 1 |
| `OSD1_GPSLAT_EN` | 1 (this element shows MGRS) |
| `OSD1_GPSLAT_X` and `OSD1_GPSLAT_Y` | where you want it on screen. It is 16 characters wide, so keep X at 13 or less. |
| `OSD1_GPSLONG_EN` | 0 |
| `OSD1_PLUSCODE_EN` | 0 |

ArduPilot has separate OSD screens (`OSD1_` to `OSD4_`). Enable the element on the screen you actually view, and if you change screens with a radio channel, make sure that channel is on that screen.

**Betaflight:** in Configurator, OSD tab:

1. Enable the **Latitude** element (also labelled "GPS Lat"). This is the one that shows MGRS.
2. Drag it where you want it. It is about 16 characters wide, so leave room. If it was a latitude before, move it, because it is wider now.
3. Leave **Longitude** off.
4. Any variant of the element (decimal, degrees/minutes/seconds, Plus Code) shows MGRS.
5. Click **Save**, and check the element is on the OSD profile you use.

## 10. Step 6 - check it works

- You need a **3D GPS fix**, so go outside. Before the fix it shows dashes.
- Compare against any online MGRS converter, typing in the lat/long your GPS shows. At 10 m precision they should agree on the digits shown.
- Reference point: lat 38.8977, long -77.0365 reads `18S UJ 2339 0739`.
- **Betaflight:** in the CLI, type `options`. The list should include these numbers: 4097 (CRSF), 8231 (DSHOT), 16416 (analog OSD), 16422, 16407, 16427, 16412, 16428, 16415, 16418, 16425, 16429, 16420 and 16421. If any are missing, the build is missing a feature.
- **ArduPilot:** move your VTX power switch and check the Messages tab shows `VTXA: power pos N -> ...` lines.

## 11. If something goes wrong

| Problem | Likely cause and fix |
|---|---|
| Build is red | Open the run, click the red step, find the first line that starts with `error:` and send it to Claude. |
| Build stops fast and lists names | Board name is wrong. Use the name from Step 1 and run again. |
| "Patch OSD" step is red | A new release changed the OSD code. Send the log line to Claude. Your old firmware still works. |
| OSD shows dashes | No 3D GPS fix yet. Wait or go outside. |
| OSD shows nothing there | Element not enabled, off screen, or on a different OSD screen or profile (Step 5). |
| Values look wrong | Stop. Note the lat/long and what the OSD shows, and tell Claude. Do not navigate with it until it is checked. |
| Settings reset after flashing | Reload your backup (ArduPilot: Load from file. Betaflight: paste `diff all`, then `save`). |
| Betaflight servo or range finder gone | Check the `options` list in Step 6. The baseline in section 13 includes them. |
| Board not detected for flashing | DFU mode and driver (Step 4B, step 7). |

## 12. New versions

- Run the build again any time. It finds the newest stable release by itself, so there is nothing to update.
- It does not notice new releases on its own. It only checks when you press Run.
- Betas and release candidates are skipped on purpose.
- Update one drone first, bench-test it or fly it, then do the rest.
- Keep the last firmware file that worked. GitHub deletes build downloads after about 90 days, so save the one you trust. It is your way back.

## 13. Other drones and changing the setup

- **Different board:** only STEP 2 changes. Use that drone's board name (Step 1).
- **Betaflight options:** the build uses your saved cloud-build options: CRSF radio, automatic telemetry, analog OSD, DSHOT, plus Altitude Hold, Cam. Control, Flight Plan, GPS, Optical Flow, Magnetometers, Pin IO, Position Hold, Range Finder, Servos and VTX. They are stored as `BF_OPTIONS` in `.github/workflows/build.yml`. To change them, open that file on GitHub, click the pencil, edit the list, and commit.
- **1 m precision instead of 10 m:** in `mgrs_osd/mgrs_core.h`, change `#define MGRS_DIGITS 4` to `5`, commit, then run the build again. The readout gets one character wider per number.
- **ArduPilot VTX power levels:** those are the `VTXA_` parameters from the script, so most tuning needs no rebuild.

## 14. Going back to stock

- **ArduPilot:** Mission Planner, Setup, Install Firmware, pick the normal Copter firmware. Then reload your parameter backup if needed.
- **Betaflight:** Firmware Flasher, pick the normal release for your board, flash with Full chip erase off. Then paste your `diff all` if needed.

## 15. What is in this repo

| File | What it does |
|---|---|
| `.github/workflows/build.yml` | The build. Choose firmware and board, it does the rest. |
| `mgrs_osd/mgrs_core.h` | The latitude/longitude to MGRS maths (C), shared by both firmwares. |
| `mgrs_osd/apply_ardupilot.py` | Patches ArduPilot's OSD to show MGRS. |
| `mgrs_osd/apply_betaflight.py` | Patches Betaflight's OSD to show MGRS. |
| `mgrs_osd/test_mgrs.c` and `compare.py` | A self-test run by the build against a reference MGRS library. |
| `vtx_power.lua` | The adjustable VTX power script, added to ArduPilot builds. |

## 16. Limits and safety

- MGRS is shown to 10 m precision, WGS84 datum. It is not supported in polar regions (north of 84 N, south of 80 S); the OSD shows dashes there.
- It is a display aid. Do not use it as your only navigation reference.
- A wrong board name builds firmware that will not run properly on your controller. Always check the name first.
- Never transmit on the VTX without an antenna or dummy load, and keep airflow on it. High VTX power needs a licence in most countries.
