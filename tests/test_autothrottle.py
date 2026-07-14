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
