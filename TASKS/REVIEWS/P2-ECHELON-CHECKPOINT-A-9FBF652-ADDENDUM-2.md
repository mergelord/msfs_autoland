# P2 ECHELON CHECKPOINT A — Final Corrected Report (Addendum 2 Response)

```
STATUS: COMPLETED_NO_CHANGES
BASE_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
HEAD_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
WORKTREE_EVIDENCE: 6 modified PNGs + 8 untracked (pre-existing, read-only audit)
CODE_CHANGED: no
COMMIT_CREATED: no
PR_CREATED: no
```

---

## CM02_EXECUTABLE_PROBE

```bash
python probes_lv/cm02_boundary_probe.py
```

Raw output (84 combinations):

```
 alt_agl     VS |   prev_phase ->    new_phase
--------------------------------------------------
     499   -501 |       CRUISE ->      landing
     499   -500 |       CRUISE ->      landing
     499     -1 |       CRUISE ->      landing
     499      0 |       CRUISE ->      landing
     499      1 |       CRUISE ->      landing
     499    500 |       CRUISE ->      landing
     499    501 |       CRUISE ->      takeoff
     500   -501 |       CRUISE ->     approach
     500   -500 |       CRUISE ->     approach
     500     -1 |       CRUISE ->     approach
     500      0 |       CRUISE ->       cruise
     500      1 |       CRUISE ->       cruise
     500    500 |       CRUISE ->       cruise
     500    501 |       CRUISE ->      takeoff
     501   -501 |       CRUISE ->     approach
     501   -500 |       CRUISE ->     approach
     501     -1 |       CRUISE ->     approach
     501      0 |       CRUISE ->       cruise
     501      1 |       CRUISE ->       cruise
     501    500 |       CRUISE ->       cruise
     501    501 |       CRUISE ->      takeoff
    1499   -501 |       CRUISE ->     approach
    1499   -500 |       CRUISE ->     approach
    1499     -1 |       CRUISE ->     approach
    1499      0 |       CRUISE ->       cruise
    1499      1 |       CRUISE ->       cruise
    1499    500 |       CRUISE ->       cruise
    1499    501 |       CRUISE ->      takeoff
    1500   -501 |       CRUISE ->     approach
    1500   -500 |       CRUISE ->     approach
    1500     -1 |       CRUISE ->     approach
    1500      0 |       CRUISE ->       cruise
    1500      1 |       CRUISE ->       cruise
    1500    500 |       CRUISE ->       cruise
    1500    501 |       CRUISE ->        climb
    1501   -501 |       CRUISE ->     approach
    1501   -500 |       CRUISE ->     approach
    1501     -1 |       CRUISE ->     approach
    1501      0 |       CRUISE ->       cruise
    1501      1 |       CRUISE ->       cruise
    1501    500 |       CRUISE ->       cruise
    1501    501 |       CRUISE ->        climb
    2999   -501 |       CRUISE ->     approach
    2999   -500 |       CRUISE ->     approach
    2999     -1 |       CRUISE ->     approach
    2999      0 |       CRUISE ->       cruise
    2999      1 |       CRUISE ->       cruise
    2999    500 |       CRUISE ->       cruise
    2999    501 |       CRUISE ->        climb
    3000   -501 |       CRUISE ->       cruise
    3000   -500 |       CRUISE ->       cruise
    3000     -1 |       CRUISE ->       cruise
    3000      0 |       CRUISE ->       cruise
    3000      1 |       CRUISE ->       cruise
    3000    500 |       CRUISE ->       cruise
    3000    501 |       CRUISE ->        climb
    3001   -501 |       CRUISE ->       cruise
    3001   -500 |       CRUISE ->       cruise
    3001     -1 |       CRUISE ->       cruise
    3001      0 |       CRUISE ->       cruise
    3001      1 |       CRUISE ->       cruise
    3001    500 |       CRUISE ->       cruise
    3001    501 |       CRUISE ->        climb
    9999   -501 |       CRUISE ->       cruise
    9999   -500 |       CRUISE ->       cruise
    9999     -1 |       CRUISE ->       cruise
    9999      0 |       CRUISE ->       cruise
    9999      1 |       CRUISE ->       cruise
    9999    500 |       CRUISE ->       cruise
    9999    501 |       CRUISE ->        climb
   10000   -501 |       CRUISE ->       cruise
   10000   -500 |       CRUISE ->       cruise
   10000     -1 |       CRUISE ->       cruise
   10000      0 |       CRUISE ->       cruise
   10000      1 |       CRUISE ->       cruise
   10000    500 |       CRUISE ->       cruise
   10000    501 |       CRUISE ->       cruise
   10001   -501 |       CRUISE ->      descent
   10001   -500 |       CRUISE ->       cruise
   10001     -1 |       CRUISE ->       cruise
   10001      0 |       CRUISE ->       cruise
   10001      1 |       CRUISE ->       cruise
   10001    500 |       CRUISE ->       cruise
   10001    501 |       CRUISE ->       cruise

--- on_ground=True tests ---
       0   -500 |        CLIMB ->       ground
       0      0 |        CLIMB ->       ground
       0    500 |        CLIMB ->       ground
     100   -500 |        CLIMB ->       ground
     100      0 |        CLIMB ->       ground
     100    500 |        CLIMB ->       ground
     500   -500 |        CLIMB ->       ground
     500      0 |        CLIMB ->       ground
     500    500 |        CLIMB ->       ground
    1500   -500 |        CLIMB ->       ground
    1500      0 |        CLIMB ->       ground
    1500    500 |        CLIMB ->       ground
```

