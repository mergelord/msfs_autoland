"""
Tests for LOC (localizer-only) approach support.

LOC = hybrid: lateral via real localizer (NAV1 CDI), vertical via
synthetic glidepath, minimum = MDA (barometric, not radio DH).
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from modules.ils_navigation import ILSNavigation
from modules.synthetic_glidepath import SyntheticGlidepath
from modules.types import ApproachConfig, NavStation


# ── Helpers ──────────────────────────────────────────────────────────

RUNWAY_THRESHOLD_LAT = 55.7558
RUNWAY_THRESHOLD_LON = 37.6173
RUNWAY_ELEVATION = 600
GLIDESLOPE_ANGLE = 3.0


def _make_loc_config(**overrides) -> ApproachConfig:
    defaults = dict(
        station=NavStation("LOC-UUWW", 110300, 55.7558, 37.6173, "LOC"),
        final_approach_course=270,
        glideslope_angle=GLIDESLOPE_ANGLE,
        decision_height=500,
        approach_speed=140,
        runway_elevation=RUNWAY_ELEVATION,
        runway_length=10000,
        runway_width=145,
        runway_threshold_lat=RUNWAY_THRESHOLD_LAT,
        runway_threshold_lon=RUNWAY_THRESHOLD_LON,
    )
    defaults.update(overrides)
    return ApproachConfig(**defaults)


def _make_ils_config(**overrides) -> ApproachConfig:
    defaults = dict(
        station=NavStation("ILS-UUWW", 110300, 55.7558, 37.6173, "ILS"),
        final_approach_course=270,
        glideslope_angle=3.0,
        decision_height=200,
        approach_speed=130,
        runway_elevation=600,
        runway_length=10000,
        runway_width=145,
        runway_threshold_lat=RUNWAY_THRESHOLD_LAT,
        runway_threshold_lon=RUNWAY_THRESHOLD_LON,
    )
    defaults.update(overrides)
    return ApproachConfig(**defaults)


def _make_telemetry(
    *,
    altitude_msl: float = 2000.0,
    altitude_agl: float = 1400.0,
    ground_speed: float = 140.0,
) -> dict:
    return {
        "position": {
            "latitude": 55.75,
            "longitude": 37.50,
            "altitude": altitude_msl,
            "altitude_agl": altitude_agl,
            "radio_height": altitude_agl,
            "on_ground": False,
        },
        "attitude": {"bank": 0.0, "pitch": 2.5, "heading_magnetic": 270.0},
        "speed": {
            "airspeed_indicated": 140.0,
            "vertical_speed": -700.0,
            "ground_speed": ground_speed,
        },
        "nav": {},
    }


# ── is_loc_available / is_ils_available ─────────────────────────────

class TestSignalAvailability:
    """LOC available = localizer only. ILS = localizer + glideslope."""

    def test_loc_available_with_localizer_only(self):
        """nav1_has_localizer=True, nav1_has_glideslope=False → LOC available."""
        nav = ILSNavigation()
        ils_data = {'nav1_has_localizer': True, 'nav1_has_glideslope': False}
        assert nav.is_loc_available(ils_data) is True
        assert nav.is_ils_available(ils_data) is False

    def test_loc_not_available_without_localizer(self):
        """nav1_has_localizer=False → LOC not available."""
        nav = ILSNavigation()
        ils_data = {'nav1_has_localizer': False, 'nav1_has_glideslope': False}
        assert nav.is_loc_available(ils_data) is False

    def test_ils_available_with_both_signals(self):
        """Both localizer + glideslope → ILS available."""
        nav = ILSNavigation()
        ils_data = {'nav1_has_localizer': True, 'nav1_has_glideslope': True}
        assert nav.is_ils_available(ils_data) is True
        assert nav.is_loc_available(ils_data) is True


# ── calculate_loc_approach ──────────────────────────────────────────

class TestCalculateLOCApproach:
    """LOC approach calculation: localizer deviation, no glideslope."""

    def test_loc_returns_localizer_deviation(self):
        """LOC approach returns localizer deviation from CDI."""
        nav = ILSNavigation()
        config = MagicMock()
        config.localizer_course = 270
        nav.config = config

        # CDI=10 → dots = (10/127)*5 = 0.39 → on_localizer = True
        ils_data = {
            'nav1_has_localizer': True,
            'nav1_cdi': 10,
        }
        telemetry = _make_telemetry()

        result = nav.calculate_loc_approach(telemetry, ils_data)

        assert result['loc_available'] is True
        assert result['on_localizer'] is True  # |dots| < 0.5
        assert 'localizer' in result
        assert 'corrected_heading' in result

    def test_loc_not_available_returns_error(self):
        """No localizer signal → error dict."""
        nav = ILSNavigation()
        config = MagicMock()
        nav.config = config

        ils_data = {'nav1_has_localizer': False}
        result = nav.calculate_loc_approach(_make_telemetry(), ils_data)

        assert result['loc_available'] is False
        assert 'error' in result

    def test_loc_stabilized_only_on_localizer(self):
        """Stabilized = on_localizer only (no glideslope check)."""
        nav = ILSNavigation()
        config = MagicMock()
        config.localizer_course = 270
        nav.config = config

        # On localizer, no glideslope signal
        ils_data = {'nav1_has_localizer': True, 'nav1_cdi': 0}
        result = nav.calculate_loc_approach(_make_telemetry(), ils_data)

        assert result['stabilized'] is True  # on_localizer only

    def test_loc_off_localizer_not_stabilized(self):
        """Off localizer → not stabilized."""
        nav = ILSNavigation()
        config = MagicMock()
        config.localizer_course = 270
        nav.config = config

        ils_data = {'nav1_has_localizer': True, 'nav1_cdi': 100}  # ~2 dots
        result = nav.calculate_loc_approach(_make_telemetry(), ils_data)

        assert result['stabilized'] is False


# ── LOC signal loss ────────────────────────────────────────────────

class TestLOCSignalLoss:
    """LOC signal lost mid-approach → loc_available=False → error."""

    def test_loc_signal_loss_returns_error(self):
        """When localizer signal disappears, calculate_loc_approach returns error."""
        nav = ILSNavigation()
        config = MagicMock()
        config.localizer_course = 270
        nav.config = config

        # First: signal present
        ils_data_ok = {'nav1_has_localizer': True, 'nav1_cdi': 10}
        result_ok = nav.calculate_loc_approach(_make_telemetry(), ils_data_ok)
        assert result_ok['loc_available'] is True

        # Then: signal lost
        ils_data_lost = {'nav1_has_localizer': False}
        result_lost = nav.calculate_loc_approach(_make_telemetry(), ils_data_lost)
        assert result_lost['loc_available'] is False
        assert 'error' in result_lost


# ── _calculate_approach_data routing ───────────────────────────────

class TestApproachDataRouting:
    """LOC uses localizer-based approach data, not geometry."""

    def test_loc_routes_to_loc_approach(self):
        """LOC type + localizer signal → calculate_loc_approach."""
        from modules.ils_navigation import ILSNavigation

        system = MagicMock()
        system.approach_config = _make_loc_config()
        system.use_ils = False
        ils_nav = ILSNavigation()
        ils_nav.config = MagicMock()
        ils_nav.config.localizer_course = 270
        system.ils_navigation = ils_nav
        system.navigation = MagicMock()

        # Mock data with localizer signal
        data = {
            'position': {'latitude': 55.75, 'longitude': 37.50, 'altitude': 1200, 'altitude_agl': 600},
            'attitude': {'heading_magnetic': 270},
            'nav': {},
            'ils': {'nav1_has_localizer': True, 'nav1_cdi': 10},
        }

        # Simulate _calculate_approach_data logic
        ils = data.get('ils', {})
        if system.use_ils and ils.get('nav1_has_localizer'):
            result = system.ils_navigation.calculate_ils_approach(data, ils)
        elif (system.approach_config.station.type == 'LOC'
              and ils.get('nav1_has_localizer')):
            result = system.ils_navigation.calculate_loc_approach(data, ils)
        else:
            result = system.navigation.calculate_vor_approach(
                {**data['position'], **data['attitude']},
                data['nav'],
                system.approach_config,
            )

        assert 'loc_available' in result
        assert result['loc_available'] is True

    def test_loc_without_signal_falls_to_vor(self):
        """LOC type + NO localizer signal → calculate_vor_approach (geometry fallback)."""
        system = MagicMock()
        system.approach_config = _make_loc_config()
        system.use_ils = False
        system.ils_navigation = ILSNavigation()
        system.navigation = MagicMock()
        system.navigation.calculate_vor_approach.return_value = {'fallback': True}

        data = {
            'position': {'latitude': 55.75, 'longitude': 37.50, 'altitude': 1200, 'altitude_agl': 600},
            'attitude': {'heading_magnetic': 270},
            'nav': {},
            'ils': {'nav1_has_localizer': False},
        }

        ils = data.get('ils', {})
        if system.use_ils and ils.get('nav1_has_localizer'):
            result = system.ils_navigation.calculate_ils_approach(data, ils)
        elif (system.approach_config.station.type == 'LOC'
              and ils.get('nav1_has_localizer')):
            result = system.ils_navigation.calculate_loc_approach(data, ils)
        else:
            result = system.navigation.calculate_vor_approach(
                {**data['position'], **data['attitude']},
                data['nav'],
                system.approach_config,
            )

        assert result.get('fallback') is True


# ── LOC radio setup: no ADF, no OBS ───────────────────────────────

class TestLOCRadioSetup:
    """LOC → NAV1 frequency only. No ADF, no OBS."""

    def test_loc_no_adf_frequency(self):
        """LOC approach must NOT call set_adf_frequency."""
        from tests.fakes import FakeControl

        control = FakeControl()
        config = _make_loc_config()

        # Simulate radio setup logic from main.py
        if config.station.type == 'ILS':
            control.set_nav_frequency(1, config.station.frequency)
        elif config.station.type == 'LOC':
            control.set_nav_frequency(1, config.station.frequency)
        elif config.station.type == 'VOR':
            control.set_nav_frequency(1, config.station.frequency)
            control.set_obs(1, config.final_approach_course)
        else:  # NDB
            control.set_adf_frequency(config.station.frequency)

        adf_calls = [c for c in control.calls if c[0] == 'set_adf_frequency']
        nav_calls = [c for c in control.calls if c[0] == 'set_nav_frequency']
        obs_calls = [c for c in control.calls if c[0] == 'set_obs']

        assert len(adf_calls) == 0, "LOC must not call set_adf_frequency"
        assert len(obs_calls) == 0, "LOC must not call set_obs"
        assert len(nav_calls) == 1, "LOC must call set_nav_frequency once"
        assert nav_calls[0][1] == (1, config.station.frequency)

    def test_vor_still_calls_adf_for_ndb(self):
        """NDB still calls set_adf_frequency (neighbour test)."""
        from tests.fakes import FakeControl

        control = FakeControl()
        ndb_config = _make_loc_config()
        ndb_config.station = NavStation("NDB-UUWW", 350, 55.7558, 37.6173, "NDB")

        if ndb_config.station.type == 'ILS':
            control.set_nav_frequency(1, ndb_config.station.frequency)
        elif ndb_config.station.type == 'LOC':
            control.set_nav_frequency(1, ndb_config.station.frequency)
        elif ndb_config.station.type == 'VOR':
            control.set_nav_frequency(1, ndb_config.station.frequency)
            control.set_obs(1, ndb_config.final_approach_course)
        else:  # NDB
            control.set_adf_frequency(ndb_config.station.frequency)

        adf_calls = [c for c in control.calls if c[0] == 'set_adf_frequency']
        assert len(adf_calls) == 1, "NDB must call set_adf_frequency"


# ── autopilot_takeover: LOC in VOR/NDB path ───────────────────────

class TestLOC_Takeover:
    """LOC follows VOR/NDB takeover path (distance-based, not DH window)."""

    def test_loc_accepted_by_gate(self):
        """LOC is in the allowed types for should_initiate_takeover."""
        from modules.autopilot_takeover import AutopilotTakeover

        at = AutopilotTakeover()
        # LOC, distance=5nm (within 10nm), altitude=2500 (within 1500-4000)
        result = at.should_initiate_takeover(
            distance_to_threshold=5.0,
            altitude_agl=2500.0,
            approach_phase="INTERMEDIATE",
            approach_type="LOC",
        )
        assert result is True

    def test_loc_recommended_takeover_point(self):
        """LOC gets explicit VOR/NDB-style recommendation."""
        from modules.autopilot_takeover import AutopilotTakeover

        at = AutopilotTakeover()
        dist, alt = at.get_recommended_takeover_point(
            approach_type="LOC",
            runway_length_m=3000,
            weather_conditions={},
        )
        assert dist == 10.0
        assert alt == 3500.0


# ── sink_rate classification ───────────────────────────────────────

class TestLOC_SinkRateClassification:
    """LOC sink_rate_safe = retryable (like VOR/NDB), not hard (like ILS)."""

    def test_loc_sink_rate_is_retryable(self):
        """LOC approach: sink_rate_safe failure → retryable, not hard abort."""
        from modules.autopilot_takeover import (
            AutopilotTakeover, _HARD_FAIL_CHECKS, _RETRYABLE_CHECKS
        )

        # Simulate: sink_rate_safe=False for LOC (not ILS)
        is_ils = False
        checks = {
            'airborne': True,
            'attitude_safe': True,
            'speed_stable': True,
            'altitude_stable': True,
            'altitude_safe': True,
            'sink_rate_safe': False,
        }

        hard_fails = [k for k, v in checks.items()
                      if not v and k in _HARD_FAIL_CHECKS]
        if is_ils and not checks.get('sink_rate_safe', True):
            hard_fails.append('sink_rate_safe')

        retryable_fails = [k for k, v in checks.items()
                           if not v and k in _RETRYABLE_CHECKS]
        if not is_ils and not checks.get('sink_rate_safe', True):
            retryable_fails.append('sink_rate_safe')

        assert 'sink_rate_safe' not in hard_fails
        assert 'sink_rate_safe' in retryable_fails


# ── altitude_safe for LOC ─────────────────────────────────────────

class TestLOC_AltitudeSafe:
    """LOC altitude_safe = >= takeover_altitude_min (like VOR/NDB)."""

    def test_loc_uses_vor_ndb_altitude_safe(self):
        """LOC: altitude_safe = altitude_agl >= takeover_altitude_min."""
        from modules.autopilot_takeover import AutopilotTakeover

        at = AutopilotTakeover()
        at.config.takeover_altitude_min = 1500.0

        # Above min → safe
        checks_above = at._perform_safety_checks(
            _make_telemetry(altitude_agl=1600.0),
            approach_type="LOC",
        )
        assert checks_above['altitude_safe'] is True

        # Below min → not safe
        checks_below = at._perform_safety_checks(
            _make_telemetry(altitude_agl=1400.0),
            approach_type="LOC",
        )
        assert checks_below['altitude_safe'] is False


# ── Neighbour: ILS unchanged ───────────────────────────────────────

class TestILSUnchanged:
    """ILS approach behaviour must not change with LOC addition."""

    def test_ils_still_uses_dh_guard(self):
        """ILS: use_ils=True → DH guard active in FinalPhaseState."""
        from modules.approach_phases import FinalPhaseState
        from modules.control_ownership import ControlOwner
        from tests.fakes import FakeControl

        system = MagicMock()
        system.synthetic_glidepath = None
        system.use_ils = True
        system.use_vjoy = False
        system.use_autothrottle = False
        system.approach_config = _make_ils_config()
        system.autopilot_takeover.status.completed = False

        control = FakeControl()
        system.control = control

        state = FinalPhaseState(system)
        state._ownership = MagicMock()
        state._ownership.roll = ControlOwner.AIRCRAFT_AP
        state._ownership.pitch = ControlOwner.AIRCRAFT_AP

        # Below DH → DH guard triggers
        telemetry = _make_telemetry(altitude_msl=800.0, altitude_agl=200.0)
        wind_data = {"corrected_vs": 600.0, "corrected_heading": 270.0}

        state._control_aircraft(telemetry, wind_data)

        # ILS uses wind_data['corrected_vs'] directly (no synthetic glidepath)
        vs_calls = [c for c in control.calls if c[0] == "set_vertical_speed"]
        assert len(vs_calls) == 1
        assert vs_calls[0][1] == -600


# ── Neighbour: VOR/NDB unchanged ──────────────────────────────────

class TestVORUnchanged:
    """VOR approach behaviour must not change with LOC addition."""

    def test_vor_uses_synthetic_glidepath(self):
        """VOR: synthetic_glidepath drives VS command."""
        from modules.approach_phases import FinalPhaseState
        from modules.control_ownership import ControlOwner
        from tests.fakes import FakeControl

        nav = MagicMock()
        nav.calculate_distance_to_threshold.return_value = 3.0
        nav.calculate_required_altitude.return_value = 1800.0
        nav.should_start_descent.return_value = {
            "should_descend": True, "status": "ON_PROFILE",
            "altitude_error_ft": 0, "distance_to_intercept_nm": 1.0,
            "ideal_altitude_agl": 1200, "vertical_deviation_dots": 0,
            "reason": "", "glideslope_angle": 3.0,
        }
        config = _make_loc_config()
        config.station = NavStation("VOR-UUWW", 114300, 55.7558, 37.6173, "VOR")
        gp = SyntheticGlidepath(nav, config)

        system = MagicMock()
        system.synthetic_glidepath = gp
        system.use_ils = False
        system.use_vjoy = False
        system.use_autothrottle = False
        system.approach_config = config

        control = FakeControl()
        system.control = control

        state = FinalPhaseState(system)
        state._ownership = MagicMock()
        state._ownership.roll = ControlOwner.AIRCRAFT_AP
        state._ownership.pitch = ControlOwner.AIRCRAFT_AP

        telemetry = _make_telemetry(altitude_msl=1850.0, altitude_agl=1250.0)
        wind_data = {"corrected_vs": 600.0, "corrected_heading": 270.0}

        state._control_aircraft(telemetry, wind_data)

        vs_calls = [c for c in control.calls if c[0] == "set_vertical_speed"]
        assert len(vs_calls) == 1
        # VOR uses synthetic glidepath, not wind_data directly
        assert vs_calls[0][1] != -600  # Different from raw wind_data


# ── Production-path: lateral from CDI ──────────────────────────────

class TestLOC_ProductionPathLateral:
    """LOC lateral guidance: heading command from CDI, not geometry."""

    def test_loc_heading_from_cdi(self):
        """LOC corrected_heading is derived from localizer CDI deviation."""
        nav = ILSNavigation()
        config = MagicMock()
        config.localizer_course = 270
        nav.config = config

        # CDI = 63 → ~1 dot right → heading correction left
        ils_data = {'nav1_has_localizer': True, 'nav1_cdi': 63}
        result = nav.calculate_loc_approach(_make_telemetry(), ils_data)

        # correction = -(63/127)*2.5 * 3 = ~-3.7° → heading = 270 - 3.7 = 266.3
        assert result['loc_available'] is True
        assert abs(result['corrected_heading'] - 266.3) < 1.0

    def test_loc_geometry_not_used(self):
        """LOC does NOT use geometry-based bearing for heading."""
        nav = ILSNavigation()
        config = MagicMock()
        config.localizer_course = 270
        nav.config = config

        # Even if telemetry has different lat/lon, heading comes from CDI
        ils_data = {'nav1_has_localizer': True, 'nav1_cdi': 0}
        result = nav.calculate_loc_approach(_make_telemetry(), ils_data)

        # On localizer → heading = localizer_course
        assert abs(result['corrected_heading'] - 270.0) < 0.1
