# SPACE RACCOON Avionics: TODO

Working task list for flight software. Put your name next to a task when you take it, and check it off when it's done.

The flight software (inherited from CMU Argus) is on the `main-FSW-Argus` branch. Paths below are relative to
`FSW-mainboard/` on that branch. The requirements spec is *SR-FSW-PAY-001 (Image Processing Payload SRS)*.

---

## Constraints to keep in mind

- **The mainboard runs CircuitPython, not regular Python.** Code is compiled with `mpy-cross` and uses `ulab` in
  place of numpy. No scipy, no full numpy, and limited RAM. Anything we add to the mainboard, including ADCS code,
  has to work within that.
- **The payload has no emulator yet.** `emulator/drivers/payload.py` is a stub: `read()` returns nothing and
  `write()` discards data. The payload state machine can't be tested end to end until this is replaced.
- **The GNC simulation submodule isn't set up.** `simulation/` is empty, so the SIL runs in `sil/` won't work yet.

---

## 1. Onboarding

- [ ] Everyone: finish environment setup (`familiarization/SETUP.md` on the familiarization branches)
- [ ] Everyone: work through the familiarization exercises (`familiarization/EXERCISES.md`) on your own
      `familiarization/<firstname>-<lastname>` branch
- [ ] Everyone: read `docs/architecture.md` and the payload framework files listed in SRS §3

## 2. Payload hardware and mission (needs the payload team)

- [ ] Pick the compute module (Jetson Orin Nano / Raspberry Pi CM4 + accelerator / other). Owner: ____
- [ ] Pick the camera: model, resolution, interface (CSI / USB). Owner: ____
- [ ] Get power numbers: peak W, average W, boot time. Owner: ____
- [ ] Settle the mission use case (SRS §4.2): what the model detects and what results come to the ground.
      Owner: ____
- [ ] Choose the UART baud rate (the Argus emulator uses 460800). Owner: ____

## 3. Interface Control Document (ICD)

The ICD unblocks both the mainboard work and the payload-side software.

- [ ] Draft ICD v0: the message set between mainboard and payload (commands, acks, telemetry, results, file
      transfer). Reuse the Argus framing (fixed 609-byte frames, splat codec) unless there's a reason not to.
      Owner: ____
- [ ] Define the results file format and thumbnail format/size. Owner: ____
- [ ] Review the ICD with the payload team. Owner: ____

## 4. Mainboard payload software

- [ ] Write an emulated payload in `emulator/drivers/payload.py` that follows the ICD: boot → ack → "capture" →
      return a dummy results file. Owner: ____
- [ ] Unit tests for the payload controller against the emulated payload. Owner: ____
- [ ] Go through the open TODOs in `flight/apps/payload/controller.py` (about 10, including argument checks and
      timeouts) and decide which to fix. Owner: ____
- [ ] Revisit the Argus timeouts (boot 120 s, ack 20 s, download 50 s, shutdown 15 s) once hardware is chosen.
      Owner: ____
- [ ] Add the `IMAGING_EXPERIMENT` ground command and remove or adapt the Argus-specific experiment parameters.
      Owner: ____
- [ ] Update the EPS power threshold for the payload rail (currently 16000 mW for the Jetson). Owner: ____

## 5. Payload-side software (runs on the compute module)

- [ ] UART protocol implementation that matches the ICD. Owner: ____
- [ ] Camera capture. Owner: ____
- [ ] Inference pipeline. Owner: ____
- [ ] Results and thumbnail packaging. Owner: ____
- [ ] Clean shutdown on command from the mainboard. Owner: ____

## 6. ADCS / Generalized_ADCS integration

- [ ] Audit Generalized_ADCS: language, dependencies, size, interfaces. Can it run under CircuitPython/`ulab`?
      Write up a one-page summary. Owner: ____
- [ ] Confirm RACCOON's ADCS hardware: magnetorquers only (like Argus's 6 coils) or reaction wheels too? Which
      sensors? Owner: ____
- [ ] Compare against the current ADCS (`flight/tasks/adcs.py`, `flight/apps/adcs/`) and recommend one
      approach. Owner: ____
  - (a) Port the algorithms into `flight/apps/adcs/` in `ulab`-compatible form
  - (b) Use Generalized_ADCS only on the ground and in simulation (reference model / SIL plant)
  - (c) Run it on a separate processor
- [ ] Update `flight/apps/adcs/consts.py` (inertia matrix, gains, modes) for RACCOON. Owner: ____
- [ ] Get SIL working: initialize the GNC simulation submodule or replace it with Generalized_ADCS's sim.
      Owner: ____
- [ ] Decide whether the ADCS has to point the camera during experiments. If yes, document the dependency in
      the SRS. Owner: ____

## 7. Requirements spec (SR-FSW-PAY-001)

- [ ] §2 Scope: fill in what's in and out of scope. Owner: ____
- [ ] §4.1 Payload hardware table (from section 2 above). Owner: ____
- [ ] §4.2 Mission use case. Owner: ____
- [ ] §5 Definitions. Owner: ____
- [ ] §6 Functional requirements, written as numbered "shall" statements. Owner: ____
- [ ] §7 Fault management table. Starting list: boot timeout, no ack, UART link drop, overcurrent on the payload
      rail, low power mid-experiment, corrupt or incomplete file transfer. Owner: ____
- [ ] §8 Interfaces (point to the ICD). Owner: ____
- [ ] §9 Resource budgets: power, downlink, SD, RAM, CPU. Owner: ____
- [ ] §10 Planned code changes. Owner: ____
- [ ] §11 Verification plan: unit, emulator, hardware-in-the-loop. Owner: ____
- [ ] §13 Milestone dates for M1–M5. Owner: ____
- [ ] Find reviewers. Owner: ____

---

## Open questions

- Should the payload be allowed to run in states other than NOMINAL and EXPERIMENT?
- Does an experiment need a specific attitude (for example, nadir pointing)?
- How many experiments per orbit can the power budget support?
- How many passes can we spend downlinking one experiment's results and thumbnails? The SRS currently targets 2.