## CM02_CORRECTED_MATRIX

Derived from probe output. prev_phase=CRUISE for all. `*` marks HOLD PREVIOUS.

| alt | VS=-501 | VS=-500 | VS=-1 | VS=0 | VS=1 | VS=500 | VS=501 |
|---|---|---|---|---|---|---|---|
| **499** | landing | landing | landing | landing | landing | landing | **takeoff** |
| **500** | approach | approach | approach | *cruise | *cruise | *cruise | **takeoff** |
| **501** | approach | approach | approach | *cruise | *cruise | *cruise | **takeoff** |
| **1499** | approach | approach | approach | *cruise | *cruise | *cruise | **takeoff** |
| **1500** | approach | approach | approach | *cruise | *cruise | *cruise | **climb** |
| **1501** | approach | approach | approach | *cruise | *cruise | *cruise | **climb** |
| **2999** | approach | approach | approach | *cruise | *cruise | *cruise | **climb** |
| **3000** | *cruise | *cruise | *cruise | *cruise | *cruise | *cruise | **climb** |
| **3001** | *cruise | *cruise | *cruise | *cruise | *cruise | *cruise | **climb** |
| **9999** | *cruise | *cruise | *cruise | *cruise | *cruise | *cruise | **climb** |
| **10000** | *cruise | *cruise | *cruise | *cruise | *cruise | *cruise | *cruise |
| **10001** | **descent** | *cruise | *cruise | *cruise | *cruise | *cruise | *cruise |

Key observations from probe:
- **499ft, VS=501 → takeoff**: `<1500 and VS>500` (TAKEOFF) checked BEFORE `<500` (LANDING)
- **500ft, VS<0 → approach**: `<3000 and VS<0` (APPROACH) matches; `<500` does NOT match (excludes 500)
- **500ft, VS=0 → \*cruise (HOLD)**: no branch matches; previous phase retained
- **1500ft, VS=501 → climb**: `<10000 and VS>500` (CLIMB) matches
- **3000ft, VS<0 → \*cruise (HOLD)**: `<3000` excludes exactly 3000; `<10000 and VS>500` is False; `>10000` is False
- **10000ft, all VS → \*cruise (HOLD)**: `<10000` excludes 10000; `>10000` excludes 10000; no branch matches
- **10001ft, VS=-501 → descent**: `>10000 and VS<-500` (DESCENT) matches
- **on_ground=True → ground** at all altitudes and VS values

---

## CM03_EXECUTABLE_PROBE

```bash
python probes_lv/cm03_state_probe.py
```

Raw output:

