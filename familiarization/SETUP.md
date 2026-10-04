# Setup Guide: Running the Argus Flight Software

This guide gets you from nothing to running the unit tests and the emulator. Plan on about 15 minutes.
Every step here was tested on Windows 11 (Python 3.13). CI uses Python 3.12 on Ubuntu.

---

## 1. What you need installed

| Tool | Version | Notes |
|---|---|---|
| **Git** | any recent | On Windows, install [Git for Windows](https://git-scm.com/download/win), which also gives you **Git Bash**. |
| **Python** | **3.12 or 3.13** | CI runs 3.12. 3.14 is untested. On Windows, tick *"Add python.exe to PATH"* during install. |
| An editor | — | VS Code works well. The repo ships a `.vscode/settings.json`. |

You do **not** need any of the following for these exercises:
- The physical mainboard, `mpy-cross`, or the `firmware/` folder (these are for flashing real hardware)
- The C++ GNC simulation / SIL setup (`./install.sh`, `sil/`). It is Linux-only and isn't included in this repo.
- The Confluence pages linked from the upstream README (they're internal to the CMU Argus team)

---

## 2. Get the code

The flight software uses one **git submodule** (`splat`, the telemetry/command packet codec).
Without it, every test fails with `ModuleNotFoundError: No module named 'apps.telemetry.splat.splat'`.

```bash
git clone --recurse-submodules -b familiarization/main https://github.com/Tufts-CubeSat/SPACE-RACCOON-Avionics.git
cd SPACE-RACCOON-Avionics
```

If you already cloned without `--recurse-submodules`, run:

```bash
git submodule update --init
```

### Create your own branch

**Never commit to `familiarization/main`.** Everyone works on a personal branch made from it:

```
familiarization/<firstname>-<lastname>
```

Use lowercase and hyphens, with no spaces or underscores. Examples: `familiarization/jane-doe`, `familiarization/sam-lee`.

```bash
git switch -c familiarization/jane-doe
git push -u origin familiarization/jane-doe
```

---

## 3. Create a virtual environment and install dependencies

Run everything from inside **`FSW-mainboard/`**, which is the root of the flight software project.

**Windows (PowerShell):**
```powershell
cd FSW-mainboard
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```
> If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

**Windows (Git Bash):**
```bash
cd FSW-mainboard
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd FSW-mainboard
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

`.venv/` is already git-ignored. Activate the venv each time you open a new terminal.

---

## 4. Run the unit tests

From `FSW-mainboard/` with the venv active:

```bash
python -m pytest tests/
```

**This is supposed to fail when you start.** On a fresh `familiarization/main` checkout you should see:

```
37 failed, 137 passed
```

(If your computer's clock is set to UTC, you'll see 36 failures. One of the Exercise 10 tests depends on the time zone, and the exercise explains why.)

Each exercise's bugs make its own set of tests fail. Your job is to get to **174 passed, 0 failed**.

Useful pytest options:

```bash
python -m pytest tests/test_eps.py                 # one file
python -m pytest tests/test_eps.py -k heaters      # tests whose name matches "heaters"
python -m pytest tests/ -x                         # stop at the first failure
python -m pytest tests/ -q --tb=short              # shorter output
```

### Progress scoreboard

```bash
python ../familiarization/check_progress.py
```

This prints a pass/fail table, one line per exercise.

---

## 5. Run the emulator

The **emulator** runs the *real* flight software on your laptop, with every piece of hardware (radio, IMU,
sun sensors, battery, GPS, RTC, ...) replaced by a Python fake in `emulator/`. It's the fastest way to watch
the whole system run.

**macOS / Linux / Git Bash (if `python3` works in that shell):**
```bash
./run.sh emulate
```

**Windows (any shell):** `run.sh` calls `python3`, which on Windows usually opens the Microsoft Store
instead of your venv. Run the two steps by hand instead:

```bash
python build_tools/build-emulator.py
cd build
python main.py
```

Press **Ctrl+C** to stop.

### Things to know about the emulator

- **It's very chatty.** Save the output to a file and search it:
  ```bash
  python main.py > emu.log 2>&1        # let it run ~20 s, then Ctrl+C
  grep "Switched to state" emu.log     # or: Select-String "Switched to state" emu.log  (PowerShell)
  ```
- **Time is accelerated.** The emulator replaces Python's `time` module (`emulator/accel_time.py`), so
  simulated time advances as fast as the CPU allows. On a working build, about an hour of satellite time
  passes in 30 real seconds.
- **The emulated SD card** is `build/sd/`. Delete it to simulate a satellite booting for the first time.
  Keep it to simulate a *reboot* that has data from the previous run.
- **The build regenerates `flight/core/satellite_config.py`** from `flight/configuration/ground.yaml`. The
  committed copy is slightly out of sync with the YAML, so `git status` will show it as modified. **Don't commit
  that change.** Undo it with:
  ```bash
  git checkout -- flight/core/satellite_config.py      # run from FSW-mainboard/
  ```
- `build/` and `sd/` are git-ignored.

**What you should see right now:** the satellite never leaves `STARTUP`, and the log repeats
`No transition from 0 to 1`. Once you've fixed the core exercises, it should go `STARTUP → DETUMBLING → NOMINAL`.

---

## 6. Repository map

```
SPACE-RACCOON-Avionics/
├── familiarization/          ← this guide, the exercises, the progress script
└── FSW-mainboard/            ← the flight software project (run everything from here)
    ├── flight/               ← code that runs ON the satellite (CircuitPython)
    │   ├── main.py           ←   entry point: boot hardware, start the state machine
    │   ├── core/             ←   framework: scheduler, state machine, data handler, logging, time
    │   ├── apps/             ←   mission logic as plain functions/classes (ADCS math, EPS rules, command processing, ...)
    │   ├── tasks/            ←   one scheduled Task per subsystem, which calls into apps/
    │   ├── hal/              ←   hardware abstraction layer + chip drivers for the real board
    │   └── configuration/    ←   ground.yaml / flight.yaml → turned into core/satellite_config.py at build time
    ├── emulator/             ← drop-in replacement for flight/hal/ with simulated hardware
    ├── tests/                ← pytest unit tests (tests/cp_mock.py makes flight code importable on a PC)
    ├── build_tools/          ← build scripts (emulator build, .mpy cross-compile, copy to board)
    ├── sil/                  ← software-in-the-loop with the C++ simulator (not used here)
    ├── scripts/              ← one-off hardware test scripts to run on the board
    └── firmware/             ← CircuitPython firmware images for each mainboard revision
```

---

## 7. Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError: No module named 'apps.telemetry.splat.splat'` | The submodule is missing. Run `git submodule update --init` from the repo root. |
| `ModuleNotFoundError: No module named 'tests'` or `'flight'` | Run pytest **from `FSW-mainboard/`** and use `python -m pytest`, not bare `pytest`. |
| `Python was not found; run without arguments to install from the Microsoft Store` | You ran `run.sh` on Windows. Use the manual emulator commands in section 5. |
| `No module named pytest` | Your venv isn't active, or you skipped `pip install -r requirements.txt`. |
| `git status` shows `flight/core/satellite_config.py` modified | The emulator build regenerated it. `git checkout -- flight/core/satellite_config.py` |
| The emulator crashes immediately on an old SD card | Delete `build/sd/` and run again. |

---

## A note on where this code came from

`FSW-mainboard/` is the Argus flight software from Carnegie Mellon's Argus CubeSat team
(`cmu-argus-2/FSW-mainboard`, commit `b428c54`). On the `main-FSW-Argus` branch it was committed as a broken
submodule pointer, so a fresh clone of that branch gets an **empty** folder. On `familiarization/main` the files
are committed directly, and `splat` is registered as a proper submodule, so the code is actually there.
