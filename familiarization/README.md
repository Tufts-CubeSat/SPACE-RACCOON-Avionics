# Flight Software Familiarization

This branch (`familiarization/main`) is a training copy of the Argus flight software (`FSW-mainboard/`) with
**14 deliberately planted bugs** spread across 10 exercises. Fixing them takes you through every layer of
the system: the scheduler, state machine, data storage, power, attitude control, commanding, authentication, and the
hardware emulator. You're done when **all 174 unit tests pass**.

| Document | What's in it |
|---|---|
| [SETUP.md](SETUP.md) | Installing, running the tests, running the emulator, repo map, troubleshooting |
| [EXERCISES.md](EXERCISES.md) | The problem set: bug reports, where to look, which tests, and questions to answer |
| [check_progress.py](check_progress.py) | Scoreboard: `python ../familiarization/check_progress.py` (run from `FSW-mainboard/`) |

## Branch workflow

```
main
└── main-FSW-Argus              the imported flight software
    └── familiarization/main    ← this branch: bugs planted, docs added. Never commit here.
        ├── familiarization/jane-doe
        ├── familiarization/sam-lee
        └── ...                 ← one branch per person
```

**Naming standard:** `familiarization/<firstname>-<lastname>`, all lowercase, words separated by hyphens
(for example `familiarization/jane-doe`). If two people share a name, add a middle initial: `familiarization/jane-q-doe`.

```bash
git switch familiarization/main
git pull
git switch -c familiarization/<firstname>-<lastname>
git push -u origin familiarization/<firstname>-<lastname>
```

Commit one exercise at a time (`EX-05: fix SOC boundary`) and push often. When you finish, open a **draft PR into
`familiarization/main` and never merge it**. The PR is only there for review and discussion.

## A 2-minute tour of how the code fits together

```
flight/main.py
  └─ SATELLITE.boot_sequence()               hal/        bring up hardware (or the emulator's fakes)
  └─ state_manager.start()                   core/state_machine.py
       ├─ creates one Task per entry in      core/task_configuration.py
       ├─ schedules each Task's main_task()  core/scheduler/   (cooperative, priority-based, fixed-rate)
       └─ runs the scheduler forever

Each tick, the tasks (tasks/*.py) do their job by calling:
  apps/*        pure mission logic, such as EPS thresholds, ADCS control laws, the command processor, and auth
  core/*        shared services: DataHandler (SD card + inter-task data), TimeProcessor, logger
  hal/          SATELLITE: the single object every task uses to reach hardware

Tasks don't call each other. They communicate through:
  DataHandler   e.g. the EPS task logs "eps" data, and the command task reads DH.get_latest_data("eps")
  class queues  e.g. comms → CommandQueue → command task → TransmitQueue → comms
```

The command task (`tasks/command.py`) is the satellite's "brain". It owns the state machine transitions
STARTUP → DETUMBLING → NOMINAL ⇄ LOW_POWER / EXPERIMENT.

On the real board this all runs on **CircuitPython** (a microcontroller Python). On your laptop, `hal` is swapped for the
**emulator** (`emulator/`), and `micropython` / `ulab` are swapped for small mocks (`emulator/cp/`). That's why the same
code runs in both places.