```
init_CE |                                 before_active |                                  after_active |                                 after_success
        |                     CE  rel   degraded  score |                     CE  rel   degraded  score |                     CE  rel   degraded  score
-----------------------------------------------------------------------------------------------------------------------------------------------------------
      0 |  0 1.00  False     0.0 |  0 1.00  False     0.0 |  0 1.00  False    97.8
      2 |  2 0.00  False    42.0 |  2 1.00  False    89.0 |  0 0.33  False    64.4
      3 |  3 0.00   True    38.0 |  3 1.00   True    85.0 |  0 0.25  False    60.2
      5 |  5 0.00   True    30.0 |  5 1.00   True    77.0 |  0 0.17  False    56.1

init_CE |                 after_active + 1 passive FAIL
        |                     CE  rel   degraded  score
------------------------------------------------------------
      0 |  1 0.00  False    43.0
      2 |  3 0.00   True    35.0
      3 |  4 0.00   True    31.0
      5 |  6 0.00   True    27.1
```

## CM03_CORRECTED_TABLE

| init_CE | before_active: CE/degraded | after_active: CE/degraded | after_1_success: CE/degraded | after_active+1_fail: CE/degraded |
|---|---|---|---|---|
| 0 | 0/False | 0/False | 0/False | 1/False |
| 2 | 2/False | 2/False | **0**/False | 3/**True** |
| 3 | 3/True | 3/True | **0**/False | 4/True |
| 5 | 5/True | 5/True | **0**/False | 6/True |

Key corrections from previous report:
- **After passive success, consecutive_errors resets to 0** (via `add_operation(success=True)` line 83: `self.consecutive_errors = 0`). Previous report incorrectly stated CE remains at 3/5.
- **Active test does NOT reset CE** — confirmed: CE stays at initial value after active test field assignments.
- **After active test + 1 passive failure**: CE increments from initial value (e.g. 2→3, 3→4, 5→6).
- **Design question remains:** Should active test reset CE? Currently it doesn't, but passive success does.

---

## GATEWAY_REPO_WIDE_SEARCH

### source_scope() callsites (production code only)

| # | File | Line | Code | Source | Context |
|---|---|---|---|---|---|
| 1 | main.py | 431 | `self.control.source_scope(CommandSource.SAFETY)` | SAFETY | `execute_go_around()` — go-around commands |

Other source_scope() references are in test files (`tests/test_p0_architecture.py:20,24`), harness scripts (`docs/.../harness/run_harness.py:466`, `research/.../harness/run_harness.py:466`), and research/diagram files — NOT production.

### Unscoped gateway callsites (production code)

**main.py:**

| Line | Method | Channel | Phase |
|---|---|---|---|
| 349 | set_nav_frequency | navigation | start_approach |
| 352 | set_nav_frequency | navigation | start_approach |
| 355 | set_nav_frequency | navigation | start_approach |
| 356 | set_obs | navigation | start_approach |
| 358 | set_adf_frequency | navigation | start_approach |
| 369 | set_autopilot_master(True) | autopilot | start_approach |
| 370 | set_airspeed_hold | autopilot | start_approach |
| 436 | set_autopilot_master(True) | autopilot | execute_go_around (inside SAFETY scope) |
| 442 | set_throttle(1.0) | throttle | execute_go_around (inside SAFETY scope) |
| 445 | set_vertical_speed(1500) | pitch | execute_go_around (inside SAFETY scope) |
| 448 | set_flaps(2) | configuration | execute_go_around (inside SAFETY scope) |
| 452 | set_gear(False) | configuration | execute_go_around (inside SAFETY scope) |

**approach_phases.py:**

| Line | Method | Channel | Phase |
|---|---|---|---|
| 71 | set_heading_hold | roll | InitialPhaseState.handle |
| 127 | set_heading_hold | roll | IntermediatePhaseState.handle |
| 132 | set_vertical_speed | pitch | IntermediatePhaseState.handle |
| 452 | set_heading_hold | roll | FinalPhaseState.handle |
| 493 | set_vertical_speed(-int(vs)) | pitch | FinalPhaseState.handle |
| 523 | set_throttle_asymmetric | throttle | FinalPhaseState.handle |
| 525 | set_throttle | throttle | FinalPhaseState.handle |
| 530 | set_throttle | throttle | FinalPhaseState.handle |
| 540 | set_throttle(0.5) | throttle | FinalPhaseState.handle |
| 601 | set_flaps(2) | configuration | GoAroundPhaseState.handle |
| 607 | set_gear(True) | configuration | GoAroundPhaseState.handle |
| 611 | set_flaps(3) | configuration | GoAroundPhaseState.handle |
| 721 | set_throttle_asymmetric | throttle | LandingPhaseState/Flare |
| 743 | set_throttle | throttle | LandingPhaseState/Flare |
| 746 | set_throttle | throttle | LandingPhaseState/Flare |
| 768 | set_throttle_asymmetric | throttle | LandingPhaseState/Flare |
| 770 | set_throttle | throttle | LandingPhaseState/Flare |
| 772 | set_throttle | throttle | LandingPhaseState/Flare |

