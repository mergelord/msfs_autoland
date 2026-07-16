# TASK: Fix confirmed findings from Wave 1 audit + cross-check (baseline 59d5118)

## Context

This task consolidates all findings from:
- Alisa's audits of the 8 PR #5 files (`safety_guard.py`, `autothrottle.py`, `navigation.py`, `main.py`)
- MiMo's independent cross-check of Alisa's findings (`CROSSCHECK-REPORT-59d5118.md`)
- Orchestrator's independent re-trace and correction of Finding 2's localization
  (`CROSSCHECK-FINDING2-CORRECTION.md`)

All 5 findings below are now triple/independently confirmed with exact matching code citations.
Work against `zhuk-mou-1/msfs_autoland`, branch off current `master`
(`59d5118779ec18017b138a09b172f5c321ec1dbe`). Baseline test suite: 293 passed, 6/6 CI checks green.

**Do not regress any existing test. Add new tests for every fix below.**

---

## PRIORITY 0 — MUST FIX NOW (Wave 1 regression, safety-relevant)

### Finding 1: kg/lbs unit mismatch in autothrottle weight correction

**Root cause:** `main.py` FIX-05 converted `total_weight` from lbs to kg
(`aircraft_weight_kg = weight_data.get('total_weight', 132277) * 0.453592`, ~line 491-492) and
passes it through `approach_phases.py::_get_aircraft_weight` into
`autothrottle.calculate_throttle(aircraft_weight=<kg value>)`. But
`autothrottle.py::calculate_base_throttle` still treats `aircraft_weight` as **pounds**
(docstring "Вес самолёта (фунты)", `AutothrottleConfig.weight_reference: float = 5000.0  #
фунты`, `weight_correction = (aircraft_weight - self.config.weight_reference) *
self.config.weight_factor`).

**Effect:** throttle authority is computed ~2.2x too low across the whole autothrottle range.
Not backstopped by any safety guard at the source (only reactively, after the fact, via G3/G4
airspeed-deviation checks in `safety_guard.py`, which react to the symptom, not the cause).

**Fix options (pick one, do not do both):**
1. Convert weight back to lbs at the `autothrottle.calculate_throttle` call boundary in
   `approach_phases.py::_control_throttle` (keep kg as the canonical unit everywhere else per
   FIX-05's intent), OR
2. Update `autothrottle.py`'s `AutothrottleConfig.weight_reference` and docstrings/comments to
   kg (5000 lbs ≈ 2267.96 kg) and treat `aircraft_weight` as kg consistently.

Prefer option 1 (localized, minimal blast radius) unless `autothrottle.py` has other lbs-based
constants that would also need conversion — audit for that before choosing.

**Required tests:** a regression test asserting `calculate_base_throttle`/`calculate_throttle`
produces the same throttle output for a known weight expressed consistently, e.g. a table-driven
test that passes a real-world kg aircraft weight through the full
`_get_aircraft_weight → calculate_throttle` path and asserts throttle authority is within
expected bounds (not ~2.2x off). Add a unit test directly on `calculate_base_throttle` with the
correct unit to prevent silent re-introduction.

---

## PRIORITY 1 — BACKLOG / HARDENING (not Wave 1 regressions, pre-existing)

### Finding 2: `int(NaN)` crash in vertical-speed command

**Corrected crash path** (localization corrected from Alisa's/initial MiMo citation of dead code
in `navigation.py`):
```
wind_correction.py:163  ground_speed = speed.get('ground_speed', 0)   # NaN from SimConnect
wind_correction.py:215  base_vs = self.calculate_descent_rate(ground_speed, ...)  # -> NaN (float, no int() cast)
wind_correction.py:227  corrected_vs = base_vs                          # -> NaN
approach_phases.py:487  vs = wind_data['corrected_vs']                  # -> NaN
approach_phases.py:488  self.system.control.set_vertical_speed(-int(vs))  # int(NaN) -> ValueError
```
Applies to both ILS (`corrected_vs` used directly) and VOR/NDB/LOC approaches (via
`SyntheticGlidepath.compute_target_vs`, which only clamps to 0.0 at the MDA floor and otherwise
passes NaN through).

Note: `Navigation.calculate_descent_rate` (`navigation.py:83`) is unrelated dead code (no
callers) — do not spend fix effort there; leave it or remove it as a separate cleanup, but it is
not on this crash path.

**Fix:** guard against non-finite `vs` immediately before the `int()` cast in
`approach_phases.py::_control_aircraft` (e.g. fail-closed to 0 fpm / hold current VS / trigger a
go-around per existing safety patterns in this codebase), AND/OR guard `ground_speed` for
finiteness in `wind_correction.py` before calling `calculate_descent_rate` (consistent with the
existing F-W2 guard style already used there for `wind_speed`/`wind_direction`).

**Required tests:** feed NaN/inf `ground_speed` through `apply_wind_corrections` and assert no
exception and a sane fallback value; feed NaN `corrected_vs` through `_control_aircraft` and
assert no exception / safe fallback.

### Finding 3: `cos(lat)` unguarded division near poles

Location: `navigation.py` — `calculate_glideslope_intercept_point` (unguarded
`cos(runway_threshold_lat)` division) and `calculate_runway_beacons` (same pattern, per MiMo's
crosscheck). Add a guard for `cos(lat) ≈ 0` (i.e., `abs(cos(lat)) < epsilon`) with a safe
fallback/error path, since MSFS runways near true poles are not realistic but defensive coding
is still warranted.

**Required tests:** call both functions with `lat` near ±90° and assert no
ZeroDivisionError/inf result propagates unguarded.

### Finding 4: `_calculate_headwind` NaN propagation

Location: `main.py::_calculate_headwind` (and its use in `_calculate_approach_speeds`) — no
finiteness guard on wind inputs before computing headwind component. Add a finiteness check
consistent with the existing `_is_finite_number` helper already used elsewhere in `main.py`, with
a safe fallback (e.g. treat as zero headwind) on invalid input.

**Required tests:** NaN/inf wind speed or direction input to `_calculate_headwind` should not
propagate NaN into downstream approach-speed calculations.

### Finding 5: GUARD SNAPSHOT log mismatch (cosmetic)

Location: `main.py::_handle_phase` — the GUARD SNAPSHOT log block uses `is not None` checks while
the actual guard logic elsewhere uses `_is_finite_number`. This can make the logged snapshot
claim a value is "present/valid" when it is actually NaN/inf. Align the log block to use
`_is_finite_number` for consistency with the real guard checks. No functional/safety impact —
logging only.

**Required tests:** none strictly required (cosmetic/logging), but a test asserting the log
reflects `_is_finite_number` semantics is welcome if convenient.

---

## Deliverables

1. One PR (or a small stack) implementing all fixes above, each with dedicated tests.
2. Full test suite must pass (293 existing + new tests), all 6 CI checks green.
3. A short report per finding: what changed, file/line, and the new test(s) added.
4. Do not touch any other unrelated code/tests. Do not modify Wave 1's already-merged FIX-05
   kg-conversion decision itself — only fix the downstream consumer mismatch (Finding 1).
