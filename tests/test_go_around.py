"""Tests for abort_approach_critical — unified critical abort handler.

Replaces old execute_go_around tests. abort_approach_critical must NOT
send any actuator commands (AP, axes, throttle, flaps, gear, heading,
altitude, speed). It only: logs CRITICAL, plays audio alert, deactivates
our autothrottle, centers vJoy, and calls stop_approach.
"""
from unittest.mock import MagicMock, patch
from tests.fakes import FakeControl


class TestAbortApproachCritical:
    def test_abort_logs_critical_with_reason(self):
        """abort_approach_critical must log CRITICAL with the reason string."""
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = False
        system.use_vjoy = False
        system.virtual_joystick = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.audio_system = MagicMock()
        system.audio_system.is_available.return_value = False

        with patch('main.logger') as mock_logger:
            system.abort_approach_critical("test reason")
            mock_logger.critical.assert_called_with(
                "APPROACH ABORTED: %s", "test reason"
            )

    def test_abort_calls_stop_approach(self):
        """abort_approach_critical must call stop_approach()."""
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = False
        system.use_vjoy = False
        system.virtual_joystick = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.audio_system = MagicMock()
        system.audio_system.is_available.return_value = False

        with patch.object(system, 'stop_approach') as mock_stop:
            system.abort_approach_critical("test")
            mock_stop.assert_called_once()

    def test_abort_deactivates_our_autothrottle(self):
        """abort_approach_critical must deactivate our autothrottle if active."""
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = True
        system.use_vjoy = False
        system.virtual_joystick = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.audio_system = MagicMock()
        system.audio_system.is_available.return_value = False

        with patch.object(system, 'stop_approach'):
            system.abort_approach_critical("test")
            system.autothrottle.deactivate.assert_called_once()

    def test_abort_centers_vjoy(self):
        """abort_approach_critical must center vJoy axes when vJoy is used."""
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = False
        system.use_vjoy = True
        system.virtual_joystick = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.audio_system = MagicMock()
        system.audio_system.is_available.return_value = False

        with patch.object(system, 'stop_approach'):
            system.abort_approach_critical("test")
            system.virtual_joystick.center_all_axes.assert_called_once()

    def test_abort_sends_no_actuator_commands(self):
        """abort_approach_critical must NOT send any actuator commands.

        No AP, no axes, no throttle, no flaps, no gear, no heading,
        no altitude, no speed commands.
        """
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = False
        system.use_vjoy = False
        system.virtual_joystick = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.audio_system = MagicMock()
        system.audio_system.is_available.return_value = False

        with patch.object(system, 'stop_approach'):
            system.abort_approach_critical("test")

        ctrl = system.control
        assert not ctrl.has_call('set_autopilot_master'), \
            "abort must NOT send AP master"
        assert not ctrl.has_call('set_heading_hold'), \
            "abort must NOT send heading hold"
        assert not ctrl.has_call('set_vertical_speed'), \
            "abort must NOT send vertical speed"
        assert not ctrl.has_call('set_throttle'), \
            "abort must NOT send throttle"
        assert not ctrl.has_call('set_flaps'), \
            "abort must NOT send flaps"
        assert not ctrl.has_call('set_gear'), \
            "abort must NOT send gear"
        assert not ctrl.has_call('set_airspeed_hold'), \
            "abort must NOT send airspeed hold"


class TestErrorBudgetF4:
    def test_error_budget_abort_after_takeover(self):
        """3 errors + takeover.completed → abort_approach_critical."""
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = False
        system.use_vjoy = False
        system.vjoy_throttle = None
        system.virtual_joystick = MagicMock()
        system.stabilized_monitor = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.autopilot_takeover = MagicMock()
        system.autopilot_takeover.status.completed = True
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.running = True
        system.connection_monitor = None
        system.connection_optimizer = None
        system.audio_alerts_enabled = False
        system.audio_system = None
        system._last_guard_decision = None
        system._last_guard_reason = None
        system._last_fms_log_time = 0
        system._last_guard_snapshot_log_time = 0
        system.fms_reader = None
        system.safety_guard = None
        system.approach_config = MagicMock()
        system.approach_config.approach_speed = 120
        system.approach_config.station = MagicMock()
        system.approach_config.station.type = 'VOR'

        # Force 3 consecutive errors
        system.telemetry = MagicMock()
        system.telemetry.get_all_data.side_effect = SimulatedError("test")

        with patch.object(system, 'abort_approach_critical') as mock_abort:
            system.execute_approach()
            mock_abort.assert_called_once()

    def test_error_budget_abort_before_takeover(self):
        """3 errors + takeover NOT completed → abort_approach_critical (unified)."""
        from main import AutoLandSystem
        system = AutoLandSystem.__new__(AutoLandSystem)
        system.control = FakeControl()
        system.autothrottle = MagicMock()
        system.autothrottle.active = False
        system.use_vjoy = False
        system.vjoy_throttle = None
        system.virtual_joystick = MagicMock()
        system.stabilized_monitor = MagicMock()
        system.telemetry_recorder = MagicMock()
        system.autopilot_takeover = MagicMock()
        system.autopilot_takeover.status.completed = False
        system.phase = MagicMock()
        system.phase.value = 'FINAL'
        system.running = True
        system.connection_monitor = None
        system.connection_optimizer = None
        system.audio_alerts_enabled = False
        system.audio_system = None
        system._last_guard_decision = None
        system._last_guard_reason = None
        system._last_fms_log_time = 0
        system._last_guard_snapshot_log_time = 0
        system.fms_reader = None
        system.safety_guard = None
        system.approach_config = MagicMock()
        system.approach_config.approach_speed = 120
        system.approach_config.station = MagicMock()
        system.approach_config.station.type = 'VOR'

        system.telemetry = MagicMock()
        system.telemetry.get_all_data.side_effect = SimulatedError("test")

        with patch.object(system, 'abort_approach_critical') as mock_abort:
            system.execute_approach()
            mock_abort.assert_called_once()


class SimulatedError(Exception):
    pass
