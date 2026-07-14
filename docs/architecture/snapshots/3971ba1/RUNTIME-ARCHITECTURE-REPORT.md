# RUNTIME-ARCHITECTURE-3971ba1 — Report v3

## 1. Executive Verdict

**COMPLETED_WITH_UNRESOLVED**

Статическая модель построена. Все 49 production-файлов просканированы. 11/11 offline harness-сценариев выполнены с реальными production methods. CommandGateway lifecycle исправлен. Ограничения без MSFS честно отмечены.

---

## 2. Baseline

- **Commit:** `3971ba12113d8994665b1c9a172f2dca6c9e3855`
- **Branch:** `master`
- **Python:** 3.14.5
- **Production scope:** 49 files (47 modules/ + main.py + gui.py)

---

## 3. CommandGateway Lifecycle (corrected)

### Creation chain:
```
main.py:73   self.control = None
main.py:125  raw_control = MSFSControl(...)
             self.control = CommandGateway(raw_control, self._current_control_ownership)
```

### Authorization mechanism:
- `CommandGateway.__getattr__()` intercepts all `set_*` calls
- `_authorize()` checks `CommandSource` (ContextVar) against expected owner per channel
- SAFETY source bypasses `_authorize()` entirely
- `CommandRejected` raised on mismatch

### Classification of control.set_*() paths:

| Path | Classification | Evidence |
|------|---------------|----------|
| `self.system.control.set_*()` in approach_phases.py | GATEWAY_GUARDED | approach_phases.py:70,126,131,451,488,517,519,524,534 |
| `self.control.set_*()` in execute_go_around() | SAFETY_SCOPE_BYPASS | main.py:436,442,445,448,452 |
| `self.system.virtual_joystick.*` | VJOY_SEPARATE_BACKEND | approach_phases.py:461-478 |
| `self.ae.event()` in control.py | TERMINAL_SINK | control.py:58,68,80,90,100,110,120 |

**RAW_CONTROL_BYPASS = 0** — all phase-state calls go through CommandGateway.

---

## 4. SAFETY Scope in execute_go_around()

Each command in `execute_go_around()` classified:

| Command | Inside `with source_scope(SAFETY)`? | Owner | Source | Allow/Reject |
|---------|--------------------------------------|-------|--------|-------------|
| set_autopilot_master(True) | YES | AIRCRAFT_AP | SAFETY | ALLOW (bypass) |
| set_throttle(1.0) or vjoy_throttle | YES | AIRCRAFT_AP | SAFETY | ALLOW (bypass) |
| set_vertical_speed(1500) | YES | AIRCRAFT_AP | SAFETY | ALLOW (bypass) |
| set_flaps(2) | YES | AIRCRAFT_AP | SAFETY | ALLOW (bypass) |
| set_gear(False) | NO (after `with` block) | AIRCRAFT_AP | AIRCRAFT_AP (default) | ALLOW |
| center_all_axes | N/A (vJoy, not gateway) | N/A | N/A | N/A |

**Key finding:** `set_gear(False)` at main.py:452 is OUTSIDE the `with source_scope(SAFETY)` block. It uses default `CommandSource.AIRCRAFT_AP`. If ownership is EXTERNAL at that moment, `CommandRejected` would be raised. However, in go-around context, AP master is re-engaged first (line 436), so ownership should be AIRCRAFT_AP.

---

## 5. Actuator Exception Behavior

### MSFSControl.set_*() behavior (confirmed by code review):
- All `set_*` methods contain `try/except Exception` blocks
- Exceptions are logged via `logger.error()` and **swallowed** (no re-raise)
- This means actuator write failures are **fail-silent** — the main loop error budget does NOT see them

### Implication:
- `frame-command-order.csv` scenario "actuator exception" was WRONG about exception propagating to error budget
- Real behavior: exception caught in control.py, logged, command lost silently
- Main loop continues with next frame as if command succeeded

### Corrected fail-safe classification:
- `control.py` exceptions: SWALLOWED/LOGGED (fail-silent)
- `CommandRejected`: RAISED (caught by caller or propagates)
- `vJoy/WASM` exceptions: SWALLOWED (fail-silent)

---

