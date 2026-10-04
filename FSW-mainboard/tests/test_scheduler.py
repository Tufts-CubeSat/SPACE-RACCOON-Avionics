# isort: skip_file
"""
Unit tests for the cooperative scheduler (flight/core/scheduler/scheduler.py).

Added for the familiarization exercises (replaces the disabled tests/test_loop.py).

The scheduler reads time through the module-level `_monotonic_ns` function and idles with
`time.sleep()`. Both are replaced here by a fake clock so the tests are deterministic and fast:
sleeping simply advances the fake clock instead of blocking.
"""

import pytest

import tests.cp_mock  # noqa: F401
import flight.core.scheduler.scheduler as S

_NS_PER_S = 1_000_000_000


class FakeClock:
    def __init__(self):
        self.now_ns = 0

    def monotonic_ns(self):
        return self.now_ns

    def sleep(self, seconds):
        self.now_ns += int(seconds * _NS_PER_S)


@pytest.fixture
def clock(monkeypatch):
    fake = FakeClock()
    monkeypatch.setattr(S, "_monotonic_ns", fake.monotonic_ns)
    monkeypatch.setattr(S.time, "sleep", fake.sleep)
    return fake


def run_for(scheduler, clock, seconds, max_steps=100_000):
    """Step the scheduler until `seconds` of fake time have elapsed."""
    end_ns = clock.now_ns + int(seconds * _NS_PER_S)
    steps = 0
    while clock.now_ns < end_ns and steps < max_steps:
        scheduler._step()
        steps += 1
    return steps


def test_ready_tasks_run_in_priority_order(clock):
    """Lower priority number == more important == runs first."""
    scheduler = S.Scheduler()
    order = []

    async def job(name):
        order.append(name)

    scheduler.add_task(job("low"), 3)
    scheduler.add_task(job("high"), 1)
    scheduler.add_task(job("medium"), 2)

    scheduler._step()

    assert order == ["high", "medium", "low"]


@pytest.mark.parametrize("hz", [0.5, 1, 2, 5])
def test_scheduled_task_runs_at_requested_rate(clock, hz):
    scheduler = S.Scheduler()
    runs = []

    async def job():
        runs.append(clock.now_ns)

    scheduler.schedule(hz, job, 1)
    run_for(scheduler, clock, seconds=10)

    # A task scheduled at `hz` runs immediately, then once every 1/hz seconds.
    expected = 10 * hz
    assert expected <= len(runs) <= expected + 1

    # Consecutive runs should be exactly one period apart.
    period_ns = _NS_PER_S / hz
    for earlier, later in zip(runs, runs[1:]):
        assert later - earlier == pytest.approx(period_ns, abs=1)


def test_change_rate(clock):
    scheduler = S.Scheduler()
    runs = []

    async def job():
        runs.append(clock.now_ns)

    task = scheduler.schedule(1, job, 1)
    run_for(scheduler, clock, seconds=5)
    runs_at_1hz = len(runs)

    task.change_rate(4)
    run_for(scheduler, clock, seconds=5)

    assert 5 <= runs_at_1hz <= 6
    assert 19 <= len(runs) - runs_at_1hz <= 21


def test_schedule_later_skips_first_interval(clock):
    scheduler = S.Scheduler()
    runs = []

    async def job():
        runs.append(clock.now_ns)

    scheduler.schedule_later(1, job, 1)

    scheduler._step()
    assert runs == [], "schedule_later must not run the task immediately"

    run_for(scheduler, clock, seconds=3)
    assert 2 <= len(runs) <= 3


def test_stopped_task_does_not_run(clock):
    scheduler = S.Scheduler()
    runs = []

    async def job():
        runs.append(clock.now_ns)

    task = scheduler.schedule(1, job, 1)
    scheduler._step()
    assert len(runs) == 1

    task.stop()
    run_for(scheduler, clock, seconds=5)
    assert len(runs) == 1

    task.start()
    run_for(scheduler, clock, seconds=2)
    assert len(runs) > 1


def test_sleep_suspends_task(clock):
    scheduler = S.Scheduler()
    events = []

    async def job():
        events.append(("start", clock.now_ns))
        await scheduler.sleep(0.5)
        events.append(("end", clock.now_ns))

    scheduler.add_task(job(), 1)
    run_for(scheduler, clock, seconds=1)

    assert [name for name, _ in events] == ["start", "end"]
    assert events[1][1] - events[0][1] >= 0.5 * _NS_PER_S
