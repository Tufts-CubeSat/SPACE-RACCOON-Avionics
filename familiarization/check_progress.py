"""
Familiarization progress scoreboard.

Runs the FSW unit tests once and reports which exercises are complete.

Usage (from FSW-mainboard/, with your virtual environment active):
    python ../familiarization/check_progress.py
"""

import os
import subprocess
import sys

FSW_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "FSW-mainboard"))

# Exercise -> (title, test node-id prefixes that must all pass)
EXERCISES = [
    ("EX-01", "Scheduler", ["tests/test_scheduler.py"]),
    ("EX-02", "State machine", ["tests/test_state_machine.py"]),
    ("EX-03", "DataProcess telemetry logging", ["tests/test_data_process.py"]),
    ("EX-04", "FileProcess packet storage", ["tests/test_data_handler.py::test_file_process"]),
    ("EX-05", "EPS power flag & heaters", ["tests/test_eps.py"]),
    ("EX-06", "ADCS sun vector", ["tests/test_sun.py"]),
    ("EX-07", "ADCS B-dot detumbling", ["tests/test_acs.py::test_bdot"]),
    ("EX-08", "Command queue & processor", ["tests/test_fifo.py", "tests/test_cmd_processor.py"]),
    ("EX-09", "Command authentication", ["tests/test_command_auth.py"]),
    ("EX-10", "Emulator RTC", ["tests/test_emulator_rtc.py"]),
]


def run_tests():
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q", "-rA", "--no-header", "-p", "no:cacheprovider"]
    result = subprocess.run(cmd, cwd=FSW_ROOT, capture_output=True, text=True)
    outcomes = {}
    for line in result.stdout.splitlines():
        parts = line.split(" ", 2)
        if len(parts) >= 2 and parts[0] in ("PASSED", "FAILED", "ERROR"):
            outcomes[parts[1]] = parts[0]
    if not outcomes:
        print(result.stdout[-3000:])
        print(result.stderr[-3000:])
        sys.exit("Could not run the tests. Is your virtual environment active and are the submodules initialized?")
    return outcomes


def main():
    outcomes = run_tests()

    print()
    print(f"{'':6} {'Exercise':34} {'Tests':>9}   Status")
    print("-" * 64)
    done = 0
    for ex_id, title, prefixes in EXERCISES:
        mine = {node: status for node, status in outcomes.items() if any(node.startswith(p) for p in prefixes)}
        passed = sum(1 for s in mine.values() if s == "PASSED")
        complete = passed == len(mine)
        done += complete
        print(f"{ex_id:6} {title:34} {passed:>4}/{len(mine):<4}   {'DONE' if complete else '...'}")
    print("-" * 64)

    total_passed = sum(1 for s in outcomes.values() if s == "PASSED")
    print(f"Exercises complete: {done}/{len(EXERCISES)}      All tests: {total_passed}/{len(outcomes)} passing")
    if total_passed == len(outcomes):
        print("\nEvery test passes. Nice work! Now run the emulator and watch it reach NOMINAL.")


if __name__ == "__main__":
    main()
