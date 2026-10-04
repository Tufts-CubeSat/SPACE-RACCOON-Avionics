"""
Unit tests for DataProcess, the struct-formatted telemetry logger in flight/core/data_handler.py.

Added for the familiarization exercises. (tests/test_data_handler.py covers FileProcess.)
"""

# isort: skip_file
import struct

import pytest

import tests.cp_mock  # noqa: F401
import flight.core.data_handler as dh

DH = dh.DataHandler


@pytest.fixture
def sd_root(tmp_path, monkeypatch):
    sd_root = tmp_path / "sd_root"
    sd_root.mkdir()
    monkeypatch.setattr(dh, "_HOME_PATH", str(sd_root))
    return sd_root


def records_on_disk(process):
    """Read back every record written to the process' current file."""
    with open(process.current_path, "rb") as f:
        raw = f.read()
    assert len(raw) % process.bytesize == 0, "file must contain only whole records"
    return [struct.unpack(process.data_format, raw[i : i + process.bytesize]) for i in range(0, len(raw), process.bytesize)]


def test_bytesize_matches_format(sd_root):
    DH.register_data_process("fmt_test", "BhIf", persistent=True)
    process = DH.data_process_registry["fmt_test"]
    assert process.data_format == "<BhIf"
    assert process.bytesize == 1 + 2 + 4 + 4


def test_every_sample_written_with_default_interval(sd_root):
    DH.register_data_process("every_test", "if", persistent=True)
    process = DH.data_process_registry["every_test"]

    for i in range(4):
        DH.log_data("every_test", [i, i * 0.5])

    assert records_on_disk(process) == [(0, 0.0), (1, 0.5), (2, 1.0), (3, 1.5)]


def test_write_interval(sd_root):
    """
    With write_interval=N only every Nth sample goes to the SD card -- starting with the very first one,
    so a freshly booted satellite has data on disk right away. Every sample is still available in RAM.
    """
    DH.register_data_process("interval_test", "i", persistent=True, write_interval=3)
    process = DH.data_process_registry["interval_test"]

    records_after_each_log = []
    for sample in range(1, 8):
        DH.log_data("interval_test", [sample])
        assert DH.get_latest_data("interval_test") == [sample]
        records_after_each_log.append(len(records_on_disk(process)))

    #                                 samples:  1  2  3  4  5  6  7
    assert records_after_each_log == [1, 1, 1, 2, 2, 2, 3]
    assert records_on_disk(process) == [(1,), (4,), (7,)]


def test_non_persistent_process_keeps_latest_only(sd_root):
    DH.register_data_process("ram_only", "ii", persistent=False)
    assert not DH.data_available("ram_only")

    DH.log_data("ram_only", [1, 2])
    DH.log_data("ram_only", [3, 4])
    assert DH.get_latest_data("ram_only") == [3, 4]

    DH.clear_latest_data("ram_only")
    assert not DH.data_available("ram_only")
    assert not (sd_root / "ram_only").exists()


def test_latest_data_recovered_after_reboot(sd_root):
    """
    After a reboot the data handler re-registers each process from the SD card. The latest data point
    must be restored from the last record in the newest file so tasks can resume where they left off.
    """
    DH.register_data_process("reboot_test", "iI", persistent=True)
    for record in ([1, 2], [3, 4], [5, 6]):
        DH.log_data("reboot_test", record)
    DH.data_process_registry["reboot_test"].close()

    # --- simulate a reboot: forget everything in RAM and rebuild from the SD card ---
    DH.data_process_registry.clear()
    DH.scan_SD_card()

    assert DH.data_process_exists("reboot_test")
    latest = DH.get_latest_data("reboot_test")
    assert latest is not None, "latest data point was not recovered from the SD card"
    assert tuple(latest) == (5, 6)


def test_unregistered_tag_is_handled(sd_root):
    # Logging to an unknown tag must not raise (a crash here would take down the calling task)
    DH.log_data("does_not_exist", [1])
    assert DH.get_latest_data("does_not_exist") is None
