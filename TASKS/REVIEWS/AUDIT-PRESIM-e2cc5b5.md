# AUDIT-PRESIM: Pre-flight Readiness Audit

**Commit:** `e2cc5b5a25f5e1d29d60f5b9304961ff12e425b2`
**Date:** 2026-07-13
**Mode:** Read-only
**Scope:** All modules/*.py, main.py — full codebase audit for live MSFS readiness

## Files Audited (49 files, ~11,800 LOC)

| File | LOC | Status |
|------|-----|--------|
| main.py | 767 | Findings |
| modules/approach_phases.py | 753 | Findings |
| modules/connection_monitor.py | 717 | Clean |
| modules/aircraft_adapter.py | 596 | Clean |
| modules/navigation.py | 599 | Clean |
| modules/telemetry.py | 497 | Clean |
| modules/autothrottle.py | 389 | Clean |
| modules/autopilot_takeover.py | 439 | Clean (post P1-1 fix) |
| modules/control.py | 296 | Clean |
| modules/stabilized_approach.py | 320 | Clean |
| modules/safety_guard.py | 198 | Clean |
| modules/synthetic_glidepath.py | 168 | Clean |
| modules/command_gateway.py | 74 | Clean |
| modules/wind_correction.py | 244 | Clean |
| modules/flare_controller.py | 258 | Clean |
| modules/connection_optimizer.py | 339 | Clean |
| modules/dme_navigation.py | 252 | Clean |
| modules/ils_navigation.py | 226 | Clean |
| modules/approach_speed_calculator.py | 246 | Clean |
| modules/telemetry_recorder.py | 230 | Clean |
| modules/types.py | 72 | Clean |
| modules/control_ownership.py | 70 | Clean |
| modules/settings.py | 121 | Clean |
| modules/audio_alerts.py | 199 | Clean |
| modules/turbulence_detector.py | 264 | Clean |
| modules/wind_shear_detector.py | 269 | Clean |
| modules/engine_failure_detector.py | 245 | Clean |
| modules/thresholds_config.py | 223 | Clean |
| modules/log_analyzer.py | 358 | Clean |
| modules/log_database.py | 410 | Clean |
| modules/structured_logger.py | 315 | Clean |
| modules/virtual_joystick.py | 236 | Clean |
| modules/rudder_compensation.py | 205 | Clean |
| modules/aileron_compensation.py | 150 | Clean |
| modules/simconnect_client_data.py | 309 | Clean |
| modules/fms_reader.py | 228 | Clean |
| modules/navigraph_parser.py | 307 | Clean |
| modules/aircraft_config_reader.py | 313 | Clean |
| modules/aircraft_geometry.py | 208 | Clean |
| modules/airports_database.py | 209 | Clean |
| modules/approach_dialog.py | 518 | Clean |
| modules/settings_dialog.py | 164 | Clean |
| modules/wasm_interface.py | 308 | Clean |
| modules/wasm_version_checker.py | 232 | Clean |
| modules/auto_fixer.py | 192 | Clean |
| modules/base_controller.py | 42 | Clean |
| modules/msfs_airport_reader.py | 364 | Clean |
| modules/__init__.py | 1 | Clean |

---

## Findings

### AUD-01: Direct telemetry dict access in AutopilotTakeover — crash on missing keys

**Severity:** P0 (cannot fly)
**File:** `modules/autopilot_takeover.py:231-237`
**Confidence:** HIGH

```python
def _save_initial_parameters(self, telemetry: Dict):
    self.initial_parameters = {
        'altitude': telemetry['position']['altitude'],
        'altitude_agl': telemetry['position']['altitude_agl'],
        'airspeed': telemetry['speed']['airspeed_indicated'],
        'heading': telemetry['attitude']['heading_magnetic'],
        'pitch': telemetry['attitude']['pitch'],
        'bank': telemetry['attitude']['bank'],
        'vertical_speed': telemetry['speed']['vertical_speed']
    }
```

**Risk in live mode:** If SimConnect returns incomplete telemetry during a transient glitch (e.g. `position` dict exists but `altitude_agl` key is missing because the sim hasn't computed it yet), this raises `KeyError` and crashes `perform_takeover()` mid-sequence. The outer `execute_approach()` catches it after 3 consecutive errors, but by then the approach may be at 200ft with no commands being sent.

**Fix:** Replace with `.get()` with fail-closed defaults:
```python
'altitude': telemetry.get('position', {}).get('altitude', 0.0),
```

---

### AUD-02: Direct telemetry dict access in _perform_safety_checks — crash on missing keys

**Severity:** P0 (cannot fly)
**File:** `modules/autopilot_takeover.py:249,263,271,278-280,286`
**Confidence:** HIGH

```python
altitude_agl = telemetry['position']['altitude_agl']       # line 249
current_speed = telemetry['speed']['airspeed_indicated']   # line 263
current_alt = telemetry['position']['altitude']             # line 271
bank = abs(telemetry['attitude']['bank'])                   # line 278
pitch = telemetry['attitude']['pitch']                      # line 279
vertical_speed = telemetry['speed']['vertical_speed']       # line 286
```

**Risk:** Same as AUD-01. Any missing key in any of these 6 accesses crashes the entire safety check, preventing takeover completion. At 200ft AGL this is unrecoverable.

**Fix:** Use `.get()` with safe defaults for each access.

---

### AUD-03: Direct telemetry dict access in _save_initial_parameters crash path propagates to perform_takeover

**Severity:** P0 (cascade)
**File:** `modules/autopilot_takeover.py:159-160`
**Confidence:** HIGH

```python
if not self.initial_parameters:
    self._save_initial_parameters(telemetry)
```

**Risk:** If `_save_initial_parameters()` crashes (AUD-01), the exception propagates up through `perform_takeover()` → `_perform_takeover()` → `IntermediatePhaseState/FinalPhaseState`. In `FinalPhaseState`, this crashes `_handle_phase()`, which is caught by the outer `execute_approach()` exception handler. But the state machine is left in an inconsistent state — `takeover_initiated=True` but `status.completed=False`, and no go-around is executed.

**Fix:** Wrap `_save_initial_parameters()` in try/except with fallback to empty dict, or use defensive access as in AUD-01.

---

### AUD-04: IntermediatePhaseState direct access to approach_data without None guard

**Severity:** P1 (high risk)
**File:** `modules/approach_phases.py:54-56,89-92`
**Confidence:** HIGH

```python
# InitialPhaseState.handle():
distance = approach_data['distance_to_station']         # line 54
cross_track = approach_data['cross_track_error']         # line 55

# IntermediatePhaseState.handle():
distance = approach_data['distance_to_station']         # line 89
altitude = telemetry['position']['altitude']             # line 90
required_alt = approach_data['required_altitude']        # line 92
```

**Risk:** If `_calculate_approach_data()` returns a partial dict (e.g. LOC signal loss returns `loc_available=False` but the code path reaches the state handler before the None check in `_handle_phase`), these crash. The `_handle_phase()` has `if approach_data is None: return` at line 699, which protects against None, but NOT against partial dicts.

**Fix:** Use `.get()` with defaults or validate `approach_data` completeness before state delegation.

---

### AUD-05: FinalPhaseState._control_aircraft direct access to telemetry['attitude']

**Severity:** P1 (high risk)
**File:** `modules/approach_phases.py:444-446`
**Confidence:** HIGH

```python
current_bank = telemetry['attitude']['bank']
current_pitch = telemetry['attitude']['pitch']
current_heading = telemetry['attitude']['heading_magnetic']
```

**Risk:** If vJoy path is active and attitude data is missing (transient SimConnect glitch), this crashes the entire FINAL phase handler. No go-around is executed because the exception propagates to the outer handler.

**Fix:** Use `.get()` with safe defaults.

---

### AUD-06: LandingPhaseState._deploy_flaps_and_gear — no None guard on radio_height

**Severity:** P1 (high risk)
**File:** `modules/approach_phases.py:581,586`
**Confidence:** MEDIUM

```python
if radio_height < 2000 and not self._flaps_2_deployed:
    ...
if radio_height < 1500:
    ...
```

**Risk:** `radio_height` comes from `telemetry['position'].get('radio_height', altitude_agl)`. If both are None, `radio_height` is None and `None < 2000` raises `TypeError` in Python 3. The calling code in `FinalPhaseState.handle()` at line 247 does `radio_height = telemetry['position'].get('radio_height', altitude_agl)` — if `altitude_agl` is also None, `radio_height` is None. However, the LANDING phase entry requires `radio_height < decision_height` (line 290), which would also fail if None. So this is only reachable if the type confusion happens in an edge case.

**Fix:** Add `if radio_height is None: return` guard at function entry.

---

### AUD-07: time.time() used for periodic logging — NTP/DST jump risk

**Severity:** P2 (desirable)
**File:** `main.py:747-748,814-815`
**Confidence:** MEDIUM

```python
current_time = time.time()                                    # line 747
if current_time - getattr(self, '_last_guard_snapshot_log_time', 0.0) > 5.0:

self._last_fms_log_time = current_time                        # line 821
```

**Risk:** `time.time()` is not monotonic. NTP adjustments or DST transitions can cause large jumps, making the 5-second logging interval fire erratically. Not a safety issue (logging only), but can cause log flooding or silence during jumps.

**Fix:** Use `time.monotonic()` for interval timing.

---

### AUD-08: _calculate_approach_speeds silently swallows all exceptions

**Severity:** P1 (high risk)
**File:** `main.py:512-514`
**Confidence:** HIGH

```python
except Exception as e:
    logger.error("Failed to calculate approach speeds: %s", e)
    logger.warning("Using default approach speed from config")
```

**Risk:** If speed calculation fails (e.g. missing telemetry data, invalid aircraft weight), the system silently falls back to `config.approach_speed` which may be 120kt — potentially wrong for the actual aircraft/weight/weather. In live mode, an incorrect Vref means the safety guard thresholds (G3 underspeed, G4 overspeed) are calibrated to the wrong speed, and the stabilization check uses wrong criteria. This is a silent degradation that could lead to a hard landing or go-around at the wrong threshold.

**Fix:** At minimum, log the fallback value explicitly. Better: validate that the fallback is within ±20kt of expected Vref for the aircraft type.

---

### AUD-09: execute_go_around() gear retraction not commanded

**Severity:** P2 (desirable)
**File:** `main.py:446-448`
**Confidence:** MEDIUM

```python
# 4. Уборка шасси (после положительного набора)
# Шасси убираем только если набираем высоту
logger.info("Go-around: Gear up after positive climb")
```

**Risk:** The gear retraction is logged but never actually commanded. After go-around, the aircraft climbs with gear down, creating drag. In a go-around scenario with engine failure or low energy, this drag could be critical.

**Fix:** Add `self.control.set_gear(False)` after confirming positive climb rate, or at minimum add a timer-based retraction after 5 seconds.

---

### AUD-10: No go-around path from INITIAL phase state

**Severity:** P2 (desirable)
**File:** `modules/approach_phases.py:51-77`
**Confidence:** MEDIUM

**Risk:** `InitialPhaseState.handle()` has no go-around logic. If the aircraft is in INITIAL phase and encounters critical wind shear, unsafe bank, or engine failure, there is no automatic go-around — the state just keeps setting heading hold. The safety guard only runs in FINAL phase (line 710: `if self.phase == ApproachPhase.FINAL`).

**Fix:** Add critical condition checks in INITIAL and INTERMEDIATE phases, or extend safety guard coverage to all phases.

---

### AUD-11: No replay test for VOR/NDB approach flow

**Severity:** P2 (desirable)
**File:** `tests/replay/` — missing fixture
**Confidence:** HIGH

**Risk:** The 4 existing replay tests cover only ILS scenarios. There are no replay tests for VOR/NDB approaches with synthetic glidepath, which is the primary use case. A regression in `synthetic_glidepath.py` or `wind_correction.py` would not be caught by replay tests.

**Fix:** Add `vor_nominal.jsonl` and `ndb_nominal.jsonl` replay fixtures.

---

### AUD-12: No replay test for safety guard trigger under load

**Severity:** P2 (desirable)
**File:** `tests/replay/` — missing fixture
**Confidence:** HIGH

**Risk:** No replay scenario tests the safety guard actually triggering GO_AROUND in a realistic sequence. The unit tests mock the guard, but no integration test verifies the full pipeline: telemetry → guard evaluation → go-around → flap/gear retraction → telemetry recorder flush.

**Fix:** Add `safety_guard_goaround.jsonl` fixture that reproduces a sink rate exceedance triggering guard GO_AROUND.

---

### AUD-13: No integration test for full control loop (telemetry → actuators)

**Severity:** P2 (desirable)
**File:** `tests/` — missing
**Confidence:** HIGH

**Risk:** Unit tests test individual modules with mocks. No test exercises the complete `execute_approach()` → `_handle_phase()` → `FinalPhaseState._control_aircraft()` → `control.set_vertical_speed()` chain with realistic telemetry. A wiring error between modules would not be caught.

**Fix:** Add integration test using `make_telemetry()` that runs 10+ iterations of `execute_approach()` body and verifies actuator commands.

---

### AUD-14: `_get_aircraft_weight` fallback returns lbs when SimConnect provides weight

**Severity:** P2 (desirable)
**File:** `modules/approach_phases.py:533-538`
**Confidence:** MEDIUM

```python
weight_data = telemetry.get('weight', {})
if weight_data and 'total_weight' in weight_data:
    aircraft_weight = weight_data['total_weight']
    logger.debug("Using aircraft weight from SimConnect: %s lbs", aircraft_weight)
    return aircraft_weight
```

**Risk:** SimConnect `TOTAL_WEIGHT` returns pounds, but `approach_params['aircraft_weight_kg']` is in kilograms. The fallback at line 537 returns lbs but the autothrottle may expect kg. Unit mismatch in weight → incorrect throttle calculation during flare.

**Fix:** Document the unit expectation clearly, or convert lbs to kg in the SimConnect fallback path.

---

### AUD-15: StabilizedApproachMonitor.check_stabilization returns None for is_stabilized when above gate

**Severity:** P2 (desirable)
**File:** `modules/stabilized_approach.py:114-120`
**Confidence:** MEDIUM

```python
if radio_height > self.criteria.stabilization_height:
    return {
        'is_stabilized': None,
        'checked': False,
        ...
    }
```

**Risk:** When above stabilization height, `is_stabilized` is `None`. In `FinalPhaseState._check_final_stabilization()` (line 603): `if not self.system.stabilized_monitor.is_stabilized and radio_height > 200` — `not None` is `True`, so this triggers go-around when above stabilization height but below 200ft. This is correct behavior (not stabilized at low altitude), but the `None` semantics are confusing and could break if the condition is inverted.

**Fix:** Consider using `False` instead of `None` for consistency, or add explicit None check.

---

## Summary Table

| Severity | Count | IDs |
|----------|-------|-----|
| P0 (cannot fly) | 3 | AUD-01, AUD-02, AUD-03 |
| P1 (high risk) | 3 | AUD-04, AUD-05, AUD-08 |
| P2 (desirable) | 7 | AUD-06, AUD-07, AUD-09, AUD-10, AUD-11, AUD-12, AUD-13, AUD-14, AUD-15 |
| **Total** | **15** | |

## Verdict: **NO-GO** for unattended live flight

**Rationale:** Three P0 findings (AUD-01, AUD-02, AUD-03) all involve direct `telemetry['key']` access in `AutopilotTakeover` that will raise `KeyError` on incomplete SimConnect data. In live mode, transient telemetry gaps are guaranteed (SimConnect lag, sim freeze, weather reload). A `KeyError` at 200ft AGL during takeover sequence means no commands are sent and no go-around is executed — the aircraft continues uncontrolled.

**Minimum for GO:**
1. Fix AUD-01/02/03 (defensive telemetry access in autopilot_takeover.py) — **P0 blocker**
2. Fix AUD-08 (silent speed calculation fallback) — **P1, quick fix**

**Recommended for GO:**
3. Fix AUD-04/05 (defensive access in approach_phases.py) — **P1**
4. Add at least one VOR/NDB replay fixture (AUD-11) — **P2, high confidence gap**

**Can defer:**
- AUD-06, AUD-07, AUD-09, AUD-10, AUD-13, AUD-14, AUD-15 — P2 items, not blocking first flight
