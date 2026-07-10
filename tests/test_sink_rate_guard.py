"""
Tests for sink rate guard in autopilot takeover.

TASK-003: Sink rate check during takeover.
Threshold: 1000 fpm descent (vertical_speed >= -1000).
"""

import time
import pytest
from modules.autopilot_takeover import AutopilotTakeover, TakeoverConfig


def make_telemetry(vertical_speed: float = 0.0,
                   altitude_agl: float = 3000.0,
                   on_ground: bool = False,
                   airspeed: float = 140.0,
                   altitude: float = 5000.0,
                   bank: float = 0.0,
                   pitch: float = -2.0) -> dict:
    """Create minimal telemetry dict for testing."""
    return {
        'position': {
            'altitude': altitude,
            'altitude_agl': altitude_agl,
            'on_ground': on_ground
        },
        'speed': {
            'airspeed_indicated': airspeed,
            'vertical_speed': vertical_speed
        },
        'attitude': {
            'heading_magnetic': 180.0,
            'pitch': pitch,
            'bank': bank
        }
    }


class TestSinkRateGuard:
    """Sink rate safety check tests."""

    def test_sink_rate_within_limit_passes(self):
        """Normal descent (-500 fpm) should pass sink rate check."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=-500.0)
        checks = takeover._perform_safety_checks(telemetry)

        assert checks['sink_rate_safe'] is True

    def test_sink_rate_at_limit_passes(self):
        """Sink rate exactly at limit (-1000 fpm) should pass."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=-1000.0)
        checks = takeover._perform_safety_checks(telemetry)

        assert checks['sink_rate_safe'] is True

    def test_sink_rate_exceeds_limit_fails(self):
        """Excessive descent (-1100 fpm) should fail sink rate check."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=-1100.0)
        checks = takeover._perform_safety_checks(telemetry)

        assert checks['sink_rate_safe'] is False

    def test_sink_rate_climb_passes(self):
        """Positive vertical speed (climb) should always pass."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=500.0)
        checks = takeover._perform_safety_checks(telemetry)

        assert checks['sink_rate_safe'] is True

    def test_sink_rate_zero_passes(self):
        """Level flight (0 fpm) should pass."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=0.0)
        checks = takeover._perform_safety_checks(telemetry)

        assert checks['sink_rate_safe'] is True

    def test_sink_rate_custom_threshold(self):
        """Custom threshold should be respected."""
        config = TakeoverConfig(sink_rate_max=800.0)
        takeover = AutopilotTakeover(config)
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        # -850 fpm exceeds 800 fpm limit
        telemetry = make_telemetry(vertical_speed=-850.0)
        checks = takeover._perform_safety_checks(telemetry)

        assert checks['sink_rate_safe'] is False

    def test_sink_rate_aborts_takeover(self):
        """Unsafe sink rate should abort takeover with failed status."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.status.in_progress = True
        takeover.takeover_start_time = time.time()  # Recent to avoid timeout
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=-1200.0, altitude_agl=2000.0)
        
        # Mock aircraft_adapter and control
        class MockAdapter:
            def disengage_autopilot(self): return True
            def disengage_autothrottle(self): return True
        class MockControl:
            def set_autopilot_master(self, v): pass
            def set_heading_hold(self, v): pass
            def set_altitude_hold(self, v): pass
            def set_airspeed_hold(self, v): pass
            def set_vertical_speed_hold(self, v): pass

        status = takeover.perform_takeover(telemetry, MockAdapter(), MockControl())

        assert status.failed is True
        assert 'Sink rate' in status.error_message
        assert 'exceeds limit' in status.error_message

    def test_sink_rate_safe_takeover_proceeds(self):
        """Safe sink rate should not abort takeover."""
        config = TakeoverConfig(sink_rate_max=1000.0)
        takeover = AutopilotTakeover(config)
        takeover.status.in_progress = True
        takeover.takeover_start_time = time.time()  # Recent to avoid timeout
        takeover.initial_parameters = {'airspeed': 140.0, 'altitude': 5000.0}

        telemetry = make_telemetry(vertical_speed=-500.0, altitude_agl=3000.0)
        
        class MockAdapter:
            def disengage_autopilot(self): return True
            def disengage_autothrottle(self): return True
        class MockControl:
            def set_autopilot_master(self, v): pass
            def set_heading_hold(self, v): pass
            def set_altitude_hold(self, v): pass
            def set_airspeed_hold(self, v): pass
            def set_vertical_speed_hold(self, v): pass
            def get_autopilot_engaged(self): return False
            def get_autothrottle_engaged(self): return False

        status = takeover.perform_takeover(telemetry, MockAdapter(), MockControl())

        assert status.failed is False


class TestSinkRateConfig:
    """Configuration tests for sink rate."""

    def test_default_sink_rate_threshold(self):
        """Default threshold should be 1000 fpm."""
        config = TakeoverConfig()
        assert config.sink_rate_max == 1000.0

    def test_custom_sink_rate_threshold(self):
        """Custom threshold should be settable."""
        config = TakeoverConfig(sink_rate_max=800.0)
        assert config.sink_rate_max == 800.0
