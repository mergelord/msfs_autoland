"""Tests for VJoyThrottleIntegration (FIX-01, FIX-02)."""
import pytest


def test_vjoy_enable_no_attribute_error():
    """FIX-01: VJoyThrottleIntegration.enable() must not raise AttributeError."""
    from modules.virtual_joystick import VirtualJoystick
    from modules.autothrottle import VJoyThrottleIntegration

    vj = VirtualJoystick.__new__(VirtualJoystick)
    vj.__init__(device_id=1)
    integration = VJoyThrottleIntegration(vj)
    # Must not raise AttributeError; pyvjoy unavailable so enabled=False
    result = integration.enable()
    assert result is False


def test_vjoy_throttle_range_passthrough():
    """FIX-02: VJoyThrottleIntegration.set_throttle passes 0..1 directly."""
    from modules.virtual_joystick import VirtualJoystick
    from modules.autothrottle import VJoyThrottleIntegration

    received = []
    vj = VirtualJoystick.__new__(VirtualJoystick)
    vj.__init__(device_id=1)
    vj.set_throttle = lambda v: received.append(v)
    vj.enabled = True  # after FIX-01
    integration = VJoyThrottleIntegration(vj)
    integration.enabled = True
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        integration.set_throttle(t)
    assert received == [0.0, 0.25, 0.5, 0.75, 1.0], f"Got {received}"


# --- FIX-05: Unit conversion verification ---

def test_runway_length_conversion():
    """FIX-05a: 8000 ft -> ~2438 m."""
    result = 8000 / 3.28084
    assert abs(result - 2438.4) < 1.0


def test_weight_conversion():
    """FIX-05b: 132277 lbs -> ~60000 kg."""
    result = 132277 * 0.453592
    assert abs(result - 59999) < 5


# --- REM-02: Production-path regression test for FIX-05 ---

def test_calculate_approach_speeds_kwargs():
    """REM-02: _calculate_approach_speeds passes correct units to calculator."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    # Fake telemetry
    fake_telemetry = {
        'weather': {
            'wind_direction': 0,
            'wind_velocity': 0,
            'wind_gust': 0,
            'ambient_temperature': 15,
        },
        'aircraft': {'title': 'Test Aircraft'},
        'weight': {'total_weight': 132277},
    }

    # Spy on speed_calculator
    captured_kwargs = {}
    fake_calculator = MagicMock()
    fake_calculator.calculate_approach_parameters.side_effect = lambda **kw: (
        captured_kwargs.update(kw),
        {
            'aircraft_name': 'Test', 'flaps_configuration': 'LANDING',
            'vref': 120, 'vapp': 125,
            'wind_correction': 0, 'gust_correction': 0,
            'altitude_correction': 0, 'temperature_correction': 0,
            'weight_ok': True, 'aircraft_weight_kg': kw.get('aircraft_weight_kg', 60000),
            'max_landing_weight_kg': 70000,
        }
    )[1]

    # Build minimal system
    from main import AutoLandSystem
    system = AutoLandSystem.__new__(AutoLandSystem)
    system.telemetry = MagicMock()
    system.telemetry.get_all_data.return_value = fake_telemetry
    system.speed_calculator = fake_calculator
    system.connection_monitor = None
    system.connection_optimizer = None
    system.structured_logger = MagicMock()

    # Config
    config = SimpleNamespace(
        runway_length=8000,
        runway_elevation=0,
        final_approach_course=0,
        approach_speed=120,
        glideslope_angle=3.0,
        decision_height=200,
        station=SimpleNamespace(type='VOR', name='Test', frequency=11030000),
    )

    # Call real method
    system._calculate_approach_speeds(config)

    # Assert captured kwargs
    assert captured_kwargs['runway_length_m'] == pytest.approx(8000 / 3.28084, rel=1e-4)
    assert captured_kwargs['aircraft_weight_kg'] == pytest.approx(132277 * 0.453592, rel=1e-4)
    assert captured_kwargs['aircraft_title'] == 'Test Aircraft'


def test_calculate_approach_speeds_fallback_weight():
    """REM-02: Fallback to 60000 kg when total_weight is absent."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    fake_telemetry = {
        'weather': {
            'wind_direction': 0, 'wind_velocity': 0,
            'wind_gust': 0, 'ambient_temperature': 15,
        },
        'aircraft': {'title': 'Test'},
        'weight': {},  # no total_weight
    }

    captured_kwargs = {}
    fake_calculator = MagicMock()
    fake_calculator.calculate_approach_parameters.side_effect = lambda **kw: (
        captured_kwargs.update(kw),
        {
            'aircraft_name': 'Test', 'flaps_configuration': 'LANDING',
            'vref': 120, 'vapp': 125,
            'wind_correction': 0, 'gust_correction': 0,
            'altitude_correction': 0, 'temperature_correction': 0,
            'weight_ok': True, 'aircraft_weight_kg': 60000,
            'max_landing_weight_kg': 70000,
        }
    )[1]

    from main import AutoLandSystem
    system = AutoLandSystem.__new__(AutoLandSystem)
    system.telemetry = MagicMock()
    system.telemetry.get_all_data.return_value = fake_telemetry
    system.speed_calculator = fake_calculator
    system.connection_monitor = None
    system.connection_optimizer = None
    system.structured_logger = MagicMock()

    config = SimpleNamespace(
        runway_length=8000, runway_elevation=0, final_approach_course=0,
        approach_speed=120, glideslope_angle=3.0, decision_height=200,
        station=SimpleNamespace(type='VOR', name='Test', frequency=11030000),
    )

    system._calculate_approach_speeds(config)
    assert captured_kwargs['aircraft_weight_kg'] == pytest.approx(60000, rel=1e-4)