**Other modules (via `control` parameter, which IS the gateway):**

| File | Line | Method | Channel |
|---|---|---|---|
| aileron_compensation.py | 177 | set_aileron | roll |
| rudder_compensation.py | 249 | set_rudder | roll |

**Via adapter (bypasses gateway):**

| File | Line | Method |
|---|---|---|
| aircraft_adapter.py | 180,197,203 | set_heading_hold |
| aircraft_adapter.py | 233,249,254 | set_altitude_hold |
| aircraft_adapter.py | 284,290,305,310 | set_vertical_speed |
| aircraft_adapter.py | 390,401,406 | set_nav_hold |
| aircraft_adapter.py | 433,440,450,459,463 | set_autopilot_master(True) |
| aircraft_adapter.py | 485,492,502,511,515 | set_autopilot_master(False) |
| aircraft_adapter.py | 552,566,570 | set_airspeed_hold |

**Via raw_control (bypasses gateway):**

| File | Line | Context |
|---|---|---|
| approach_phases.py | 668 | flare_controller receives `self.system.raw_control` |

### GATEWAY_CORRECTED_INVENTORY

**Summary:**
- **1 scoped callsite in production:** `main.py:431` — `source_scope(SAFETY)` in `execute_go_around()`
- **~30 unscoped callsites in production:** all in `main.py`, `approach_phases.py`, `aileron_compensation.py`, `rudder_compensation.py`
- **~15 adapter callsites:** bypass gateway via `aircraft_adapter.control` (which IS the gateway but called through adapter methods)
- **1 raw_control bypass:** `approach_phases.py:668`
- **Bottom line unchanged:** Default `AIRCRAFT_AP` cannot be changed in P2-A. All unscoped calls rely on it.

---

## WIND_ATTRIBUTION

`RESOLVED_BY_3971ba1 — merge of fix/wind-correction`

---

## FINAL_ID_TABLE

