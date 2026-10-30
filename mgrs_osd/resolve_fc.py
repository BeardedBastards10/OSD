#!/usr/bin/env python3
"""Work out which firmware version and board to build.

Reads these environment variables (set by the workflow):
  FIRMWARE       ArduPilot or Betaflight
  FC_INFO        text pasted from the flight controller (optional)
  INPUT_VERSION  version typed in the form: a tag, "latest" or blank
  INPUT_BOARD    board typed in the form

Pasted text wins over the typed version and board. It can be:
  ArduPilot  the boot Messages (needs "ArduCopter V4.7.2" and the board line)
  Betaflight the CLI "diff all" or "version" output (needs the version and board_name)
The text may arrive on one line (a form box strips line breaks), so only
patterns are used, never line positions.

Writes TAG and BOARD to $GITHUB_ENV and tag and board to $GITHUB_OUTPUT.
"""
import os
import re
import subprocess
import sys


def fail(msg):
    print(f"ERROR: {msg}")
    sys.exit(1)


firmware = os.environ.get("FIRMWARE", "")
info = " ".join(os.environ.get("FC_INFO", "").split())
typed_version = os.environ.get("INPUT_VERSION", "").strip()
typed_board = os.environ.get("INPUT_BOARD", "").strip()

if firmware not in ("ArduPilot", "Betaflight"):
    fail(f"FIRMWARE must be ArduPilot or Betaflight, got '{firmware}'")

version = ""
board = ""
source = "the form boxes"

if info:
    looks_ardu = bool(re.search(r"Ardu(Copter|Plane|Rover|Sub)|ChibiOS", info))
    looks_bf = bool(re.search(r"Betaflight|board_name", info))
    if firmware == "ArduPilot":
        if looks_bf and not looks_ardu:
            fail("the pasted text looks like Betaflight output, but STEP 1 says ArduPilot")
        if re.search(r"Ardu(Plane|Rover|Sub)", info) and not re.search(r"ArduCopter", info):
            fail("the pasted text is not ArduCopter. This build only makes Copter firmware")
        m = re.search(r"ArduCopter V(\d+\.\d+\.\d+(?:-[A-Za-z0-9]+)?)", info)
        if m:
            version = "Copter-" + m.group(1)
        # the board line is the name followed by three 8-digit hex groups (the chip ID)
        m = re.search(r"([A-Za-z0-9_-]+) [0-9A-Fa-f]{8} [0-9A-Fa-f]{8} [0-9A-Fa-f]{8}", info)
        if m:
            board = m.group(1)
    else:
        if looks_ardu and not looks_bf:
            fail("the pasted text looks like ArduPilot output, but STEP 1 says Betaflight")
        m = re.search(r"\b(\d{4}\.\d+\.\d+)\b", info) or re.search(r"\b(\d+\.\d+\.\d+)\b", info)
        if m:
            version = m.group(1)
        m = re.search(r"board_name:? *([A-Za-z0-9_]+)", info)
        if m:
            board = m.group(1)
    if not version and not board:
        fail("could not find a version or a board in the pasted text. "
             "Paste more of it, or clear the box and use STEPS 3 and 4")
    source = "the pasted FC output"

version_from_paste = bool(version)
if not version:
    version = typed_version
if not board:
    board = typed_board
if not board:
    fail("no board. Paste your FC output in STEP 2, or type the board in STEP 4")

if not version or version.lower() == "latest":
    if firmware == "ArduPilot":
        url, pat = "https://github.com/ArduPilot/ardupilot", r"^Copter-\d+\.\d+\.\d+$"
        refs = "refs/tags/Copter-*"
    else:
        url, pat = "https://github.com/betaflight/betaflight", r"^\d{4}\.\d+\.\d+$"
        refs = "refs/tags/*"
    out = subprocess.run(["git", "ls-remote", "--tags", "--refs", url, refs],
                         capture_output=True, text=True, check=True).stdout
    tags = [line.split("refs/tags/")[1] for line in out.splitlines() if "refs/tags/" in line]
    tags = [t for t in tags if re.match(pat, t)]
    if not tags:
        fail("could not work out the newest version")
    tags.sort(key=lambda t: [int(n) for n in re.findall(r"\d+", t)])
    version = tags[-1]
    how = "newest stable release"
else:
    how = "from the pasted text" if version_from_paste else "as typed"

if not re.fullmatch(r"[A-Za-z0-9._-]+", version) or not re.fullmatch(r"[A-Za-z0-9_-]+", board):
    fail(f"version '{version}' or board '{board}' has odd characters")

print(f"{firmware}: version {version} ({how}), board {board}, read from {source}")

for key, value in (("GITHUB_ENV", f"TAG={version}\nBOARD={board}\n"),
                   ("GITHUB_OUTPUT", f"tag={version}\nboard={board}\n")):
    path = os.environ.get(key)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(value)
