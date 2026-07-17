"""
Tests for P0 safety fixes: A-DISP-1, A-CONF-1, A-CONF-4, B-AT-1.

A-DISP-1: SimConnect event dispatch compatibility
A-CONF-1: Flaps via discrete events (FLAPS_UP/1/2/3)
A-CONF-4: Deterministic AP_VS_ON (not toggle AP_VS_HOLD)
B-AT-1:   Continuous flaps fraction in autothrottle
"""

import pytest
from unittest.mock import MagicMock, call

from modules.control import MSFSControl, SDK_ONLY_EVENTS
from modules.autothrottle import AutothrottleController, AutothrottleConfig


# ── FakeEvents: models real AircraftEvents API (find + callable) ──


class FakeEvent:
    """Simulates SimConnect.EventList.Event — callable, records calls."""

    def __init__(self, name: str):
        self.name = name
        self.calls: list = []

    def __call__(self, value=None):
        self.calls.append(value)


class FakeAircraftEvents:
    """Simulates real AircraftEvents: find() returns callable Event objects.

    Does NOT have .event() method — matching real SimConnect v0.4.26 API.
    """

    def __init__(self, catalog: dict[str, FakeEvent] | None = None):
        self._catalog: dict[str, FakeEvent] = catalog or {}
        self.sm = MagicMock()  # for SDK-only Event construction
        self.find_calls: list[str] = []

    def find(self, name: str):
        self.find_calls.append(name)
        return self._catalog.get(name)


def _make_ae_with_catalog(event_names: list[str]) -> FakeAircraftEvents:
    """Create FakeAircraftEvents with a catalog of named FakeEvents."""
    catalog = {name: FakeEvent(name) for name in event_names}
    return FakeAircraftEvents(catalog)


# ── A-DISP-1: dispatcher tests ──────────────────────────────────


class TestADISP1Dispatcher:
    """A-DISP-1: SimConnect event dispatch via find() + SDK-only fallback."""

    def test_catalogued_event_no_param(self):
        """Catalogued event called without parameter."""
        ae = _make_ae_with_catalog(["GEAR_DOWN"])
        ctrl = MSFSControl(ae)
        ctrl._send_event("GEAR_DOWN")
        assert ae._catalog["GEAR_DOWN"].calls == [None]

    def test_catalogued_event_with_param(self):
        """Catalogued event called with value."""
        ae = _make_ae_with_catalog(["THROTTLE_SET"])
        ctrl = MSFSControl(ae)
        ctrl._send_event("THROTTLE_SET", 8192)
        assert ae._catalog["THROTTLE_SET"].calls == [8192]

    def test_explicit_zero_not_noarg(self):
        """Explicit parameter 0 does not become no-arg call."""
        ae = _make_ae_with_catalog(["FLAPS_UP"])
        ctrl = MSFSControl(ae)
        ctrl._send_event("FLAPS_UP", 0)
        assert ae._catalog["FLAPS_UP"].calls == [0]

    def test_unknown_non_allowlisted_raises(self):
        """Unknown event not in allowlist → ValueError, no low-level call."""
        ae = FakeAircraftEvents({})
        ctrl = MSFSControl(ae)
        with pytest.raises(ValueError, match="Unknown SimConnect event"):
            ctrl._send_event("TYPO_EVENT")
        assert ae.sm.send_event.called is False

    def test_non_callable_find_result(self):
        """find() returns non-callable → TypeError."""
        ae = FakeAircraftEvents({"BROKEN": "not_callable"})
        ctrl = MSFSControl(ae)
        with pytest.raises(TypeError, match="is not callable"):
            ctrl._send_event("BROKEN")

    def test_sdk_only_event_creates_and_calls(self):
        """AP_VS_ON: find() returns None, Event created, called."""
        ae = FakeAircraftEvents({})
        ctrl = MSFSControl(ae)
        ctrl._send_event("AP_VS_ON")
        # Event was created and cached
        assert "AP_VS_ON" in ctrl._dynamic_events
        # Event constructor was called with correct bytes
        event = ctrl._dynamic_events["AP_VS_ON"]
        assert event.deff == b"AP_VS_ON"

    def test_sdk_only_event_cached(self):
        """SDK-only event: second call reuses cached Event."""
        ae = FakeAircraftEvents({})
        ctrl = MSFSControl(ae)
        ctrl._send_event("AP_VS_ON")
        first_event = ctrl._dynamic_events["AP_VS_ON"]
        ctrl._send_event("AP_VS_ON")
        assert ctrl._dynamic_events["AP_VS_ON"] is first_event

    def test_sdk_only_no_sm_raises(self):
        """SDK-only fallback without ae.sm → RuntimeError."""
        ae = FakeAircraftEvents({})
        ae.sm = None
        ctrl = MSFSControl(ae)
        with pytest.raises(RuntimeError, match="AircraftEvents.sm unavailable"):
            ctrl._send_event("AP_VS_ON")

    def test_no_test_depends_on_event_method(self):
        """Verify FakeAircraftEvents does not have .event() method."""
        ae = FakeAircraftEvents({})
        assert not hasattr(ae, "event") or not callable(getattr(ae, "event", None))


