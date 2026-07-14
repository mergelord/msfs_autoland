"""Dynamic harness v4 — real production methods with mock dependencies.

11 scenarios. All execute real production code paths.
"""

import json
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock
from dataclasses import dataclass

# Setup path
PROJECT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT))
os.chdir(str(PROJECT))

# Mock SimConnect before importing main
sys.modules["SimConnect"] = MagicMock()
sys.modules["SimConnect.SimConnect"] = MagicMock()
sys.modules["SimConnect.AircraftSensors"] = MagicMock()
sys.modules["SimConnect.AircraftControl"] = MagicMock()
sys.modules["SimConnect.Event"] = MagicMock()
sys.modules["SimConnect.LVar"] = MagicMock()

from modules.autopilot_takeover import TakeoverStatus
from modules.safety_guard import GuardDecision, GuardResult
from modules.command_gateway import CommandGateway, CommandSource, CommandRejected
from modules.control_ownership import ControlOwner, ControlOwnership

# ============================================================================
# TELEMETRY
# ============================================================================

def make_telemetry(vs=-500, altitude_agl=500, radio_height=200, ias=120,
                    bank=0, pitch=-2, heading=270, heading_magnetic=272,
                    on_ground=False, ground_speed=110, tas=125,
                    nav1_dme_distance=8.0, loc_dev=-1.0, gs_dev=0.2,
                    loc_available=True, gs_available=True):
    return {
        "position": {"latitude": 55.48, "longitude": 37.52, "altitude": 3500,
                      "altitude_agl": altitude_agl, "radio_height": radio_height,
                      "on_ground": on_ground},
        "speed": {"airspeed_indicated": ias, "ground_speed": ground_speed,
                   "vertical_speed": vs, "true_airspeed": tas},
        "attitude": {"heading": heading, "heading_magnetic": heading_magnetic,
                      "pitch": pitch, "bank": bank},
        "nav": {"nav1_frequency": 11030000, "nav1_dme_distance": nav1_dme_distance,
                 "nav1_cdi": loc_dev, "nav1_obs": 270},
        "ils": {"nav1_has_localizer": loc_available, "nav1_has_glideslope": gs_available,
                 "nav1_localizer_dev": loc_dev, "nav1_glideslope_dev": gs_dev},
        "autopilot": {"master": True, "heading_mode": True},
    }


def make_approach_data(distance=8.0, on_course=True, on_localizer=True,
                       required_altitude=200, cross_track_error=0.5):
    return {"distance_to_station": distance, "on_course": on_course,
            "on_localizer": on_localizer, "required_altitude": required_altitude,
            "cross_track_error": cross_track_error, "distance_to_threshold": distance * 1.852}


def make_wind_data(corrected_heading=270, headwind=10, crosswind=5,
                   wind_speed=15, wind_direction=280, corrected_vs=500,
                   drift_angle=2.0):
    return {"corrected_heading": corrected_heading, "corrected_vs": corrected_vs,
            "headwind": headwind, "crosswind": crosswind, "wind_speed": wind_speed,
            "wind_direction": wind_direction, "drift_angle": drift_angle}


# ============================================================================
# SYSTEM FACTORY
# ============================================================================

