# isort: skip_file
"""
Unit tests for the satellite state machine (flight/core/state_machine.py + flight/core/states.py).

Added for the familiarization exercises.

StateManager.start() schedules every flight task and then runs the scheduler forever, so these tests
put the StateManager directly into a given state instead of calling start().
"""

import pytest

import tests.cp_mock  # noqa: F401
from flight.core.state_machine import StateManager
from flight.core.states import STATES, STR_STATES
from hal.configuration import SATELLITE

ALL_STATES = [STATES.STARTUP, STATES.DETUMBLING, STATES.NOMINAL, STATES.LOW_POWER, STATES.EXPERIMENT]

# The mission's allowed transitions (source state -> allowed destination states).
# This is the specification; it is intentionally written out here rather than read from STATES.TRANSITIONS.
ALLOWED = {
    STATES.STARTUP: {STATES.DETUMBLING},
    STATES.DETUMBLING: {STATES.NOMINAL, STATES.LOW_POWER},
    STATES.NOMINAL: {STATES.LOW_POWER, STATES.DETUMBLING, STATES.EXPERIMENT},
    STATES.LOW_POWER: {STATES.NOMINAL, STATES.LOW_POWER},
    STATES.EXPERIMENT: {STATES.LOW_POWER, STATES.DETUMBLING, STATES.NOMINAL},
}


@pytest.fixture(autouse=True)
def fake_power_interfaces(monkeypatch):
    # Entering/leaving LOW_POWER touches payload and GPS power. The emulated satellite does not implement
    # every one of these interfaces, so stub them out for the test.
    monkeypatch.setattr(type(SATELLITE), "PAYLOADPOWER_AVAILABLE", False, raising=False)
    monkeypatch.setattr(SATELLITE, "DEVICE_STATUS", lambda name: {"dead": False}, raising=False)
    monkeypatch.setattr(SATELLITE, "turn_off_device", lambda name: None)
    monkeypatch.setattr(SATELLITE, "turn_on_device", lambda name: None)


def manager_in_state(state):
    """Return the (singleton) StateManager, already initialized and sitting in `state`."""
    sm = StateManager()  # __init__ resets the singleton's fields
    sm._StateManager__states = list(ALL_STATES)
    sm._StateManager__initialized = True
    sm._StateManager__current_state = state
    return sm


@pytest.mark.parametrize("source", ALL_STATES, ids=lambda s: STR_STATES[s])
@pytest.mark.parametrize("destination", ALL_STATES, ids=lambda s: STR_STATES[s])
def test_transition(source, destination):
    sm = manager_in_state(source)

    if destination in ALLOWED[source]:
        sm.switch_to(destination)
        assert sm.current_state == destination
        assert sm.previous_state == source
    else:
        with pytest.raises(ValueError):
            sm.switch_to(destination)
        assert sm.current_state == source, "an illegal transition must not change the state"


def test_unknown_state_is_rejected():
    sm = manager_in_state(STATES.NOMINAL)
    with pytest.raises(ValueError):
        sm.switch_to(0x42)
    assert sm.current_state == STATES.NOMINAL


def test_forced_state_blocks_switching():
    sm = manager_in_state(STATES.NOMINAL)

    sm.start_forced_state(STATES.EXPERIMENT, time_in_state=2)
    assert sm.current_state == STATES.EXPERIMENT

    # While forced, requests to switch are ignored
    sm.switch_to(STATES.NOMINAL)
    assert sm.current_state == STATES.EXPERIMENT

    # update_time_in_state() is called once per command-task cycle (tasks/command.py)
    for _ in range(3):
        sm.update_time_in_state()

    sm.switch_to(STATES.NOMINAL)
    assert sm.current_state == STATES.NOMINAL
