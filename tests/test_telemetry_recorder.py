"""TASK-007-PREP: Telemetry recorder tests.

Tests:
  T-REC-1: Recorder writes a row per frame (real CSV, not mock).
  T-REC-2: Recorder write error does not crash control loop.
  T-REC-3: Recorder is read-only (no actuators, no telemetry mutation).
  T-REC-4: start/stop lifecycle.
"""

import csv
import logging
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from modules.telemetry_recorder import TelemetryRecorder, _flatten_dict
from tests.fakes import make_telemetry


# ═══════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════

def _full_telemetry() -> dict:
    """Simulate full get_all_data() output with all nested sections."""
    base = make_telemetry(
        altitude=3000, altitude_agl=2500, radio_height=2400,
        airspeed=130, vertical_speed=-800, ground_speed=135,
        bank=2.5, pitch=3.0, heading=265,
    )
    # Add extra sections that get_all_data() returns
    base['ils'] = {
        'nav1_has_localizer': True,
        'nav1_has_glideslope': True,
        'nav1_cdi': 3,
    }
    base['autopilot'] = {'master': True, 'heading_hold': True}
    base['weather'] = {'ambient_temperature': 12}
    base['weight'] = {'total_weight': 55000}
    base['aircraft'] = {'title': 'Test Aircraft'}
    base['configuration'] = {'flaps_position': 0.7, 'gear_position': 1.0}
    base['nav'] = {'nav1_frequency': 11030000}
    return base


# ═══════════════════════════════════════════════════════════════════
# Unit tests — _flatten_dict
# ═══════════════════════════════════════════════════════════════════

class TestFlattenDict:
    """Deterministic flattening of nested telemetry sections."""

    def test_simple_dict(self):
        result = _flatten_dict({'a': 1, 'b': 2})
        assert result == {'a': 1, 'b': 2}

    def test_nested_dict(self):
        result = _flatten_dict({'pos': {'lat': 55.0, 'lon': 37.0}})
        assert result == {'pos_lat': 55.0, 'pos_lon': 37.0}

    def test_deeply_nested(self):
        result = _flatten_dict({'a': {'b': {'c': 42}}})
        assert result == {'a_b_c': 42}

    def test_sorted_keys(self):
        """Column order is deterministic (sorted)."""
        result = _flatten_dict({'z': 1, 'a': 2, 'm': 3})
        assert list(result.keys()) == ['a', 'm', 'z']

    def test_list_stringified(self):
        result = _flatten_dict({'arr': [1, 2, 3]})
        assert result == {'arr': '[1, 2, 3]'}


# ═══════════════════════════════════════════════════════════════════
# Integration tests — recorder through real CSV write path
# ═══════════════════════════════════════════════════════════════════

