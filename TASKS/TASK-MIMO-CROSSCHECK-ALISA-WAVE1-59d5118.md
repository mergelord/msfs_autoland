# TASK: Cross-check Alisa's Wave 1 regression audits (all 8 PR #5 files)

## Context

Alisa completed 4 independent regression audits covering all 8 files touched by PR #5
(merge commit `f1b47f98131d85d5fd29683dc0354b46952d4ab2`, final head commit
`59d5118779ec18017b138a09b172f5c321ec1dbe`, baseline `3971ba12113d8994665b1c9a172f2dca6c9e3855`):

1. `safety_guard.py` (+ `tests/test_safety_guard.py`)
2. `autothrottle.py` (+ `tests/test_autothrottle.py`, `approach_phases.py` call path)
3. `navigation.py` (+ `tests/test_navigation.py`)
4. `main.py` remaining diff (import, comment, `weight_data` var, GUARD SNAPSHOT log block)

The orchestrating auditor (me) independently re-verified each report against the live repo
after Alisa delivered it, and made corrections/upgrades where warranted. Before committing to
a fix task, we want a **second independent pair of eyes (MiMo)** to cross-check Alisa's
arguments and my corrections, specifically for the findings below. Do not simply restate
Alisa's conclusions — independently trace the code yourself against the live repo and say
where you agree, disagree, or would add nuance.

**Audited version:** `master` @ `59d5118779ec18017b138a09b172f5c321ec1dbe` (repo
`zhuk-mou-1/msfs_autoland`). Verify via GitHub API, do not trust cached assumptions.

## Findings to cross-check

### 1. [CRITICAL — candidate regression] autothrottle F4: kg/lbs unit mismatch

**Claim (confirmed by Alisa, independently re-traced and upgraded to STATIC_CONFIRMED by the
orchestrator):** In `approach_phases.py`, `_get_aircraft_weight()` returns
`approach_params['aircraft_weight_kg']` (a kilogram value, per FIX-08's weight-conversion fix).
This value is then passed as `aircraft_weight=` into `autothrottle.calculate_throttle()`, whose
internal `calculate_base_throttle()` treats the value as **pounds** (e.g. divides by a
lbs-denominated reference weight such as 5000). Net effect: throttle calculation receives a
weight value that is off by the kg/lbs conversion factor (~2.2x), degrading throttle authority
sizing.

**Please verify:**
- Trace the exact call chain yourself: `_handle_phase` / `_control_throttle` →
  `_get_aircraft_weight` → `autothrottle.calculate_throttle` → `calculate_base_throttle`.
- Confirm (or refute) that the value really is kg at the point it's produced, and really is
  treated as lbs at the point it's consumed.
- Is this genuinely introduced/exposed by Wave 1 (FIX-08), or did an equivalent mismatch exist
  before Wave 1 under a different code path? (baseline commit `3971ba1` is the pre-Wave-1
  reference.)
- Confirm whether `safety_guard` G3/G4 (ias vs vref bounds) fully backstops this, or whether
  there are flight phases/conditions where degraded throttle sizing could exceed the guard's
  reaction margin.

### 2. [Pre-existing, not Wave 1] navigation F2: `calculate_descent_rate` crash on NaN/inf

**Claim:** `vs = ground_speed * math.tan(math.radians(glideslope_angle)) * 101.3; return int(vs)`
— `int(float('nan'))` raises `ValueError`, `int(float('inf'))` raises `OverflowError`. No guard
exists. This method is NOT touched by the Wave 1 diff (FIX-04 only touches
`calculate_landing_distance`).

**Please verify:**
- Confirm this is real (reproduce the exception in your own trace/reasoning).
- Confirm whether this method is reachable with attacker/telemetry-controlled NaN/inf
  `ground_speed` in the actual production call path (i.e., is there any upstream filtering
  before this is called during a live approach?).
- Confirm this method's diff-history: was it modified at all by Wave 1, or purely pre-existing?

### 3. [Pre-existing, not Wave 1] navigation F6: division by `cos(lat)` at poles

**Claim:** `calculate_glideslope_intercept_point` divides by
`math.cos(math.radians(runway_threshold_lat))`, which is 0 at latitude ±90°. Unguarded.
`calculate_runway_beacons` was cited by Alisa as having the same pattern but its body was never
fully fetched/confirmed by the orchestrator (only the signature/docstring was read).

**Please verify:**
- Fetch and confirm (or refute) the actual body of `calculate_runway_beacons` — does it also
  divide by `cos(lat)` unguarded?
- Assess practical severity (real-world runways are never at ±90° latitude, so this is more of
  a defensive-programming gap than an operational risk) — do you agree with that framing?

### 4. [Pre-existing, not Wave 1] navigation F11 / main.py `_calculate_headwind`: no NaN/inf filter

**Claim:** `main.py._calculate_headwind`: `headwind = wind_speed * math.cos(math.radians(wind_angle))`
with no `math.isfinite(wind_speed)` guard. This headwind value feeds into
`calculate_landing_distance` (guarded by FIX-04 only for `ground_speed`, not `headwind`) and
potentially other consumers.

**Please verify:**
- Trace all consumers of `_calculate_headwind`'s return value in the current `main.py` /
  `approach_phases.py` and confirm whether any of them would silently propagate NaN into a
  safety-relevant decision (as opposed to just a logged/informational value).

### 5. [Cosmetic, already agreed low-severity] safety_guard/main.py F1: GUARD SNAPSHOT log mismatch

**Claim:** The periodic GUARD SNAPSHOT logging block in `main.py` (~lines 769-803) uses
`x.get(...) is not None` instead of `_is_finite_number(...)`, while the actual `_handle_phase`
decision logic (~lines 737-741) correctly uses `_is_finite_number`. This means the log can
display `has_vs=True` for a NaN value even though the real decision treated it as `False`.
Both Alisa and the orchestrator agree this affects only log readability, not runtime behavior.

**Please verify:**
- Confirm you agree this is genuinely cosmetic (i.e., the GUARD SNAPSHOT block's output is never
  read back into any decision — it is purely `logger.info`/similar output).

## Deliverable

For each of the 5 items above, give a verdict: `AGREE` / `DISAGREE` / `PARTIALLY AGREE (with
nuance)`, with your own code citations (fetched from the live repo at `59d5118`, not copied from
Alisa's report). Flag explicitly if you find anything Alisa or the orchestrator missed,
especially anything that would change which items belong in a "must-fix-now" critical bucket
versus a "backlog/hardening" bucket.

Do not propose or write the actual code fix yet — this is a verification/cross-check pass only.
The fix task will be written separately once this cross-check is back.