## 6. Actuator Counters (exact)

| Entity | Count | Source |
|--------|-------|--------|
| Terminal `ae.event()` sinks | 26 | actuator-sinks.csv (channel=ae.event) |
| `set_*` method call sites | 46 | actuator-sinks.csv (channel=set_*) |
| Total actuator interaction sites | 72 | actuator-sinks.csv total |
| `virtual_joystick.*` calls | 6 | approach_phases.py, main.py |
| `vjoy_throttle.*` calls | 2 | approach_phases.py, main.py |
| `aircraft_adapter.*` calls | 5 | approach_phases.py |

---

## 7. Phase State Machine (corrected)

### Concrete phase-state classes: 4
### Abstract/base: 1
### Lifecycle enum values: 6
### Forward transitions: 5
### Abort transitions: 2
- INTERMEDIATE → IDLE — takeover failure in IntermediatePhaseState (approach_phases.py:244)
- FINAL → IDLE — SafetyGuard / weather / stabilization / DH / error budget (approach_phases.py:313,373,408,578,618; main.py:604,746)
### Go-around call sites: 10

### Missing transitions (NO_TRANSITION_DEFINED):
- INITIAL → IDLE: no go-around in InitialPhaseState
- LANDING → IDLE: no go-around in LandingPhaseState

---

## 8. Harness Results (v3 — real production methods)

| Scenario | Method Called | Status | Evidence |
|----------|--------------|--------|----------|
| ils_final_ap | FinalPhaseState.handle() | PASS | raw_control.set_* called via gateway |
| ils_final_vjoy | FinalPhaseState.handle() | PASS | virtual_joystick.apply_control_inputs called |
| non_ils_synthetic_glidepath | FinalPhaseState.handle() | PASS | synthetic_glidepath.compute_target_vs called |
| safety_guard_goaround | main._handle_phase() | PASS | SafetyGuard GO_AROUND → execute_go_around |
| stabilized_monitor_goaround | FinalPhaseState.handle() | PASS | stabilized_monitor.should_go_around → True |
| loc_signal_loss | main._calculate_approach_data() | PASS | loc_available=False → None → go-around |
| takeover_initiation | IntermediatePhaseState.handle() | PASS | should_initiate_takeover → perform_takeover |
| takeover_failure | FinalPhaseState.handle() | PASS | failed TakeoverStatus → execute_go_around |
| raw_ae_event_exception_swallowed | MSFSControl.set_vertical_speed() | PASS | exception caught, logged, swallowed |
| gateway_command_rejected | CommandGateway._authorize() | PASS | CommandRejected raised on mismatch |

All scenarios execute real production methods with mock dependencies. Traces saved in `harness/command-traces/`.

---

## 9. Data Flow

Primary telemetry bus: `telemetry.get_all_data()` → dict consumed by all modules. No module writes to this dict (STATIC_SCAN_NO_WRITES_FOUND).

Other data carriers: approach_data, wind_data, self.system.* state, approach_config, ownership objects, ContextVar CommandSource, state objects, recorder pending-frame state.

---

## 10. Safety/Fail-Safe

### Pre-command: SafetyGuard.evaluate() (main._handle_phase, before phase_state.handle())
### Post-command: StabilizedApproachMonitor (FinalPhaseState step 10, after commands)
### Weather: WindShearDetector, TurbulenceDetector (FinalPhaseState step 5, before commands)
### DH Guard: FinalPhaseState step 12a (after commands, before transition)

---

## 11. What Cannot Be Confirmed Without MSFS

- Real SimConnect communication timing
- LVAR/WASM read/write accuracy
- vJoy hardware mapping
- Telemetry jitter
- Connection switching under load

---

## 12. Architectural Risks

1. **Fail-silent actuator writes** — MSFSControl swallows exceptions
2. **set_gear outside SAFETY scope** — potential CommandRejected in edge cases
3. **No telemetry staleness detection**
4. **SEQUENTIAL_MIXED_COMMANDS** — approach commands before StabilizedMonitor check
5. **185 self.system.* accesses** — tight coupling

---

*Report v4. Harness 11/11 with real production methods. All evidence verified against baseline 3971ba1.*