# ── A-CONF-1: flaps discrete events ─────────────────────────────


class TestACONF1Flaps:
    """A-CONF-1: Flaps set via discrete events, not FLAPS_SET."""

    @pytest.mark.parametrize("position,event_name", [
        (0, "FLAPS_UP"),
        (1, "FLAPS_1"),
        (2, "FLAPS_2"),
        (3, "FLAPS_3"),
    ])
    def test_discrete_event_mapping(self, position, event_name):
        ae = _make_ae_with_catalog(["FLAPS_UP", "FLAPS_1", "FLAPS_2", "FLAPS_3"])
        ctrl = MSFSControl(ae)
        ctrl.set_flaps(position)
        assert ae._catalog[event_name].calls == [None]
        assert ae.find_calls[-1] == event_name

    def test_flaps_no_param(self):
        """Flaps events are called without parameter."""
        ae = _make_ae_with_catalog(["FLAPS_UP", "FLAPS_1", "FLAPS_2", "FLAPS_3"])
        ctrl = MSFSControl(ae)
        ctrl.set_flaps(2)
        assert ae._catalog["FLAPS_2"].calls == [None]

    def test_flaps_clamp_below(self):
        """Position < 0 clamps to 0 (FLAPS_UP)."""
        ae = _make_ae_with_catalog(["FLAPS_UP", "FLAPS_1", "FLAPS_2", "FLAPS_3"])
        ctrl = MSFSControl(ae)
        ctrl.set_flaps(-1)
        assert ae._catalog["FLAPS_UP"].calls == [None]

    def test_flaps_clamp_above(self):
        """Position > 3 clamps to 3 (FLAPS_3)."""
        ae = _make_ae_with_catalog(["FLAPS_UP", "FLAPS_1", "FLAPS_2", "FLAPS_3"])
        ctrl = MSFSControl(ae)
        ctrl.set_flaps(99)
        assert ae._catalog["FLAPS_3"].calls == [None]

    def test_flaps_set_not_called(self):
        """FLAPS_SET must NOT be called."""
        ae = _make_ae_with_catalog(["FLAPS_UP", "FLAPS_1", "FLAPS_2", "FLAPS_3", "FLAPS_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_flaps(2)
        assert ae._catalog["FLAPS_SET"].calls == []


# ── A-CONF-4: deterministic VS ──────────────────────────────────


class TestACONF4VerticalSpeed:
    """A-CONF-4: AP_VS_ON (deterministic), not AP_VS_HOLD (toggle)."""

    def test_vs_uses_ap_vs_on(self):
        """set_vertical_speed calls AP_VS_ON, not AP_VS_HOLD."""
        ae = _make_ae_with_catalog(["AP_VS_ON", "AP_VS_VAR_SET_ENGLISH"])
        ctrl = MSFSControl(ae)
        ctrl.set_vertical_speed(1500)
        assert ae._catalog["AP_VS_ON"].calls == [None]
        assert ae._catalog["AP_VS_VAR_SET_ENGLISH"].calls == [1500]

    def test_vs_order_on_before_var(self):
        """AP_VS_ON is called before AP_VS_VAR_SET_ENGLISH."""
        ae = _make_ae_with_catalog(["AP_VS_ON", "AP_VS_VAR_SET_ENGLISH"])
        ctrl = MSFSControl(ae)
        ctrl.set_vertical_speed(1500)
        # find() order confirms AP_VS_ON resolved first
        assert ae.find_calls[0] == "AP_VS_ON"
        assert ae.find_calls[1] == "AP_VS_VAR_SET_ENGLISH"

    def test_vs_hold_not_called(self):
        """AP_VS_HOLD must NOT be called."""
        ae = _make_ae_with_catalog(["AP_VS_ON", "AP_VS_VAR_SET_ENGLISH", "AP_VS_HOLD"])
        ctrl = MSFSControl(ae)
        ctrl.set_vertical_speed(1500)
        assert ae._catalog["AP_VS_HOLD"].calls == []


# ── B-AT-1: continuous flaps fraction ───────────────────────────


class TestBAT1Autothrottle:
    """B-AT-1: Continuous flaps fraction, no quantization."""

    def test_calibration_half(self):
        """flaps 0.5 → drag 0.30 (matches old round(2)×0.15)."""
        ctrl = AutothrottleController()
        result = ctrl.calculate_base_throttle(
            aircraft_weight=5000.0, flaps_fraction=0.5, gear_down=False
        )
        assert abs(result - (0.5 + 0.3)) < 1e-9

    def test_calibration_zero(self):
        """flaps 0.0 → drag 0.0."""
        ctrl = AutothrottleController()
        result = ctrl.calculate_base_throttle(
            aircraft_weight=5000.0, flaps_fraction=0.0, gear_down=False
        )
        assert abs(result - 0.5) < 1e-9

    def test_calibration_linearity(self):
        """flaps_fraction × flaps_drag_full_deployment is linear (no steps)."""
        ctrl = AutothrottleController()
        # Use 0.8 to stay under 1.0 clamp (0.5 + 0.8×0.6 = 0.98)
        result = ctrl.calculate_base_throttle(
            aircraft_weight=5000.0, flaps_fraction=0.8, gear_down=False
        )
        assert abs(result - (0.5 + 0.8 * 0.6)) < 1e-9

    def test_clamp_above(self):
        """flaps > 1.0 clamps to 1.0, result clamped to max_throttle."""
        ctrl = AutothrottleController()
        result = ctrl.calculate_base_throttle(
            aircraft_weight=5000.0, flaps_fraction=2.0, gear_down=False
        )
        # 0.5 + 1.0*0.6 = 1.1 → clamped to 1.0
        assert abs(result - 1.0) < 1e-9

    def test_clamp_below(self):
        """flaps < 0.0 clamps to 0.0."""
        ctrl = AutothrottleController()
        result = ctrl.calculate_base_throttle(
            aircraft_weight=5000.0, flaps_fraction=-0.5, gear_down=False
        )
        assert abs(result - 0.5) < 1e-9

    def test_intermediate_linear(self):
        """Intermediate values are linear (no step quantization)."""
        ctrl = AutothrottleController()
        r0 = ctrl.calculate_base_throttle(5000.0, 0.0, False)
        r_half = ctrl.calculate_base_throttle(5000.0, 0.5, False)
        # Linear: 0.5 should be r0 + 0.5 * drag_full = 0.5 + 0.3 = 0.8
        expected_half = r0 + 0.5 * 0.6
        assert abs(r_half - expected_half) < 1e-9

    def test_no_quantization_in_calculate_throttle(self):
        """calculate_throttle passes raw fraction, not int(round(*4))."""
        ctrl = AutothrottleController()
        ctrl.activate()
        # Monkey-patch calculate_base_throttle to capture args
        captured = {}
        original = ctrl.calculate_base_throttle

        def spy(aircraft_weight, flaps_fraction, gear_down):
            captured["flaps_fraction"] = flaps_fraction
            return original(aircraft_weight, flaps_fraction, gear_down)

        ctrl.calculate_base_throttle = spy

        telemetry = {
            "speed": {"airspeed_indicated": 140.0},
            "attitude": {"bank": 0},
            "configuration": {"flaps_position": 0.37, "gear_position": 1.0},
        }
        ctrl.calculate_throttle(telemetry, target_speed=140.0, wind_data={})
        # Must be 0.37, not int(round(0.37*4))=1
        assert captured["flaps_fraction"] == 0.37

    def test_config_field_renamed(self):
        """AutothrottleConfig uses flaps_drag_full_deployment, not flaps_drag_factor."""
        config = AutothrottleConfig()
        assert hasattr(config, "flaps_drag_full_deployment")
        assert not hasattr(config, "flaps_drag_factor")
        assert config.flaps_drag_full_deployment == 0.6


# ── Contract test against installed SimConnect library ───────────


class TestSimConnectContract:
    """Verify static API shape of installed SimConnect v0.4.26.

    In test environment, AircraftEvents is mocked by conftest.
    These tests verify the real API only when SimConnect is installed.
    """

    def test_event_import_path(self):
        from SimConnect.EventList import Event
        assert Event is not None

    def test_sdk_only_events_defined(self):
        """SDK_ONLY_EVENTS contains exactly the 3 confirmed SDK-only names."""
        from modules.control import SDK_ONLY_EVENTS
        assert SDK_ONLY_EVENTS == frozenset({
            "AP_VS_ON", "NAV1_RADIO_SET_HZ", "NAV2_RADIO_SET_HZ",
        })