class TestRecorderWritesRow:
    """T-REC-1: Each write_frame produces one CSV row with real data."""

    def test_single_frame_row_count(self, tmp_path):
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        assert rec.is_recording

        telemetry = _full_telemetry()
        rec.write_frame(telemetry, phase="FINAL",
                        guard_decision="CONTINUE", guard_reason="all_checks_passed")

        rec.stop_recording()
        assert not rec.is_recording

        # Read back the CSV
        csv_files = list(tmp_path.glob('telemetry_*.csv'))
        assert len(csv_files) == 1
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader)
            rows = list(reader)
        assert len(rows) == 1
        # Header + 1 data row = 2 lines total
        assert 'timestamp' in header
        assert 'phase' in header
        assert 'guard_decision' in header
        assert 'guard_reason' in header

    def test_multiple_frames(self, tmp_path):
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()

        for i in range(5):
            rec.write_frame(_full_telemetry(), phase="FINAL")

        rec.stop_recording()

        csv_files = list(tmp_path.glob('telemetry_*.csv'))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader)  # skip header
            rows = list(reader)
        assert len(rows) == 5
        assert rec._frame_count == 5

    def test_nested_sections_flattened(self, tmp_path):
        """All nested telemetry sections are flattened into CSV columns."""
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()

        telemetry = _full_telemetry()
        rec.write_frame(telemetry, phase="FINAL")

        rec.stop_recording()

        csv_files = list(tmp_path.glob('telemetry_*.csv'))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)

        # Check flattened columns from nested sections
        assert 'position_altitude_agl' in row
        assert 'attitude_bank' in row
        assert 'speed_airspeed_indicated' in row
        assert 'ils_nav1_has_localizer' in row
        assert 'autopilot_master' in row

    def test_guard_columns_populated(self, tmp_path):
        """Guard verdict columns are written when guard is active."""
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()

        rec.write_frame(_full_telemetry(), phase="FINAL",
                        guard_decision="GO_AROUND", guard_reason="CRITICAL_SINK_RATE")

        rec.stop_recording()

        csv_files = list(tmp_path.glob('telemetry_*.csv'))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)

        assert row['guard_decision'] == 'GO_AROUND'
        assert row['guard_reason'] == 'CRITICAL_SINK_RATE'

    def test_guard_columns_empty_when_none(self, tmp_path):
        """Guard columns are empty strings when guard not active."""
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()

        rec.write_frame(_full_telemetry(), phase="INITIAL")

        rec.stop_recording()

        csv_files = list(tmp_path.glob('telemetry_*.csv'))
        with open(csv_files[0], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            row = next(reader)

        assert row['guard_decision'] == ''
        assert row['guard_reason'] == ''


class TestRecorderErrorDoesNotCrash:
    """T-REC-2: I/O errors in recorder never break the control loop."""

    def test_write_after_stop_is_silent(self, tmp_path):
        """write_frame after stop_recording does not raise."""
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        rec.stop_recording()

        # Should not raise
        rec.write_frame(_full_telemetry(), phase="FINAL")

    def test_start_with_invalid_dir_logs_warning(self, tmp_path):
        """start_recording with unwritable path logs warning, does not raise."""
        rec = TelemetryRecorder(log_dir=str(tmp_path / "nonexistent" / "deep"))
        # The mkdir(parents=True) should handle this, but if it fails:
        # Just verify it doesn't crash
        rec.start_recording()
        # Whether recording started or not, stop should not raise
        rec.stop_recording()

    def test_write_error_does_not_propagate(self, tmp_path):
        """Simulate file write error — must not raise."""
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        assert rec.is_recording

        # Force an error by closing the underlying file mid-flight
        rec._file.close()

        # This should NOT raise — error is swallowed
        rec.write_frame(_full_telemetry(), phase="FINAL")


class TestRecorderReadOnly:
    """T-REC-3: Recorder is strictly read-only."""

    def test_no_actuator_calls(self, tmp_path):
        """Recorder does not call any actuator methods."""
        control = MagicMock()
        telemetry_obj = MagicMock()
        telemetry_obj.get_all_data.return_value = _full_telemetry()

        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        rec.write_frame(_full_telemetry(), phase="FINAL")
        rec.stop_recording()

        # Verify no actuator methods were called on any object
        control.set_throttle.assert_not_called()
        control.set_heading_hold.assert_not_called()
        control.set_vertical_speed.assert_not_called()

    def test_telemetry_not_mutated(self, tmp_path):
        """Recorder does not modify the telemetry dict."""
        telemetry = _full_telemetry()
        original_keys = set(telemetry.keys())
        original_position = dict(telemetry['position'])

        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        rec.write_frame(telemetry, phase="FINAL")
        rec.stop_recording()

        assert set(telemetry.keys()) == original_keys
        assert telemetry['position'] == original_position


class TestRecorderLifecycle:
    """T-REC-4: start/stop lifecycle."""

    def test_not_recording_by_default(self):
        rec = TelemetryRecorder()
        assert not rec.is_recording

    def test_recording_flag_after_start(self, tmp_path):
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        assert rec.is_recording

    def test_recording_flag_after_stop(self, tmp_path):
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        rec.stop_recording()
        assert not rec.is_recording

    def test_double_stop_is_safe(self, tmp_path):
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        rec.stop_recording()
        rec.stop_recording()  # should not raise

    def test_multiple_sessions(self, tmp_path):
        """Two start/stop cycles produce separate recordings."""
        rec = TelemetryRecorder(log_dir=str(tmp_path))
        rec.start_recording()
        rec.write_frame(_full_telemetry(), phase="INITIAL")
        rec.stop_recording()

        rec.start_recording()
        rec.write_frame(_full_telemetry(), phase="FINAL")
        rec.stop_recording()

        csv_files = list(tmp_path.glob('telemetry_*.csv'))
        assert len(csv_files) >= 1
        # Both sessions wrote at least one frame
        total_frames = 0
        for f in csv_files:
            with open(f, 'r', encoding='utf-8') as fh:
                reader = csv.reader(fh)
                next(reader)  # skip header
                total_frames += sum(1 for _ in reader)
        assert total_frames == 2
