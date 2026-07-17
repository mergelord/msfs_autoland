"""
Tests for P1 safety fixes: A-CONF-2 and A-CONF-3.

A-CONF-2: Throttle clamp to SDK max 16383
A-CONF-3: Rudder/aileron clamp to SDK range ±16383
"""

import pytest

from modules.control import MSFSControl, AXIS_ABS_MAX
from tests.test_p0_aconf1_aconf4_bat1 import (
    _make_ae_with_catalog,
)


# ── A-CONF-2: throttle clamp ─────────────────────────────────────


class TestACONF2ThrottleClamp:
    """A-CONF-2: THROTTLE_SET max 16383, not 16384."""

    def test_throttle_at_max(self):
        """set_throttle(1.0) → exactly 16383."""
        ae = _make_ae_with_catalog(["THROTTLE_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_throttle(1.0)
        assert ae._catalog["THROTTLE_SET"].calls == [16383]

    def test_throttle_at_zero(self):
        """set_throttle(0.0) → 0 (unchanged)."""
        ae = _make_ae_with_catalog(["THROTTLE_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_throttle(0.0)
        assert ae._catalog["THROTTLE_SET"].calls == [0]

    def test_throttle_intermediate(self):
        """set_throttle(0.5) → 8192 (unchanged intermediate)."""
        ae = _make_ae_with_catalog(["THROTTLE_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_throttle(0.5)
        assert ae._catalog["THROTTLE_SET"].calls == [8192]

    def test_throttle_over_max_input(self):
        """set_throttle(1.5) → input clamped to 1.0 → 16383."""
        ae = _make_ae_with_catalog(["THROTTLE_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_throttle(1.5)
        assert ae._catalog["THROTTLE_SET"].calls == [16383]

    @pytest.mark.parametrize("engine_index,event_name", [
        (1, "THROTTLE1_SET"),
        (2, "THROTTLE2_SET"),
        (3, "THROTTLE3_SET"),
        (4, "THROTTLE4_SET"),
    ])
    def test_throttle_engine_at_max(self, engine_index, event_name):
        """set_throttle_engine(i, 1.0) → 16383 for each engine."""
        ae = _make_ae_with_catalog([event_name])
        ctrl = MSFSControl(ae)
        ctrl.set_throttle_engine(engine_index, 1.0)
        assert ae._catalog[event_name].calls == [16383]

    def test_throttle_asymmetric_at_max(self):
        """set_throttle_asymmetric with 1.0 → 16383 for each engine."""
        ae = _make_ae_with_catalog([
            "THROTTLE1_SET", "THROTTLE2_SET",
            "THROTTLE3_SET", "THROTTLE4_SET",
        ])
        ctrl = MSFSControl(ae)
        ctrl.set_throttle_asymmetric({1: 1.0, 2: 0.5, 3: 1.0, 4: 0.0})
        assert ae._catalog["THROTTLE1_SET"].calls == [16383]
        assert ae._catalog["THROTTLE2_SET"].calls == [8192]
        assert ae._catalog["THROTTLE3_SET"].calls == [16383]
        assert ae._catalog["THROTTLE4_SET"].calls == [0]


# ── A-CONF-3: rudder/aileron clamp ──────────────────────────────


class TestACONF3RudderClamp:
    """A-CONF-3: RUDDER_SET range ±16383."""

    def test_rudder_positive_max(self):
        """set_rudder(+1.0) → +16383."""
        ae = _make_ae_with_catalog(["RUDDER_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_rudder(1.0)
        assert ae._catalog["RUDDER_SET"].calls == [16383]

    def test_rudder_negative_max(self):
        """set_rudder(-1.0) → -16383."""
        ae = _make_ae_with_catalog(["RUDDER_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_rudder(-1.0)
        assert ae._catalog["RUDDER_SET"].calls == [-16383]

    def test_rudder_zero(self):
        """set_rudder(0.0) → 0 (unchanged)."""
        ae = _make_ae_with_catalog(["RUDDER_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_rudder(0.0)
        assert ae._catalog["RUDDER_SET"].calls == [0]

    def test_rudder_intermediate(self):
        """set_rudder(0.5) → 8192 (unchanged intermediate)."""
        ae = _make_ae_with_catalog(["RUDDER_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_rudder(0.5)
        assert ae._catalog["RUDDER_SET"].calls == [8192]

    def test_rudder_negative_overmax(self):
        """set_rudder(-2.0) → input clamped to -1.0 → -16383."""
        ae = _make_ae_with_catalog(["RUDDER_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_rudder(-2.0)
        assert ae._catalog["RUDDER_SET"].calls == [-16383]


class TestACONF3AileronClamp:
    """A-CONF-3: AILERON_SET range ±16383."""

    def test_aileron_positive_max(self):
        """set_aileron(+1.0) → +16383."""
        ae = _make_ae_with_catalog(["AILERON_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_aileron(1.0)
        assert ae._catalog["AILERON_SET"].calls == [16383]

    def test_aileron_negative_max(self):
        """set_aileron(-1.0) → -16383."""
        ae = _make_ae_with_catalog(["AILERON_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_aileron(-1.0)
        assert ae._catalog["AILERON_SET"].calls == [-16383]

    def test_aileron_overmax(self):
        """set_aileron(+2.0) → input clamped to +1.0 → +16383."""
        ae = _make_ae_with_catalog(["AILERON_SET"])
        ctrl = MSFSControl(ae)
        ctrl.set_aileron(2.0)
        assert ae._catalog["AILERON_SET"].calls == [16383]


# ── Contract: AXIS_ABS_MAX constant ──────────────────────────────


class TestAXISAbsMax:
    """Verify AXIS_ABS_MAX matches SDK limit."""

    def test_constant_value(self):
        assert AXIS_ABS_MAX == 16383
