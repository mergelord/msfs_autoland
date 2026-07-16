"""TEST-CG-02 Stage 1: Observability + explicit nominal scoping."""
import logging
import threading

import pytest
from modules.command_gateway import CommandGateway, CommandRejected, CommandSource
from modules.control_ownership import ControlOwner, ControlOwnership


# ---------------------------------------------------------------------------
# Fake control + ownership
# ---------------------------------------------------------------------------

class FakeControl:
    def __init__(self):
        self.calls = []
    def set_throttle(self, v):
        self.calls.append(("set_throttle", v))
    def set_vertical_speed(self, v):
        self.calls.append(("set_vertical_speed", v))
    def set_heading_hold(self, v):
        self.calls.append(("set_heading_hold", v))
    def set_flaps(self, v):
        self.calls.append(("set_flaps", v))

def ap_owner():
    return ControlOwnership(ControlOwner.AIRCRAFT_AP, ControlOwner.AIRCRAFT_AP, ControlOwner.AIRCRAFT_AP)

def external_owner():
    return ControlOwnership(ControlOwner.EXTERNAL, ControlOwner.EXTERNAL, ControlOwner.EXTERNAL)


# ---------------------------------------------------------------------------
# 1. Unscoped call → still authorized as AP, WARNING emitted
# ---------------------------------------------------------------------------

def test_unscoped_call_authorized_as_ap_with_warning(caplog):
    """Unscoped call is allowed under AP ownership but emits warning."""
    raw = FakeControl()
    gw = CommandGateway(raw, ap_owner)

    import modules.command_gateway as cg_mod
    with caplog.at_level(logging.WARNING, logger=cg_mod.logger.name):
        gw.set_throttle(0.5)

    assert raw.calls == [("set_throttle", 0.5)]
    assert any("unscoped" in r.message.lower() or "implicit" in r.message.lower()
               for r in caplog.records if r.levelno >= logging.WARNING)


# ---------------------------------------------------------------------------
# 2. Warning emitted once per method name
# ---------------------------------------------------------------------------

def test_warning_once_per_method_name(caplog):
    """Two unscoped calls to same method → one warning. Different method → new warning."""
    raw = FakeControl()
    gw = CommandGateway(raw, ap_owner)

    import modules.command_gateway as cg_mod
    with caplog.at_level(logging.WARNING, logger=cg_mod.logger.name):
        gw.set_throttle(0.5)
        gw.set_throttle(0.7)
        gw.set_vertical_speed(1500)

    assert len(raw.calls) == 3
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING
                and ("unscoped" in r.message.lower() or "implicit" in r.message.lower())]
    # Should have exactly 2 warnings: one for set_throttle, one for set_vertical_speed
    assert len(warnings) == 2


# ---------------------------------------------------------------------------
# 3. Explicitly scoped AIRCRAFT_AP call → NO warning
# ---------------------------------------------------------------------------

def test_explicit_scope_no_warning(caplog):
    """Explicit source_scope(AIRCRAFT_AP) produces no warning."""
    raw = FakeControl()
    gw = CommandGateway(raw, ap_owner)

    import modules.command_gateway as cg_mod
    with caplog.at_level(logging.WARNING, logger=cg_mod.logger.name):
        with gw.source_scope(CommandSource.AIRCRAFT_AP):
            gw.set_throttle(0.5)

    assert raw.calls == [("set_throttle", 0.5)]
    assert not any("unscoped" in r.message.lower() or "implicit" in r.message.lower()
                   for r in caplog.records if r.levelno >= logging.WARNING)


# ---------------------------------------------------------------------------
# 4. SAFETY scope → bypass, no warning
# ---------------------------------------------------------------------------

def test_safety_scope_no_warning(caplog):
    """SAFETY scope allows commands and produces no unscoped warning."""
    raw = FakeControl()
    gw = CommandGateway(raw, external_owner)  # EXTERNAL owner

    import modules.command_gateway as cg_mod
    with caplog.at_level(logging.WARNING, logger=cg_mod.logger.name):
        with gw.source_scope(CommandSource.SAFETY):
            gw.set_throttle(1.0)

    assert raw.calls == [("set_throttle", 1.0)]
    assert not any("unscoped" in r.message.lower() or "implicit" in r.message.lower()
                   for r in caplog.records if r.levelno >= logging.WARNING)


# ---------------------------------------------------------------------------
# 5. EXTERNAL unscoped-owner rejection unchanged
# ---------------------------------------------------------------------------

def test_external_unscoped_rejection_unchanged():
    """EXTERNAL owner + unscoped actuator → CommandRejected (fail-closed as before)."""
    raw = FakeControl()
    gw = CommandGateway(raw, external_owner)

    with pytest.raises(CommandRejected):
        gw.set_throttle(0.5)


# ---------------------------------------------------------------------------
# 6. After source_scope exits, unscoped call maps None → AP
# ---------------------------------------------------------------------------

def test_scope_exit_restores_none_default(caplog):
    """After source_scope exits, unscoped call sees None default → maps to AP."""
    raw = FakeControl()
    gw = CommandGateway(raw, ap_owner)

    import modules.command_gateway as cg_mod
    with caplog.at_level(logging.WARNING, logger=cg_mod.logger.name):
        with gw.source_scope(CommandSource.EXTERNAL):
            # Inside EXTERNAL scope — rejected for AP owner
            pass
        # After scope exit — unscoped call, None → AP
        gw.set_throttle(0.5)

    assert raw.calls == [("set_throttle", 0.5)]


# ---------------------------------------------------------------------------
# 7. Thread isolation: new thread sees None default
# ---------------------------------------------------------------------------

def test_thread_isolation_sees_none_default(caplog):
    """Fresh thread while main context is inside source_scope sees None default."""
    raw = FakeControl()
    gw = CommandGateway(raw, ap_owner)

    thread_warnings = []
    import modules.command_gateway as cg_mod

    def thread_fn():
        with caplog.at_level(logging.WARNING, logger=cg_mod.logger.name):
            gw.set_vertical_speed(1500)
        thread_warnings.extend(
            r for r in caplog.records
            if r.levelno >= logging.WARNING
            and ("unscoped" in r.message.lower() or "implicit" in r.message.lower())
        )

    with gw.source_scope(CommandSource.AIRCRAFT_AP):
        t = threading.Thread(target=thread_fn)
        t.start()
        t.join()

    # Thread sees None default → warning fires
    assert len(thread_warnings) >= 1


# ---------------------------------------------------------------------------
# 8. Unscoped-call counter/accessor
# ---------------------------------------------------------------------------

def test_unscoped_call_counter():
    """Unscoped call counter tracks observed method names."""
    raw = FakeControl()
    gw = CommandGateway(raw, ap_owner)

    gw.set_throttle(0.5)
    gw.set_throttle(0.7)
    gw.set_vertical_speed(1500)

    # Access the counter
    names = gw.unscoped_call_names
    assert "set_throttle" in names
    assert "set_vertical_speed" in names
    assert len(names) == 2  # unique names only
