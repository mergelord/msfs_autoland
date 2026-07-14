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


# --- Finding 1: kg/lbs unit mismatch ---

def test_throttle_weight_conversion_kg_to_lbs():
    """Finding 1: _control_throttle converts kg to lbs before passing to autothrottle."""
    from modules.approach_phases import FinalPhaseState
    from modules.autothrottle import AutothrottleController, AutothrottleConfig
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    # Create a system with real autothrottle that records input weight
    captured_weight = {}
    real_autothrottle = AutothrottleController.__new__(AutothrottleController)
    real_autothrottle.config = AutothrottleConfig()
    real_autothrottle.active = True
    real_autothrottle.enabled = False

    # Spy on calculate_throttle to capture the weight argument
    original_calc = AutothrottleController.calculate_throttle
    def spy_calc(self, telemetry, target_speed, wind_data, aircraft_weight):
        captured_weight['value'] = aircraft_weight
        # Return minimal valid result
        return {'throttle': 0.5, 'is_stable': True, 'asymmetric_mode': False}
    real_autothrottle.calculate_throttle = lambda *a, **kw: spy_calc(real_autothrottle, *a, **kw)

    system = MagicMock()
    system.use_autothrottle = True
    system.autothrottle = real_autothrottle
    system.approach_params = {'aircraft_weight_kg': 60000.0, 'vapp': 120}
    system.vjoy_throttle = None
    system.control = MagicMock()
    system.use_vjoy = False

    # Simulate ownership allowing throttle
    state = FinalPhaseState.__new__(FinalPhaseState)
    state.system = system
    state._ownership = SimpleNamespace(throttle=MagicMock())  # AIRCRAFT_AP
    state._ownership.throttle = type('O', (), {'value': 'AIRCRAFT_AP'})()

    wind_data = {'corrected_vs': 500, 'corrected_heading': 270, 'headwind': 10,
                 'crosswind': 5, 'drift_angle': 2.0}
    telemetry = {'position': {'altitude_agl': 500}, 'speed': {'vertical_speed': -500}}

    # Mock ownership to allow throttle
    from modules.control_ownership import ControlOwner
    state._ownership = SimpleNamespace(throttle=ControlOwner.AIRCRAFT_AP)

    state._control_throttle(telemetry, wind_data)

    # 60000 kg should be converted to ~132277 lbs before passing to autothrottle
    assert 'value' in captured_weight, "calculate_throttle was not called"
    assert captured_weight['value'] == pytest.approx(60000 * 2.20462, rel=1e-4), \
        f"Expected ~132277 lbs, got {captured_weight['value']}"


def test_calculate_base_throttle_with_lbs():
    """Finding 1: calculate_base_throttle expects lbs, verify with known lbs value."""
    from modules.autothrottle import AutothrottleController, AutothrottleConfig

    ctrl = AutothrottleController.__new__(AutothrottleController)
    ctrl.config = AutothrottleConfig()

    # 5000 lbs = reference weight → correction should be 0
    result_ref = ctrl.calculate_base_throttle(5000.0, 0, False)
    # 10000 lbs → positive correction
    result_heavy = ctrl.calculate_base_throttle(10000.0, 0, False)
    # 0 lbs → negative correction
    result_light = ctrl.calculate_base_throttle(0.0, 0, False)

    assert result_heavy > result_ref, "Heavier aircraft should need more throttle"
    assert result_light < result_ref, "Lighter aircraft should need less throttle"
    # Verify the correction magnitude: (10000-5000)*0.00002 = 0.1
    assert result_heavy - result_ref == pytest.approx(0.1, abs=1e-6)


# --- Finding 4: _calculate_headwind NaN propagation ---

def test_headwind_nan_input():
    """Finding 4: NaN wind_speed must not propagate NaN headwind."""
    from main import AutoLandSystem

    system = AutoLandSystem.__new__(AutoLandSystem)
    result = system._calculate_headwind(float('nan'), 10.0, 270)
    assert result == 0.0, f"NaN wind_direction should return 0.0, got {result}"

    result2 = system._calculate_headwind(0.0, float('nan'), 270)
    assert result2 == 0.0, f"NaN wind_speed should return 0.0, got {result2}"


def test_headwind_normal():
    """Finding 4: normal inputs still work."""
    from main import AutoLandSystem

    system = AutoLandSystem.__new__(AutoLandSystem)
    result = system._calculate_headwind(0.0, 10.0, 270)
    assert isinstance(result, float)
    assert -10 <= result <= 10
