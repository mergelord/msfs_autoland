# FIXPACK-GO Report — e2cc5b5 → a9dc1e0

**Base:** `e2cc5b5a25f5e1d29d60f5b9304961ff12e425b2` (master, 221/0)
**Head:** `a9dc1e0` (fix/go-blockers)
**Tests:** 251 passed, 0 failed (221 original + 30 new)
**Branch:** `fix/go-blockers` — pushed to origin

---

## F1: Contract approach_data — ils_navigation.py + approach_phases.py

### Diff (ils_navigation.py)
- Added `_geometric_distance_to_threshold()` — Haversine fallback when DME unavailable
- `calculate_ils_approach()`: added `distance_to_station` (geometric, NOT dme_distance), `cross_track_error` (= `-loc_dev['degrees']`), `on_course` (= `loc_dev['on_course']`)
- `calculate_loc_approach()`: added same 3 keys + `required_altitude` (synthetic glidepath geometry via `calculate_required_altitude()`)
- Defensive telemetry access: `telemetry.get('position', {})` etc.

### Diff (approach_phases.py — consumer)
- `InitialPhaseState.handle()`: `approach_data['key']` → `.get('key', fail-closed default)`
  - `distance_to_station` default 999.0 (not 0 — prevents false proximity gate)
  - `required_altitude` default None (gate skips if missing)
  - `cross_track_error` default 0.0
  - `on_course` default False
- `IntermediatePhaseState.handle()`: same pattern for `distance_to_station`, `required_altitude`

### Tests
| Test | Result |
|------|--------|
| `test_ils_returns_all_consumer_keys` | PASS |
| `test_ils_keys_are_not_none` | PASS |
| `test_ils_distance_geometric_fallback_no_dme` | PASS |
| `test_ils_cross_track_error_is_degrees` | PASS |
| `test_loc_returns_all_consumer_keys` | PASS |
| `test_loc_keys_are_not_none` | PASS |
| `test_loc_required_altitude_from_glidepath_geometry` | PASS |
| `test_loc_distance_geometric` | PASS |
| `test_vor_returns_all_consumer_keys` | PASS (regression) |

---

## F2: ILS deadlock INTERMEDIATE→FINAL — approach_phases.py

### Diff
`IntermediatePhaseState.handle()` transition gate (lines 131-155):
- **Before:** `if distance < 8 and abs(altitude - required_alt) < 300: if not status.completed: wait`
- **After:** approach-type-aware gate:
  - ILS: transition to FINAL on `on_localizer` + `distance < 8` **without** requiring `status.completed`
  - Non-ILS: original logic (require completed takeover)
- Added `required_alt is not None` guard to prevent TypeError on None comparison
- `on_localizer` from approach_data used for ILS gate

### Tests
| Test | Result |
|------|--------|
| `test_ils_transitions_on_loc_capture` | PASS |
| `test_ils_no_final_without_loc` | PASS |
| `test_vor_requires_completed_takeover` | PASS (regression) |
| `test_vor_transitions_with_completed_takeover` | PASS |

---

## F3: execute_go_around re-engage AP — main.py

### Diff
`execute_go_around()` (lines 422-461):
- Added `self.control.set_autopilot_master(True)` as FIRST command in SAFETY scope (before throttle/VS/flaps)
- Added `self.control.set_gear(False)` — real gear UP command (was a comment only)
- Removed misleading comment about "positive climb"

### Tests
| Test | Result |
|------|--------|
| `test_go_around_reengages_ap_master` | PASS |
| `test_go_around_sends_gear_up` | PASS |
| `test_go_around_sends_vs_and_throttle` | PASS |

---

## F4: Error budget → go-around — main.py

### Diff
`execute_approach()` error handler (lines 591-600):
- **Before:** `self.stop_approach()` (unconditional)
- **After:** `if self.autopilot_takeover.status.completed: self.execute_go_around() else: self.stop_approach()`

### Tests
| Test | Result |
|------|--------|
| `test_error_budget_goaround_after_takeover` | PASS |
| `test_error_budget_stop_before_takeover` | PASS |

---

## F5: Defensive telemetry — autopilot_takeover.py

### Diff
`_save_initial_parameters()`:
- Complete rewrite: `telemetry.get('position', {}).get('altitude')` etc.
- Missing critical keys (altitude, altitude_agl, airspeed) → warning + return without saving (retry next tick)

`_perform_safety_checks()`:
- Complete rewrite: every channel checked for None before use
- Missing channel → corresponding check = False (fail-closed)
- `bank=None` → `attitude_safe=False` (NOT 0.0 which would be fail-open)
- `airspeed=None` → `speed_stable=False`
- `altitude=None` → `altitude_stable=False`
- `vertical_speed=None` → `sink_rate_safe=False`
- `altitude_agl=None` → `altitude_safe=False`

### Tests
| Test | Result |
|------|--------|
| `test_incomplete_telemetry_no_crash` | PASS |
| `test_valid_telemetry_saves` | PASS |
| `test_missing_bank_fail_closed` | PASS |
| `test_missing_airspeed_fail_closed` | PASS |
| `test_missing_altitude_fail_closed` | PASS |
| `test_missing_vs_fail_closed` | PASS |
| `test_missing_agl_fail_closed` | PASS |
| `test_no_initial_params_speed_stable_false` | PASS |

---

## F6: G5 expansion — safety_guard.py + main.py

### Diff
`safety_guard.py:evaluate()`:
- Added parameters: `has_vs=True`, `has_bank=True`
- G5 rule: `not has_height or not has_airspeed or not has_vs or not has_bank`

`main.py:_handle_phase()`:
- Added `attitude_data = telemetry.get('attitude', {})`
- Pass `has_vs=speed_data.get('vertical_speed') is not None`
- Pass `has_bank=attitude_data.get('bank') is not None`

### Tests
| Test | Result |
|------|--------|
| `test_vs_missing_triggers_g5` | PASS |
| `test_bank_missing_triggers_g5` | PASS |
| `test_all_present_no_g5` | PASS |
| `test_height_missing_still_triggers` | PASS |

---

## Summary

| Fix | Files changed | Tests | Status |
|-----|--------------|-------|--------|
| F1 | ils_navigation.py, approach_phases.py | 9 | DONE |
| F2 | approach_phases.py | 4 | DONE |
| F3 | main.py | 3 | DONE |
| F4 | main.py | 2 | DONE |
| F5 | autopilot_takeover.py | 8 | DONE |
| F6 | safety_guard.py, main.py | 4 | DONE |
| **Total** | **5 production + 5 test** | **30** | **251/0** |

**VOR/NDB regression:** `test_vor_returns_all_consumer_keys` PASS, `test_vor_requires_completed_takeover` PASS, `test_vor_transitions_with_completed_takeover` PASS.

**No changes outside listed files.**
