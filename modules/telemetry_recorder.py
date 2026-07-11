"""CSV telemetry recorder — read-only, never breaks the control loop.

Records every execute_approach frame (2 Hz) to a CSV file for offline analysis.
File opens at start_approach, closes at stop_approach. Any I/O error is
swallowed with a warning; the flight continues.

Schema: pre-defined from known get_all_data() structure. Each frame is written
immediately to disk — no RAM buffering. Process crash before stop does not
destroy recorded data.
"""

import csv
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Pre-defined stable schema: all known flat keys from get_all_data().
# Built once; never depends on first frame content.
_KNOWN_SECTIONS = {
    'position': ['altitude', 'altitude_agl', 'latitude', 'longitude',
                 'on_ground', 'radio_height'],
    'attitude': ['bank', 'heading_magnetic', 'heading_true', 'pitch'],
    'speed': ['airspeed_indicated', 'airspeed_true', 'ground_speed',
              'vertical_speed'],
    'nav': ['adf_frequency', 'adf_radial', 'adf_signal',
            'nav1_dme_distance', 'nav1_frequency', 'nav1_obs',
            'nav1_radial', 'nav1_signal',
            'nav2_dme_distance', 'nav2_frequency', 'nav2_obs',
            'nav2_radial', 'nav2_signal'],
    'ils': ['nav1_cdi', 'nav1_gsi', 'nav1_gs_flag', 'nav1_has_glideslope',
            'nav1_has_localizer', 'nav1_ident', 'nav1_localizer_crs',
            'nav1_to_from',
            'nav2_cdi', 'nav2_gsi', 'nav2_has_glideslope',
            'nav2_has_localizer', 'nav2_localizer_crs'],
    'autopilot': ['airspeed_hold', 'altitude_hold', 'approach_hold',
                  'heading_hold', 'master', 'nav_hold'],
    'weather': ['ambient_temperature', 'ambient_wind_direction',
                'ambient_wind_velocity', 'barometer_pressure',
                'kohlsman_setting_mb', 'sea_level_pressure'],
    'weight': ['empty_weight', 'fuel_weight', 'payload_weight',
               'total_weight'],
    'aircraft': ['aircraft_manufacturer', 'autopilot_max_bank',
                 'autopilot_type', 'autopilot_available', 'atc_model',
                 'atc_type', 'category', 'engine_type', 'engine_type_name',
                 'is_custom_aircraft', 'is_gear_retractable',
                 'is_tail_dragger', 'number_of_engines', 'title'],
    'configuration': ['flaps_position', 'gear_position', 'spoilers_position'],
    'g_force_data': ['acceleration_body_x', 'acceleration_body_y',
                     'acceleration_body_z', 'g_force'],
    'gps_destination': ['airport_icao', 'bearing', 'distance_nm',
                        'latitude', 'longitude', 'raw_id', 'runway_id',
                        'altitude'],
    'approach_info': ['approach_active', 'approach_type',
                      'decision_height', 'glideslope_valid',
                      'ils_frequency', 'localizer_valid',
                      'minimum_descent_altitude'],
}

# Top-level scalar keys from get_all_data()
_SCALAR_KEYS = ['g_force']


def _build_fieldnames() -> list:
    """Build sorted list of all known CSV column names."""
    fields = ['timestamp', 'phase', 'guard_decision', 'guard_reason']
    for section, subkeys in sorted(_KNOWN_SECTIONS.items()):
        for subkey in sorted(subkeys):
            fields.append(f'{section}_{subkey}')
    for key in sorted(_SCALAR_KEYS):
        fields.append(key)
    return sorted(fields)


# Module-level constant: the stable, deterministic CSV schema
FIELDNAMES = _build_fieldnames()


def _flatten_dict(d: dict, parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Deterministically flatten nested dict into flat key-value pairs.

    Keys: section_subkey (e.g. position_altitude_agl, attitude_bank).
    Non-dict scalars are kept as-is; dicts are recursed.
    Lists/tuples are stringified (shouldn't appear in telemetry).
    """
    items: list = []
    for k, v in sorted(d.items()):  # sorted for deterministic column order
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep).items())
        elif isinstance(v, (list, tuple)):
            items.append((new_key, str(v)))
        else:
            items.append((new_key, v))
    return dict(items)


class TelemetryRecorder:
    """Append-only CSV recorder. Strictly read-only — no actuators, no telemetry writes.

    Each frame is written immediately to disk via csv.DictWriter.
    Schema is pre-defined (FIELDNAMES) — no dynamic drift.
    """

    _session_counter: int = 0  # monotonic per-process counter for unique filenames

    def __init__(self, log_dir: str = 'logs') -> None:
        self._log_dir = Path(log_dir)
        self._file = None
        self._writer: Optional[csv.DictWriter] = None
        self._frame_count: int = 0
        self._filepath: Optional[Path] = None

    @property
    def is_recording(self) -> bool:
        return self._file is not None and not self._file.closed

    def start_recording(self) -> None:
        """Open a new CSV file and write the header immediately."""
        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
            TelemetryRecorder._session_counter += 1
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filepath = self._log_dir / f'telemetry_{timestamp}_{TelemetryRecorder._session_counter}.csv'
            self._file = open(filepath, 'w', newline='', encoding='utf-8')
            self._writer = csv.DictWriter(self._file, fieldnames=FIELDNAMES,
                                          extrasaction='ignore')
            self._writer.writeheader()
            self._file.flush()
            self._frame_count = 0
            self._filepath = filepath
            logger.info("Telemetry recorder started: %s", filepath)
        except Exception as e:
            logger.warning("Telemetry recorder failed to start: %s", e)
            self._file = None
            self._writer = None

    def stop_recording(self) -> None:
        """Close the file. Rows are already on disk — this just releases the handle."""
        try:
            if self._file and not self._file.closed:
                self._file.flush()
                self._file.close()
                logger.info("Telemetry recorder stopped (%d frames written)",
                            self._frame_count)
        except Exception as e:
            logger.warning("Telemetry recorder close error: %s", e)
        finally:
            try:
                if self._file and not self._file.closed:
                    self._file.close()
            except Exception:
                pass
            self._file = None
            self._writer = None

    def write_frame(
        self,
        telemetry: dict,
        phase: str,
        guard_decision: Optional[str] = None,
        guard_reason: Optional[str] = None,
    ) -> None:
        """Write one telemetry frame immediately to disk. Never raises.

        Args:
            telemetry: Full get_all_data() dict (nested sections).
            phase: Current approach phase name (e.g. "FINAL").
            guard_decision: Guard verdict string if guard was active this frame.
            guard_reason: Guard reason code if guard was active this frame.
        """
        if not self.is_recording:
            return

        try:
            row: Dict[str, Any] = {}
            row['timestamp'] = time.time()
            row['phase'] = phase

            # Flatten all nested telemetry sections deterministically
            for section_name in sorted(telemetry.keys()):
                section = telemetry[section_name]
                if isinstance(section, dict):
                    flat = _flatten_dict(section, parent_key=section_name)
                    row.update(flat)
                else:
                    row[section_name] = section

            # Guard verdict columns
            row['guard_decision'] = guard_decision if guard_decision is not None else ''
            row['guard_reason'] = guard_reason if guard_reason is not None else ''

            self._writer.writerow(row)
            self._file.flush()
            self._frame_count += 1
        except Exception as e:
            # Swallow ALL errors — recorder must never break the control loop
            logger.warning("Telemetry recorder write error: %s", e)