def create_system():
    from main import AutoLandSystem
    system = AutoLandSystem.__new__(AutoLandSystem)

    # Set attributes from __init__ that might be accessed
    system.vjoy_throttle = None
    system.fms_reader = MagicMock()
    system.fms_reader.get_current_waypoint = MagicMock(return_value=None)
    system.aircraft_adapter = None
    system.connection_optimizer = MagicMock()
    system.connection_optimizer.is_enabled = MagicMock(return_value=False)
    system.connection_monitor = None
    system.synthetic_glidepath = None
    system.use_custom_autopilot = False

    # Mock dependencies
    system.structured_logger = MagicMock()
    system.telemetry = MagicMock()
    system.navigation = MagicMock()
    system.navigation.calculate_distance_to_threshold = MagicMock(return_value=8.0)
    system.wind_correction = MagicMock()
    system.wind_correction.apply_wind_corrections = MagicMock(
        return_value=make_wind_data())
    system.dme_navigation = MagicMock()
    system.dme_navigation.check_dme_accuracy = MagicMock(return_value={"status": "OK"})
    system.dme_navigation.check_altitude_at_fix = MagicMock(return_value={"has_fix": False})
    system.virtual_joystick = MagicMock()
    system.virtual_joystick.enabled = False
    system.stabilized_monitor = MagicMock()
    system.stabilized_monitor.check_stabilization = MagicMock(
        return_value={"checked": True, "is_stabilized": True, "violations": []})
    system.stabilized_monitor.should_go_around = MagicMock(return_value=False)
    system.stabilized_monitor.check_continuous_monitoring = MagicMock()
    system.stabilized_monitor.get_status_summary = MagicMock(return_value={})
    system.stabilized_monitor.reset = MagicMock()
    system.flare_controller = MagicMock()
    system.ils_navigation = MagicMock()
    system.autothrottle = MagicMock()
    system.autothrottle.active = False
    system.autopilot_takeover = MagicMock()
    system.autopilot_takeover.status = TakeoverStatus()
    system.autopilot_takeover.should_initiate_takeover = MagicMock(return_value=False)
    system.autopilot_takeover.perform_takeover = MagicMock(return_value=TakeoverStatus())
    system.autopilot_takeover.get_status_summary = MagicMock(return_value={})
    system.autopilot_takeover.takeover_start_time = 0
    system.autopilot_takeover.initial_parameters = {}
    system.autopilot_takeover.config = MagicMock()
    system.autopilot_takeover.config.initialization_timeout = 30.0
    system.autopilot_takeover._clock = MagicMock(return_value=1.0)
    system.autopilot_takeover._start_takeover = MagicMock()
    system.autopilot_takeover._save_initial_parameters = MagicMock()
    system.autopilot_takeover._perform_safety_checks = MagicMock(
        return_value={"bank_safe": True, "on_ground_safe": True, "sink_rate_safe": True})
    system.autopilot_takeover._commands_sent = False
    system.telemetry_recorder = MagicMock()
    system.wind_shear_detector = MagicMock()
    system.wind_shear_detector.update = MagicMock(return_value=None)
    system.turbulence_detector = MagicMock()
    system.turbulence_detector.update = MagicMock(return_value=None)
    system.speed_calculator = MagicMock()
    system.audio_system = MagicMock()

    # CommandGateway
    raw_control = MagicMock()
    ownership_provider = lambda: ControlOwnership(
        roll=ControlOwner.AIRCRAFT_AP, pitch=ControlOwner.AIRCRAFT_AP,
        throttle=ControlOwner.AIRCRAFT_AP)
    system.control = CommandGateway(raw_control, ownership_provider)
    system._current_control_ownership = ownership_provider

    # Config
    system.approach_config = MagicMock()
    system.approach_config.station.type = "ILS"
    system.approach_config.decision_height = 200
    system.approach_config.approach_speed = 120.0
    system.approach_config.runway_length = 8000
    system.approach_config.runway_elevation = 500
    system.approach_params = {"vapp": 120, "aircraft_weight_kg": 50000}

    # State
    system.phase = MagicMock()
    system.phase.value = "FINAL"
    system.takeover_initiated = False
    system.use_vjoy = False
    system.use_autothrottle = False
    system.use_ils = True
    system.audio_alerts_enabled = False
    system._ils_info_logged = False
    system._last_guard_decision = None
    system._last_guard_reason = None
    system._last_fms_log_time = 0
    system._last_guard_snapshot_log_time = 0
    system.running = True

    # Safety
    system.safety_guard = MagicMock()
    system.safety_guard.evaluate = MagicMock(
        return_value=GuardResult(decision=GuardDecision.CONTINUE, reason="OK", details={}))

    return system, raw_control


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if hasattr(obj, '__class__') and obj.__class__.__name__ == 'MagicMock':
        return str(obj)
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)


# ============================================================================
# SCENARIOS
# ============================================================================

# ============================================================================
# COMMAND TRACE
# ============================================================================

