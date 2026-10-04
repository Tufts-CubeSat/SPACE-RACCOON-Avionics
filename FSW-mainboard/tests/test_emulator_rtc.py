# isort: skip_file
"""
Unit tests for the emulated real-time clock (emulator/drivers/rtc.py) and how the Time Processing Module
(flight/core/time_processor.py) uses it.

Added for the familiarization exercises. In the tests (and the emulator) the `hal` package is the
`emulator` package -- see tests/cp_mock.py.
"""

import time

import pytest

import tests.cp_mock  # noqa: F401
from flight.core.time_processor import TimeProcessor
from hal.configuration import SATELLITE
from hal.drivers.rtc import RTC

JAN_1_2025 = 1735689600
TOLERANCE_S = 2


def test_rtc_reads_current_time():
    rtc = RTC(time.gmtime())
    assert abs(time.mktime(rtc.datetime) - time.time()) <= TOLERANCE_S


def test_rtc_set_datetime():
    rtc = RTC(time.gmtime())
    rtc.set_datetime(time.localtime(JAN_1_2025))
    assert abs(time.mktime(rtc.datetime) - JAN_1_2025) <= TOLERANCE_S


def test_rtc_keeps_ticking_after_set():
    """After being set, the clock keeps running forward from the new time (it must not freeze)."""
    rtc = RTC(time.gmtime())
    rtc.set_datetime(time.localtime(JAN_1_2025))

    time.sleep(1.5)
    elapsed = time.mktime(rtc.datetime) - JAN_1_2025
    assert 1 <= elapsed <= 1 + TOLERANCE_S


@pytest.fixture
def restore_tpm():
    saved = (TimeProcessor.time_reference, TimeProcessor.time_offset)
    yield
    TimeProcessor.time_reference, TimeProcessor.time_offset = saved


def test_time_processor_set_time_through_emulated_rtc(restore_tpm):
    """This is what the GPS task does every time it gets a fix (flight/tasks/gps.py)."""
    assert SATELLITE.RTC_AVAILABLE

    TimeProcessor.set_time(JAN_1_2025)
    assert abs(TimeProcessor.time() - JAN_1_2025) <= TOLERANCE_S
