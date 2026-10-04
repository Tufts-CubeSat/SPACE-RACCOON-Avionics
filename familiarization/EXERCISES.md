# Argus Flight Software: Familiarization Exercises

Someone has been "improving" the flight software, and now the satellite is broken in 14 different ways.
Each exercise below is a bug report, the kind you'd get from a teammate running the emulator or reviewing
telemetry. Track down the bugs, fix them, and **make every unit test pass**.

The bugs are small, usually one or two lines each. Finding them is the hard part, and finding them
means understanding how that part of the system works. That's what the exercises are for.

---

## Rules

1. **Don't edit the tests.** The tests are the specification. If a test and the code disagree, the code is wrong.
   (Every exercise's tests pass on a correct implementation.)
2. **Work on your own branch** (`familiarization/<firstname>-<lastname>`; see [SETUP.md](SETUP.md)).
3. **One commit per exercise**, with the message `EX-NN: <what was wrong>`, for example `EX-05: fix SOC boundary`.
   This makes review easy.
4. **Answer the "Understand it" questions** in a file `familiarization/answers/<firstname>-<lastname>.md` on your branch.
   Short answers are fine. They're for discussion, not grading.
5. **Honor system:** don't diff against the upstream `cmu-argus-2/FSW-mainboard` repository or against other people's
   branches. You'll learn far less.
6. Stuck for more than ~20 minutes? Ask. Hints are available.

### Recommended workflow for each exercise

1. Run its tests and **read the failure output carefully**: the assertion message, the expected value, and the actual value.
2. Read the test itself. It tells you exactly what the code is supposed to do.
3. Read the code under test *and the code that calls it* (use your editor's "Find all references").
4. Form a hypothesis, fix it, rerun the tests.
5. Answer the questions, then commit.

### Scoreboard

```bash
cd FSW-mainboard
python ../familiarization/check_progress.py
```

### Difficulty key

★☆☆ warm-up · ★★☆ needs some reading · ★★★ needs real understanding / design

---

## Exercise 0: Orientation (no code changes)

Get set up using [SETUP.md](SETUP.md), then:

1. Run the test suite and confirm you see **37 failed, 137 passed** (36 if your clock is in UTC).
2. Run the emulator for ~20 seconds and save the log. Find the line where the satellite enters its first state.
   What happens after that?
3. Open `flight/main.py` and follow the code until you reach the first line that runs a *task*. Write down the chain of
   function calls.

**Understand it:**
- **0.1** What are the three layers of the architecture (`docs/architecture.md`), and which folders are in each?
- **0.2** List every task in `flight/core/task_configuration.py` with its frequency. Which task runs most often?
- **0.3** Flight code does `from hal.configuration import SATELLITE`. How does `hal` end up meaning the **emulator** when
  you run the emulator, and when you run the tests? (Look at `build_tools/build-emulator.py` and `tests/cp_mock.py`.)
- **0.4** The flight code imports `micropython` and `ulab`, which don't exist on your laptop. Where do they come from
  during the tests?
- **0.5** Why does every task class inherit from `TemplateTask`, and what happens if a task's `main_task()` raises an
  exception?

---

# Part 1: Core Framework (`flight/core/`)

## EX-01 · Scheduler: "The watchdog is being starved" ★★☆ · 2 bugs

> **Bug report:** In the emulator, simulated time has slowed to a crawl. Twenty real seconds now covers barely a
> minute of satellite time, when it used to cover most of an hour, and the log is flooded with task output. Separately, a
> hardware tester says the **watchdog task (priority 1) sometimes runs after the HAL monitor (priority 2)**, even though
> the comment in `task_configuration.py` says the watchdog must win.

**Where to look:** `flight/core/scheduler/scheduler.py`, `flight/core/task_configuration.py`

**Tests:** `python -m pytest tests/test_scheduler.py`

**Understand it:**
- **1.1** The scheduler runs many tasks without threads. What is a coroutine, and what does `_yield_once()` do?
  What does a task have to do to give up the processor?
- **1.2** In `TASK_CONFIG`, is priority 1 more or less important than priority 3? Which tasks are most important?
- **1.3** What unit of time does the scheduler use internally? Why might integer nanoseconds be chosen?
- **1.4** What's the difference between `schedule()` and `schedule_later()`? Which tasks use `ScheduleLater`, and why
  might they want to wait one period before their first run?
- **1.5** What happens if a task takes longer to run than its period? (Read the comment in `_run_at_fixed_rate`.)

---

## EX-02 · State machine: "Stuck in STARTUP" ★★☆ · 1 bug

> **Bug report:** The satellite never leaves `STARTUP`. The emulator log shows
> `ValueError: No transition from 0 to 1` over and over. STARTUP → DETUMBLING is definitely a legal transition.

**Where to look:** `flight/core/state_machine.py`, `flight/core/states.py`. To see *who* asks for state changes, look at
`flight/tasks/command.py` (`startup()` and `state_machine_execution()`).

**Tests:** `python -m pytest tests/test_state_machine.py`

**Understand it:**
- **2.1** Draw the state diagram: five states, with arrows for every legal transition.
- **2.2** Which task decides when to change state? What conditions cause DETUMBLING → NOMINAL, and NOMINAL → LOW_POWER?
- **2.3** What does the state machine physically turn off when it enters LOW_POWER? What does it turn off when it
  *leaves* NOMINAL?
- **2.4** What is a "forced state" (`start_forced_state`)? What ground command triggers it, and what stops the satellite
  from immediately switching back out?
- **2.5** `StateManager` is a *singleton*. What does that mean here, and how is it enforced?

---

## EX-03 · Data handler: "Telemetry goes missing" ★★☆ · 2 bugs

> **Bug report #1:** EPS telemetry is logged with `write_interval=5`. After a fresh boot, the first EPS record doesn't
> appear on the SD card until the 5th sample. It should be written on the 1st sample, then the 6th, the 11th, and so on.
>
> **Bug report #2:** Every reboot, the command task logs
> `SD card is available, but no CDH data was found; starting boot count at 1`, so **the boot counter never goes up**,
> even though the `cdh` folder on the SD card clearly has data in it. The log also contains
> `Error reading file sd/cdh/cdh_<time>.bin: [Errno 22] Invalid argument`.

**Where to look:** the `DataProcess` class in `flight/core/data_handler.py`. Look at how `flight/tasks/command.py` restores
the boot count.

**Tests:** `python -m pytest tests/test_data_process.py`

**Understand it:**
- **3.1** What is a *data process*? Describe what gets created on the SD card when one is registered: folder, file
  names, and the hidden `.json` file.
- **3.2** For `data_format="fff"`, how many bytes is one record? Why does the code put `<` in front of the format?
- **3.3** What does `write_interval` trade off? Why would EPS use 5 but the command log use 1?
- **3.4** How does a data process get its latest value back after a reboot? What else besides the boot count depends on this?
- **3.5** What do the two arguments of `file.seek(offset, whence)` mean? What are the three `whence` values?

---

## EX-04 · Data handler: "Downlinked files are garbage" ★★☆ · 1 bug

> **Bug report:** Files stored through a `FileProcess` can't be read back. Every `get_packet()` call returns `None`, and
> the log says `Invalid packet length 17480 at index 0`, even for files we know contain valid data.
> *(Hint: write 17480 in hexadecimal, then look those bytes up in an ASCII table.)*

**Where to look:** the `FileProcess` class in `flight/core/data_handler.py`

**Tests:** `python -m pytest tests/test_data_handler.py`

**Understand it:**
- **4.1** Draw the byte layout of a `FileProcess` `.bin` file: file header, then packets, each with a header, data,
  and padding. Give the sizes.
- **4.2** Every packet takes exactly 242 bytes on disk, even if it only holds 3 bytes of data. What does that buy us, and
  what does it cost?
- **4.3** `log()` copies data into a 512-byte RAM buffer before writing to the SD card. Why not write each packet directly?
- **4.4** What does `get_packet()` do differently for a `.jpg` file that has no magic number?

---

# Part 2: Applications (`flight/apps/`)

## EX-05 · EPS: "Edge-of-threshold power decisions" ★☆☆ · 2 bugs

> **Bug report #1:** With the battery at **exactly 30 %** state of charge, a satellite in NOMINAL doesn't drop into low power.
> The power rules say ≤ 30 % means LOW_POWER.
>
> **Bug report #2:** With a battery heater on and the battery at **exactly 5.00 °C**, the heater stays on. The rules
> say it should switch off at ≥ 5.00 °C.

**Where to look:** `flight/apps/eps/eps.py`, and `flight/tasks/eps.py` to see how it's used

**Tests:** `python -m pytest tests/test_eps.py`

**Understand it:**
- **5.1** Low-power mode is entered at ≤ 30 % but only exited at ≥ 40 %. Why not a single threshold? What's this pattern called?
- **5.2** What unit are the temperatures in? Convert `BATTERY_HEAT_ENABLE` and `BATTERY_HEAT_DISABLE` to °C.
- **5.3** What does `GET_POWER_STATUS` compute, and what is `window` in practice? (Check what `tasks/eps.py` passes in.)
- **5.4** Trace how the EPS power flag gets from `tasks/eps.py` to the state-machine decision in `tasks/command.py`.
  (Hint: the two tasks never call each other directly.)

---

## EX-06 · ADCS: "The sun is in the wrong place" ★★☆ · 1 bug

> **Bug report:** The sun-vector estimate matches MATLAB in some cases, but when the sun lights the **Z+ pyramid**
> sensors, the vector is noticeably wrong.

**Where to look:** `flight/apps/adcs/sun.py`

**Tests:** `python -m pytest tests/test_sun.py`

**Understand it:**
- **6.1** How many light sensors does Argus have, and where are they? Sketch the Z+ pyramid and label each sensor.
- **6.2** What are `_ERROR_LUX` and `_THRESHOLD_ILLUMINATION_LUX` used for?
- **6.3** Why can the function return `SUN_NOT_ENOUGH_READINGS` even when several sensors work?
- **6.4** (Stretch) The comments mention `N^T W N` and `N^T W y`. What least-squares problem is being solved? What are
  `N`, `W`, and `y`?

---

## EX-07 · ADCS: "Detumbling makes it spin faster" ★★☆ · 1 bug

> **Bug report:** In simulation, the satellite's angular rate *increases* while in DETUMBLING with the B-dot controller,
> until it reaches the "very fast tumbling" limit.

**Where to look:** `flight/apps/adcs/acs.py`; `flight/tasks/adcs.py` to see how it's called; `flight/apps/adcs/consts.py`

**Tests:** `python -m pytest tests/test_acs.py`

**Understand it:**
- **7.1** Explain in plain words how a B-dot controller removes spin using only magnetorquers and a magnetometer.
- **7.2** `_DERIVATIVE_WEIGHTS = [-5, -3, -1, 1, 3, 5] / 35`. Show that these weights recover the slope of a straight line
  sampled at 6 evenly spaced points.
- **7.3** What does `u / sqrt(|u|² + 1)` do to the size of the command? Why not just clip it?
- **7.4** Which controller (B-dot, B-cross, sun pointing) runs when? Where is the controller mode stored, and why does it
  survive a reboot?

---

## EX-08 · Commands: "Commands out of order, and false failures" ★★☆ · 2 bugs

> **Bug report #1:** During a pass the ground station uplinked three commands, A, B, C. The satellite ran them
> **C, B, A**.
>
> **Bug report #2:** The `EXPERIMENT` command clearly worked (the payload log shows the experiment was scheduled), but the
> ACK sent to the ground says `COMMAND_EXECUTION_FAILED` (0x03).

**Where to look:** `flight/apps/command/fifo.py`, `flight/apps/command/processor.py`, `flight/apps/command/commands.py`

**Tests:** `python -m pytest tests/test_fifo.py tests/test_cmd_processor.py`

**Understand it:**
- **8.1** Follow a command from the moment the radio receives a packet to the moment an ACK is queued for transmission.
  Name each module and class it passes through.
- **8.2** How does `@register_command()` work? What ends up in `COMMAND_REGISTRY`, and how does the processor use it?
- **8.3** `CommandQueue` and `TransmitQueue` use class-level state and `@classmethod`s instead of instances. Why does
  that work as a way for tasks to talk to each other?
- **8.4** What happens to a command that arrives while the command queue is full?

---

## EX-09 · Comms: "Every authenticated command is rejected" ★★☆ · 1 bug

> **Bug report:** Since the last update, every authenticated uplink fails with
> `[COMMS ERROR] Command authentication failed: mac_mismatch`. The ground station software hasn't changed, and the
> key is correct.

**Where to look:** `flight/apps/comms/auth.py`; `flight/apps/comms/comms.py` to see how it's called

**Tests:** `python -m pytest tests/test_command_auth.py`

**Understand it:**
- **9.1** Draw the byte layout of an authenticated command packet.
- **9.2** What is an HMAC, and why is it better here than just appending a SHA-256 of the message?
- **9.3** Why does the code use `constant_time_compare` instead of `==`?
- **9.4** What is the nonce supposed to protect against? Does the flight software actually check that a nonce hasn't been
  used before? What could an attacker with a radio do as a result?
- **9.5** Where does the authentication key come from? Is that a good place for it?

---

# Part 3: Hardware Abstraction & the Emulator

## EX-10 · Emulator: "GPS task crashes on every fix" ★★★ · 1 bug (a real one)

> **Bug report:** Every time the emulated GPS gets a fix, the GPS task crashes with:
> ```
> File ".../core/time_processor.py", in set_time
>     SATELLITE.RTC.set_datetime(time.localtime(unix_timestamp))
> File ".../hal/drivers/rtc.py", in set_datetime
>     self.datetime = date_input
> AttributeError: property 'datetime' of 'RTC' object has no setter
> ```
> Also, on some laptops the emulated satellite clock is off by several hours.

This one was **not** planted. It's a real bug in the upstream emulator. Fixing it needs some design: once the
RTC has been set, reading it must return the time it was set to, and that time must keep moving forward.

**Where to look:** `emulator/drivers/rtc.py`, `flight/core/time_processor.py`, `flight/tasks/gps.py`, `emulator/accel_time.py`

**Tests:** `python -m pytest tests/test_emulator_rtc.py`

**Understand it:**
- **10.1** What is the Time Processing Module (TPM) for? What are `time_reference` and `time_offset`, and what does TPM
  do if the RTC dies?
- **10.2** Explain `time.gmtime()`, `time.localtime()`, and `time.mktime()`. Why did `test_rtc_reads_current_time` fail
  on your laptop, and why would it pass on a CI server?
- **10.3** Compare `emulator/drivers/rtc.py` with the real driver interface the flight code expects
  (`flight/hal/drivers/ds3231.py` or `pcf8523.py`). What should an emulator driver guarantee?
- **10.4** If this bug had been in the *real* RTC driver, what would the consequences be in orbit?

---

## Bonus challenges (no tests; for anyone who finishes early)

- **B1.** The emulated satellite can't enter or leave LOW_POWER: the command task throws an `AttributeError` each time it
  tries. Find out why (compare `emulator/emulator.py` and `emulator/cubesat.py` with `flight/hal/cubesat.py`) and fix it. Then find a way to make the emulated battery drain so you can watch it happen.
- **B2.** Write unit tests for the digipeater (`flight/apps/digipeater/aprs.py` + `flight/tasks/digipeater.py`). Does
  `is_valid_lora_aprs_packet` really check the LoRa APRS header its docstring describes? What happens when
  `add_asterisk_packet` runs on CPython with a `bytes` packet?
- **B3.** Read `StateManager.start_forced_state`. Something about its logging is wrong. What, and how would you fix it?
- **B4.** Design replay protection for authenticated commands (see question 9.4). What has to survive a reboot?

---

## When you're done

- `python -m pytest tests/` → **174 passed**
- The emulator goes **STARTUP → DETUMBLING → NOMINAL**, and the GPS task no longer throws
- Your answers file is committed, and your branch is pushed
- Open a **draft** pull request from your branch into `familiarization/main` titled
  `[Familiarization] <Your Name>` so it can be reviewed. **Never merge it.** `familiarization/main` has to stay
  broken for the next person.