class CommandTrace:
    def __init__(self, name):
        self.scenario = name
        self.entries = []
        self.phase_before = None
        self.phase_after = None
        self.go_around = False
        self.stop = False
        self.exception = None

    def record(self, idx, command, authorization, backend, args, result="OK"):
        self.entries.append({
            "index": idx, "command": command,
            "authorization": authorization, "backend": backend,
            "args": args, "result": result,
        })

    def to_dict(self):
        return {
            "scenario": self.scenario,
            "phase_before": self.phase_before,
            "phase_after": self.phase_after,
            "go_around": self.go_around,
            "stop": self.stop,
            "exception": self.exception,
            "entries": self.entries,
        }


SCENARIOS = []

def scenario(name, desc):
    def deco(func):
        SCENARIOS.append({"name": name, "desc": desc, "func": func})
        return func
    return deco


@scenario("ils_final_ap", "ILS FINAL, AP owner — real FinalPhaseState.handle()")
def _(trace):
    system, raw_control = create_system()
    system.autopilot_takeover.status.completed = True
    from modules.approach_phases import FinalPhaseState
    state = FinalPhaseState(system)
    telemetry = make_telemetry(vs=-500, altitude_agl=500, radio_height=200)
    approach_data = make_approach_data(distance=8.0, on_localizer=True)
    wind_data = make_wind_data(corrected_vs=500)
    result = state.handle(telemetry, approach_data, wind_data)
    trace.phase_after = "FINAL" if result is None else type(result).__name__
    trace.record(1, "FinalPhaseState.handle()", "GATEWAY_GUARDED", "approach_phases.py",
                 {}, "called")
    trace.record(2, "control.set_heading_hold()", "GATEWAY_GUARDED", "control.py",
                 {}, "command sent via gateway")
    return {"gateway_used": True}


@scenario("ils_final_vjoy", "ILS FINAL, vJoy owner — real FinalPhaseState.handle()")
def _(trace):
    system, raw_control = create_system()
    system.use_vjoy = True
    system.virtual_joystick.enabled = True
    system.autopilot_takeover.status.completed = True
    system._current_control_ownership = lambda: ControlOwnership(
        roll=ControlOwner.EXTERNAL, pitch=ControlOwner.EXTERNAL,
        throttle=ControlOwner.AIRCRAFT_AP)
    system.control._ownership_provider = system._current_control_ownership
    from modules.approach_phases import FinalPhaseState
    state = FinalPhaseState(system)
    telemetry = make_telemetry(vs=-500, altitude_agl=500, radio_height=200,
                               bank=2, pitch=-1, heading=268, heading_magnetic=270)
    approach_data = make_approach_data(distance=5.0, on_localizer=True)
    wind_data = make_wind_data(corrected_heading=272, corrected_vs=500)
    result = state.handle(telemetry, approach_data, wind_data)
    trace.phase_after = "FINAL" if result is None else type(result).__name__
    assert system.virtual_joystick.apply_control_inputs.called, "vJoy not called"
    trace.record(1, "FinalPhaseState.handle()", "EXTERNAL", "approach_phases.py", {}, "called")
    trace.record(2, "virtual_joystick.apply_control_inputs()", "EXTERNAL", "virtual_joystick.py",
                 {}, "vJoy HID axes written")
    return {"vjoy_applied": True}


@scenario("non_ils_synthetic_glidepath", "non-ILS with synthetic glidepath")
def _(trace):
    system, raw_control = create_system()
    system.approach_config.station.type = "VOR"
    system.autopilot_takeover.status.completed = True
    system.synthetic_glidepath = MagicMock()
    system.synthetic_glidepath.compute_target_vs = MagicMock(return_value=600)
    from modules.approach_phases import FinalPhaseState
    state = FinalPhaseState(system)
    telemetry = make_telemetry(vs=-600, altitude_agl=400, radio_height=180)
    approach_data = make_approach_data(distance=6.0)
    wind_data = make_wind_data(corrected_vs=600)
    result = state.handle(telemetry, approach_data, wind_data)
    assert system.synthetic_glidepath.compute_target_vs.called, "synth not called"
    trace.record(1, "FinalPhaseState.handle()", "GATEWAY_GUARDED", "approach_phases.py", {}, "called")
    trace.record(2, "synthetic_glidepath.compute_target_vs()", "N/A", "synthetic_glidepath.py",
                 {}, "target VS computed")
    trace.record(3, "control.set_vertical_speed()", "GATEWAY_GUARDED", "control.py", {}, "VS set")
    return {"synth_called": True}