| # | ID | Classification | Wave | Evidence summary |
|---|---|---|---|---|
| 1 | P2-AT-01 | CONFIRMED_P2 | P2-A | `time.time()` wall clock, no dt clamp, integral on anomalous dt |
| 2 | P2/P3-AT-02 | DUPLICATE_OF_P2-AT-01 | — | Same root cause |
| 3 | P3-AT-03 | CONFIRMED_P3 | P3 | Broad `except Exception` in VJoyThrottleIntegration |
| 4 | P2-CM-01 | CONFIRMED_P2 | P2-A | No None/NaN/inf guards in update_flight_phase |
| 5 | P2-CM-02 | CONFIRMED_P2 | P2-B | Boundary gaps (probe-confirmed); owner decision on policy |
| 6 | P2-CM-03 | CONFIRMED_P2 | P2-B | Active test doesn't reset CE; owner decision on semantics |
| 7 | P2/P3-CM-04 | CONFIRMED_P3 | P3 | No hysteresis; mitigated by 20-op minimum |
| 8 | P3-CM-05 | CONFIRMED_P3 | P3 | Decorative profile fields |
| 9 | OPEN-CM-06 | UNPROVEN | — | Method selection I/O impact untraced |
| 10 | P2/P3-CO-01 | CONFIRMED_P3 | P3 | external_at_active always False |
| 11 | P2-CG-01 | CONFIRMED_P2 | P2-B | Default source; staged migration required |
| 12 | TEST-CG-02 | TEST_GAP_ONLY | P2-A | 3 basic tests exist; missing coverage areas |
| 13 | WIND-01 | RESOLVED_BY_3971ba1 | — | corrected_vs = base_vs; deprecated helper unused |
| 14 | REC-01 | CONFIRMED_P2 | P2-B | EngineFailureDetector not instantiated; Stage-1/2 plan |
| 15 | REC-02 | CONFIRMED_P2 | P2-B | ILS no autothrottle.activate(); owner question |
| 16 | REC-03 | RESOLVED_BY_PR6 | — | Weight units fixed |
| 17 | REC-04 | RESOLVED_BY_PR5 | — | GS=0 guard added |
| 18 | REC-05 | RESOLVED_BY_PR5/PR6 | — | G5 finite checks added |
| 19 | REC-06 | TEST_GAP_ONLY | — | No SyntheticGlidepath end-to-end test |
| 20 | F1 | CONFIRMED_P3 | P3 | Direct profile key access |
| 21 | F2 | UNPROVEN | — | event_off correct pattern; config unverified |
| 22 | F3 | UNPROVEN | — | WindowsApps glob dead; runtime impact unknown |
| 23 | F4a | CONFIRMED_P3 | P3 | throttle_reduction_start <= 0 silent |
| 24 | F4b | CONFIRMED_P3 | P3 | height_range <= 0 silent |
| 25 | F4c | CONFIRMED_P3 | P3 | Dead flare_start_time field |
| 26 | F4d | CONFIRMED_P3 | P3 | Hard-coded <10ft |
| 27 | F5a | UNPROVEN | — | preferred_flaps type; config not in repo |
| 28 | F5b | CONFIRMED_P3 | P3 | Gust full velocity comparison |
| 29 | F5c | CONFIRMED_P3 | P3 | Unvalidated flaps config keys |
| 30 | F5d | UNPROVEN | — | VAPP/VREF semantics; domain review needed |
| 31 | F6 | DUPLICATE_OF_CM-05 | — | — |
| 32 | F7a | DESIGN_NOTE | — | evaluate() operations safe; no real defect |
| 33 | F7b | CONFIRMED_P3 | P3 | Fixed rule ordering |
| 34 | F7c | CONFIRMED_P3 | P3 | Snapshot 0.0 from None/NaN |
| 35 | F8 | TEST_GAP_ONLY | — | VOR/NDB fixtures, guard-triggered go-around |

---

## FINAL_COUNTS

| Classification | Count | IDs |
|---|---|---|
| CONFIRMED_P2 | **7** | AT-01, CM-01, CM-02, CM-03, CG-01, REC-01, REC-02 |
| CONFIRMED_P3 | **12** | AT-03, CM-04, CM-05, CO-01, F1, F4a, F4b, F4c, F4d, F5b, F5c, F7b, F7c |
| RESOLVED | **5** | WIND-01, REC-03, REC-04, REC-05, REC-06(WIND) |
| DUPLICATE | **2** | AT-02, F6 |
| UNPROVEN | **5** | OPEN-CM-06, F2, F3, F5a, F5d |
| TEST_GAP_ONLY | **3** | TEST-CG-02, REC-06, F8 |
| DESIGN_NOTE | **1** | F7a |

---

## P2_A: AT-01, CM-01, TEST-CG-02

## P2_B: CG-01, REC-01, REC-02, CM-02, CM-03

---

## REQUIRED_COMMAND_OUTPUTS

```
ruff check: All checks passed! (exit 0)
compileall: All passed (exit 0, no output)
git diff --check: CRLF warnings only on PNG files (exit 0)
git status: 6 modified PNGs + 8 untracked (pre-existing)
```

## FILES_READ (final)

```
modules/autothrottle.py (482 lines)
modules/connection_monitor.py (717 lines)
modules/control_ownership.py (82 lines)
modules/command_gateway.py (74 lines)
modules/wind_correction.py (251 lines)
modules/engine_failure_detector.py (307 lines)
modules/flare_controller.py (317 lines)
modules/approach_speed_calculator.py (300 lines)
modules/safety_guard.py (225 lines)
modules/aircraft_adapter.py (1-524 lines)
modules/aircraft_config_reader.py (401 lines)
modules/approach_phases.py (1-772 lines — full)
modules/autopilot_takeover.py (325-354 lines)
modules/aileron_compensation.py (177 line ref)
modules/rudder_compensation.py (249 line ref)
main.py (64-479 lines — full for gateway-relevant sections)
tests/test_p0_architecture.py (44 lines)
probes_lv/cm02_boundary_probe.py (probe script + output)
probes_lv/cm03_state_probe.py (probe script + output)
```