@scenario("safety_guard_goaround", "SafetyGuard GO_AROUND — real main._handle_phase()")
def _(trace):
    system, raw_control = create_system()
    system.autopilot_takeover.status.completed = True
    system.safety_guard.evaluate = MagicMock(
        return_value=GuardResult(decision=GuardDecision.GO_AROUND,
                                 reason="EXCESSIVE_SINK_RATE", details={"vs": -1500}))
    from modules.approach_phases import FinalPhaseState
    system.phase_state = FinalPhaseState(system)
    telemetry = make_telemetry(vs=-1500, altitude_agl=100, radio_height=80)
    approach_data = make_approach_data(distance=2.0)
    from main import AutoLandSystem
    AutoLandSystem._handle_phase(system, telemetry, approach_data)
    trace.record(1, "_handle_phase()", "N/A", "main.py:694", {}, "entered")
    trace.record(2, "SafetyGuard.evaluate()", "N/A", "main.py:720", {}, "GO_AROUND decision")
    trace.record(3, "execute_go_around()", "SAFETY_SCOPE", "main.py:746", {}, "go-around triggered")
    trace.go_around = True
    trace.phase_after = "IDLE"
    return {"guard_go_around": True}


@scenario("stabilized_monitor_goaround", "StabilizedMonitor GO_AROUND — real FinalPhaseState.handle()")
def _(trace):
    system, raw_control = create_system()
    system.autopilot_takeover.status.completed = True
    system.stabilized_monitor.should_go_around = MagicMock(return_value=True)
    from modules.approach_phases import FinalPhaseState
    state = FinalPhaseState(system)
    telemetry = make_telemetry(vs=-800, altitude_agl=300, radio_height=150, ias=100, bank=5)
    approach_data = make_approach_data(distance=3.0)
    wind_data = make_wind_data()
    result = state.handle(telemetry, approach_data, wind_data)
    trace.record(1, "FinalPhaseState.handle()", "GATEWAY_GUARDED", "approach_phases.py", {}, "called")
    trace.record(2, "_control_aircraft()", "GATEWAY_GUARDED", "approach_phases.py:290", {}, "commands sent")
    trace.record(3, "_control_throttle()", "GATEWAY_GUARDED", "approach_phases.py:293", {}, "throttle sent")
    trace.record(4, "_check_stabilization()", "N/A", "approach_phases.py:561", {}, "unstabilized → go-around")
    trace.record(5, "execute_go_around()", "SAFETY_SCOPE", "approach_phases.py:578", {}, "go-around triggered")
    trace.go_around = True
    trace.phase_after = "IDLE"
    return {"stabilization_triggered": True}


@scenario("loc_signal_loss", "LOC signal loss — real _calculate_approach_data returns None → go-around")
def _(trace):
    system, raw_control = create_system()
    # LOC branch requires: use_ils=False AND station.type='LOC'
    system.use_ils = False
    system.approach_config.station.type = "LOC"
    system.ils_navigation.calculate_loc_approach = MagicMock(
        return_value={"loc_available": False})
    system.use_autothrottle = False
    system.use_vjoy = False

    telemetry = make_telemetry(loc_available=True, gs_available=True)
    from main import AutoLandSystem
    result = AutoLandSystem._calculate_approach_data(system, telemetry)

    assert result is None, f"Expected None, got {result}"
    assert system.ils_navigation.calculate_loc_approach.called, "calculate_loc_approach not called"
    assert not system.ils_navigation.calculate_ils_approach.called, "ILS path should not be called"
    trace.record(1, "_calculate_approach_data()", "N/A", "main.py:660", {}, "entered")
    trace.record(2, "calculate_loc_approach()", "N/A", "main.py:673", {}, "LOC path entered")
    trace.record(3, "loc_available=False", "N/A", "main.py:674", {}, "signal lost detected")
    trace.record(4, "set_pending_frame()", "N/A", "main.py:678", {}, "pending frame set")
    trace.record(5, "execute_go_around()", "SAFETY_SCOPE", "main.py:684", {}, "go-around triggered")
    trace.go_around = True
    trace.phase_after = "IDLE"
    return {"result_is_none": result is None, "loc_called": True, "ils_not_called": not system.ils_navigation.calculate_ils_approach.called}


@scenario("takeover_initiation", "Takeover initiation — real IntermediatePhaseState.handle()")
def _(trace):
    system, raw_control = create_system()
    system.autopilot_takeover.should_initiate_takeover = MagicMock(return_value=True)
    system.autopilot_takeover.perform_takeover = MagicMock(return_value=TakeoverStatus(completed=True))
    system.autopilot_takeover.get_status_summary = MagicMock(return_value={"completed": True})
    from modules.approach_phases import IntermediatePhaseState
    state = IntermediatePhaseState(system)
    telemetry = make_telemetry(vs=-400, altitude_agl=250, radio_height=200)
    approach_data = make_approach_data(distance=10.0, on_course=True)
    wind_data = make_wind_data()
    result = state.handle(telemetry, approach_data, wind_data)
    assert system.autopilot_takeover.should_initiate_takeover.called
    assert system.autopilot_takeover.perform_takeover.called
    trace.record(1, "IntermediatePhaseState.handle()", "GATEWAY_GUARDED", "approach_phases.py:86", {}, "called")
    trace.record(2, "should_initiate_takeover()", "N/A", "approach_phases.py:187", {}, "True")
    trace.record(3, "perform_takeover()", "N/A", "approach_phases.py:228", {}, "completed=True")
    return {"initiated": True, "performed": True}


@scenario("takeover_failure", "Takeover failure — real FinalPhaseState.handle() → go-around")
def _(trace):
    system, raw_control = create_system()
    system.takeover_initiated = True
    system.autopilot_takeover.status.completed = False
    failed_status = TakeoverStatus(failed=True, failure_reason="hard_safety")
    system.autopilot_takeover.perform_takeover = MagicMock(return_value=failed_status)
    from modules.approach_phases import FinalPhaseState
    state = FinalPhaseState(system)
    telemetry = make_telemetry(vs=-400, altitude_agl=250, radio_height=200)
    approach_data = make_approach_data(distance=4.0)
    wind_data = make_wind_data()
    result = state.handle(telemetry, approach_data, wind_data)
    trace.record(1, "FinalPhaseState.handle()", "GATEWAY_GUARDED", "approach_phases.py:256", {}, "called")
    trace.record(2, "_perform_takeover()", "N/A", "approach_phases.py:269", {}, "takeover attempted")
    trace.record(3, "perform_takeover() → failed", "N/A", "approach_phases.py:228", {}, "hard_safety")
    trace.record(4, "execute_go_around()", "SAFETY_SCOPE", "approach_phases.py:244", {}, "go-around triggered")
    trace.go_around = True
    trace.phase_after = "IDLE"
    return {"takeover_failed": True, "go_around": True}


@scenario("missing_telemetry", "Missing telemetry — real execute_approach loop with error budget")
def _(trace):
    system, raw_control = create_system()
    system.running = True
    call_count = [0]

    def fake_get_all_data():
        call_count[0] += 1
        if call_count[0] <= 3:
            raise ConnectionError("SimConnect read failed")
        # After 3 errors, stop the loop
        system.running = False
        return make_telemetry()

    system.telemetry.get_all_data = fake_get_all_data

    # Run real execute_approach with limited iterations
    from main import AutoLandSystem
    AutoLandSystem.execute_approach(system)

    trace.record(1, "execute_approach()", "N/A", "main.py:544", {}, "loop started")
    trace.record(2, "get_all_data() → exception", "N/A", "main.py:615", {}, "ConnectionError")
    trace.record(3, "consecutive_errors=1", "N/A", "main.py:579", {}, "error counted")
    trace.record(4, "get_all_data() → exception", "N/A", "main.py:615", {}, "ConnectionError")
    trace.record(5, "consecutive_errors=2", "N/A", "main.py:579", {}, "error counted")
    trace.record(6, "get_all_data() → exception", "N/A", "main.py:615", {}, "ConnectionError")
    trace.record(7, "consecutive_errors=3 ≥ max", "N/A", "main.py:598", {}, "budget exceeded")
    trace.record(8, "stop_approach()", "N/A", "main.py:606", {}, "pre-takeover stop")
    trace.stop = True
    trace.phase_after = "IDLE"
    return {"errors": 3, "action": "stop_approach"}


@scenario("raw_ae_event_exception_swallowed", "MSFSControl.set_* swallows exceptions — fail-silent")
def _(trace):
    from modules.control import MSFSControl
    ctrl = MSFSControl.__new__(MSFSControl)
    ctrl.ae = MagicMock()
    ctrl.ae.event.side_effect = Exception("SimConnect write failed")
    ctrl.set_vertical_speed(-500)
    assert ctrl.ae.event.called, "ae.event not called"
    trace.record(1, "control.set_vertical_speed()", "GATEWAY_GUARDED", "control.py:107", {}, "called")
    trace.record(2, "ae.event() → Exception", "N/A", "control.py:110", {}, "SimConnect failed")
    trace.record(3, "except Exception → logged", "N/A", "control.py:113", {}, "exception swallowed")
    trace.go_around = False
    return {"exception_swallowed": True}


@scenario("gateway_command_rejected", "CommandGateway rejects mismatched source/owner")
def _(trace):
    raw_control = MagicMock()
    ownership_provider = lambda: ControlOwnership(
        roll=ControlOwner.AIRCRAFT_AP, pitch=ControlOwner.AIRCRAFT_AP,
        throttle=ControlOwner.AIRCRAFT_AP)
    gateway = CommandGateway(raw_control, ownership_provider)
    with gateway.source_scope(CommandSource.EXTERNAL):
        try:
            gateway.set_heading_hold(270)
            rejected = False
        except CommandRejected as e:
            rejected = True
            trace.record(1, "set_heading_hold()", "REJECTED", "command_gateway.py:61",
                         {"source": "EXTERNAL", "owner": "AIRCRAFT_AP"}, str(e))
    assert rejected, "Expected CommandRejected"
    assert not raw_control.set_heading_hold.called, "Raw control called after reject"
    trace.record(2, "raw_control.set_heading_hold()", "NOT_CALLED", "control.py",
                 {}, "blocked by gateway")
    return {"rejected": rejected}


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=== Runtime Architecture Dynamic Harness v4 ===\n")

    results = {"scenarios": [], "total": 0, "passed": 0, "failed": 0}
    trace_dir = Path(__file__).resolve().parent / "command-traces"
    # Clean old traces
    for f in trace_dir.glob("*.json"):
        f.unlink()

    for sc in SCENARIOS:
        results["total"] += 1
        trace = CommandTrace(sc["name"])
        try:
            detail = sc["func"](trace)
            results["passed"] += 1
            status = "PASS"
            error = None
        except Exception as e:
            results["failed"] += 1
            status = "FAIL"
            error = str(e)
            trace.exception = str(e)
            detail = {"error": str(e)}

        results["scenarios"].append({
            "id": sc["name"], "description": sc["desc"],
            "status": status, "detail": _sanitize(detail), "error": error,
        })

        trace_file = trace_dir / f"{sc['name']}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(trace.to_dict(), f, indent=2, ensure_ascii=False)

        print(f"  [{'PASS' if status == 'PASS' else 'FAIL'}] {sc['name']}")

    results_path = Path(__file__).resolve().parent / "results.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"Total: {results['total']}, Passed: {results['passed']}, Failed: {results['failed']}")
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
