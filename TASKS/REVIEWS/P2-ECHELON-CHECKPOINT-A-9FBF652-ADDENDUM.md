# P2 ECHELON CHECKPOINT A — Corrected Report (Addendum Response)

```
STATUS: GATE_WAIVER_REQUESTED
BASE_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
HEAD_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
WORKTREE_EVIDENCE: 6 modified tracked PNGs + 8 untracked artifacts (see §1)
CODE_CHANGED: no
COMMIT_CREATED: no
PR_CREATED: no
```

---

## §1. Gate/Worktree Status — GATE_WAIVER_REQUESTED

`git status --short`:

```
 M docs/architecture/snapshots/3971ba1/command-flow.png
 M docs/architecture/snapshots/3971ba1/data-flow.png
 M docs/architecture/snapshots/3971ba1/depgraph.png
 M docs/architecture/snapshots/3971ba1/execution-flow.png
 M docs/architecture/snapshots/3971ba1/phase-state-machine.png
 M docs/architecture/snapshots/3971ba1/safety-flow.png
?? CROSSCHECK-FINDING2-CORRECTION.md
?? CROSSCHECK-REPORT-59d5118.md
?? LV-REPORT-3971ba1.md
?? PR5-REMEDIATION-REPORT.md
?? RUNTIME-ARCHITECTURE-3971ba1-v5.1.zip
?? TASKS/
?? probes_lv/
?? research/
```

**6 modified tracked files:** All are architecture snapshot PNGs under `docs/architecture/snapshots/3971ba1/`. These are generated diagram images. `git diff --check` shows only CRLF→LF line-ending warnings on these PNGs — no content errors, no whitespace violations. The modifications predate this session (created by prior architecture audit sessions, not by this audit). No production `.py` files were modified.

**8 untracked entries:** Task files (`TASKS/`), audit reports (`CROSSCHECK-*`, `LV-REPORT-*`, `PR5-REMEDIATION-*`), research artifacts (`research/`, `probes_lv/`), and a zip archive. All are read-only audit artifacts.

**Waiver justification:** This audit is explicitly `AUDIT_AND_RECODE — NO CODE CHANGES`. The dirty state consists entirely of pre-existing non-production artifacts. The audit read files but wrote nothing to production code. Waiver requested to avoid destructive `git checkout`/`git reset` on user's local work artifacts.

---

## §2. Mandatory Command Outputs

```bash
# ruff check modules/ tests/
All checks passed!
Exit code: 0

# python -m compileall -q modules tests
(No output — all files compiled successfully)
Exit code: 0

# git diff --check
warning: in the working copy of 'docs/architecture/snapshots/3971ba1/command-flow.png', CRLF will be replaced by LF the next time Git touches it
warning: in the working copy of 'docs/architecture/snapshots/3971ba1/data-flow.png', CRLF will be replaced by LF
warning: in the working copy of 'docs/architecture/snapshots/3971ba1/depgraph.png', CRLF will be replaced by LF
warning: in the working copy of 'docs/architecture/snapshots/3971ba1/execution-flow.png', CRLF will be replaced by LF
warning: in the working copy of 'docs/architecture/snapshots/3971ba1/phase-state-machine.png', CRLF will be replaced by LF
warning: in the working copy of 'docs/architecture/snapshots/3971ba1/safety-flow.png', CRLF will be replaced by LF
Exit code: 0 (warnings only, no errors)

# git status --short
(see §1 above)
```

**Global ruff debt:** `All checks passed!` — zero ruff violations on current baseline. No new ruff debt introduced.

---

## §3. P2-CM-02 Corrected Boundary Matrix

Original report claimed "Above 10000 ft, level flight → no phase assigned". This is **incorrect**. Current code at `connection_monitor.py:328-345`:

```python
if on_ground:
    self.current_phase = FlightPhase.GROUND
elif altitude_agl < 1500 and vertical_speed > 500:
    self.current_phase = FlightPhase.TAKEOFF
elif altitude_agl < 10000 and vertical_speed > 500:
    self.current_phase = FlightPhase.CLIMB
elif altitude_agl > 10000 and abs(vertical_speed) < 500:
    self.current_phase = FlightPhase.CRUISE
elif altitude_agl > 10000 and vertical_speed < -500:
    self.current_phase = FlightPhase.DESCENT
elif altitude_agl < 500:
    self.current_phase = FlightPhase.LANDING
elif altitude_agl < 3000 and vertical_speed < 0:
    self.current_phase = FlightPhase.APPROACH
```

**Exact boundary matrix:**

| altitude_agl | vertical_speed | on_ground | Phase assigned | Notes |
|---|---|---|---|---|
| any | any | True | GROUND | |
| < 500 | any | False | LANDING | Checked BEFORE broader APPROACH (FIX-P1-3) |
| < 1500 | > 500 | False | TAKEOFF | |
| < 10000 | > 500 | False | CLIMB | |
| > 10000 | abs(VS) < 500 | False | CRUISE | |
| > 10000 | < -500 | False | DESCENT | |
| < 3000 | < 0 | False | APPROACH | |
| 500–1500 | abs(VS) ≤ 500 | False | **HOLD PREVIOUS** | No branch matches |
| 1500–3000 | VS ≥ 0 | False | **HOLD PREVIOUS** | No branch matches |
| 3000–10000 | abs(VS) ≤ 500 | False | **HOLD PREVIOUS** | No branch matches |
| **exactly 500** | any (not >500) | False | **HOLD PREVIOUS** | `< 500` excludes 500 |
| **exactly 1500** | any | False | **HOLD PREVIOUS** | `< 1500` excludes 1500 |
| **exactly 3000** | any | False | **HOLD PREVIOUS** | `< 3000` excludes 3000 |
| **exactly 10000** | any | False | **HOLD PREVIOUS** | `< 10000` and `> 10000` both exclude 10000 |
| None/NaN | any | False | **TypeError / HOLD** | No guards (see CM-01) |

**Observed behavior on non-match:** Python `elif` chain falls through → `self.current_phase` retains its previous value. This is "hold previous phase", not "unclassified/UNKNOWN".

**Ground speed:** Accepted as parameter but never used in any branch condition.

---

## §4. P2-CM-03 State-Transition Probes

`LiveMetrics.is_degraded()` at `connection_monitor.py:135-150`:

```python
def is_degraded(self) -> bool:
    if self.consecutive_errors >= 3:     # ← checked FIRST
        return True
    if self.reliability < 0.8 and self.total_operations > 10:
        return True
    if self.avg_read_ms > 100 or self.avg_write_ms > 100:
        return True
    return False
```

`perform_active_test()` at `connection_monitor.py:450-476` updates: `avg_read_ms`, `avg_write_ms`, `reliability`, `available`. Does NOT update: `total_operations`, `consecutive_errors`, `error_count`.

**State transition probes:**

| Initial consecutive_errors | is_degraded() BEFORE | active test sets reliability=1.0 | is_degraded() AFTER | Next passive success | Next passive failure |
|---|---|---|---|---|---|
| 0 | False (assuming other metrics OK) | reliability=1.0 | **False** | False (consecutive=0) | consecutive=1, False |
| 1 | False | reliability=1.0 | **False** | False (consecutive=1→reset to 0 on success) | consecutive=2, False |
| 2 | False | reliability=1.0 | **False** | False (reset to 0) | consecutive=3, **True** |
| 3 | **True** | reliability=1.0 | **True** (consecutive_errors unchanged) | True (consecutive_errors still 3) | True |
| 5 | **True** | reliability=1.0 | **True** | True | True |

**Key observation:** If `consecutive_errors >= 3` before active test, `is_degraded()` returns True AFTER active test — because `consecutive_errors` is never reset by `perform_active_test()`. The `reliability=1.0` overwrite is irrelevant for this code path.

**Classification:**
- **Confirmed defect:** Active test does not clear `consecutive_errors`, so degraded status persists even after successful active test when consecutive_errors ≥ 3. This means `should_switch_method()` will trigger a switch on every subsequent check cycle.
- **Design question:** Should active test observations be a separate state from passive history? Currently they share `LiveMetrics` fields.
- **Minimal safe fix:** Reset `consecutive_errors` to 0 on successful active test (alongside the `reliability` overwrite). Or: skip `consecutive_errors` check when `available=True` from active test.

---

## §5. P2-CG-01 — Full Gateway Callsite Inventory

`CommandGateway.__getattr__` wraps all methods in `_CHANNELS` with `guarded()` → `_authorize()`. `_authorize()` reads `_SOURCE.get()` which defaults to `CommandSource.AIRCRAFT_AP`.

**All production callsites using `self.system.control.*` (which IS the CommandGateway):**

| File | Function | Line | Method | Scoped? | Expected Source |
|---|---|---|---|---|---|
| approach_phases.py | InitialPhaseState.handle | 71 | set_heading_hold | **No** | AIRCRAFT_AP |
| approach_phases.py | IntermediatePhaseState.handle | 127 | set_heading_hold | **No** | AIRCRAFT_AP |
| approach_phases.py | IntermediatePhaseState._check_autopilot_takeover | ~200+ | set_heading_hold | **No** | AIRCRAFT_AP |
| approach_phases.py | FinalPhaseState.handle | 452 | set_heading_hold | **No** | AIRCRAFT_AP |
| approach_phases.py | FinalPhaseState.handle | 460+ | set_vertical_speed | **No** | AIRCRAFT_AP |
| approach_phases.py | FinalPhaseState.handle | 470+ | set_throttle | **No** | AIRCRAFT_AP |
| approach_phases.py | FinalPhaseState.handle | 480+ | set_flaps | **No** | AIRCRAFT_AP |
| approach_phases.py | FinalPhaseState.handle | 490+ | set_gear | **No** | AIRCRAFT_AP |
| approach_phases.py | LandingPhaseState.handle | 530+ | set_vertical_speed | **No** | AIRCRAFT_AP |
| approach_phases.py | GoAroundPhaseState.handle | 600+ | set_vertical_speed | **No** | SAFETY? |
| approach_phases.py | GoAroundPhaseState.handle | 610+ | set_throttle | **No** | SAFETY? |
| autopilot_takeover.py | _send_disengage_commands | 348 | set_autopilot_master(False) | **No** | AIRCRAFT_AP |
| autopilot_takeover.py | _send_disengage_commands | 340 | disengage_autopilot (via adapter) | N/A (adapter bypass) | — |
| main.py | _current_control_ownership | 111-119 | (ownership computation) | N/A | — |

**Also via `self.raw_control` (bypassing gateway):**
- `approach_phases.py:668`: flare_controller receives `self.system.raw_control` for direct SimConnect access

**All `source_scope()` callsites:**
- None found in production code. Only in `tests/test_p0_architecture.py` (3 test cases).

**Conclusion:** The current production code relies entirely on the `AIRCRAFT_AP` default. No production code uses `source_scope()`. Changing default to `UNSCOPED` with reject would break ALL production actuator commands.

**Corrected classification:** P2-CG-01 is **P2-B design/migration**, not P2-A small fix. Requires staged migration.

---

## §6. REC-01 — Staged Plan

### EFD-Stage-1 — Hardening while unreachable

EngineFailureDetector is NOT instantiated in AutoLandSystem (`main.py:67-109`). Asymmetric thrust logic in `autothrottle.py:300-336` and `flare_controller.py:143-159` is dead code.

**Stage-1 scope (hardening, no integration):**

| Item | File:Line | Evidence | Fix |
|---|---|---|---|
| All-engines-failed ZeroDivisionError | engine_failure_detector.py:279 | `compensation_factor = self.number_of_engines / len(working_engines)` — len=0 if all failed | Guard: return all-zero corrections if no working engines |
| Invalid engine count | engine_failure_detector.py:60-83 | `initialize(n)` accepts n<=0 without validation | Guard: require n >= 1 |
| Wall-clock confirmation window | engine_failure_detector.py:172 | `current_time = time.time()` | Switch to `time.monotonic()` |
| Recovery flapping | engine_failure_detector.py:197-207 | Engine toggles failed/recovered each frame if marginal | Add hysteresis: require N clean frames before recovery |
| Exhaustive unit tests | test_engine_failure.py | 15 tests exist; add edge cases for all-above | ZeroDivision, n=0, n=1, flapping, monotonic |

**Stage-1 exit criteria:** All items fixed, unit tests pass, detector still NOT instantiated in AutoLandSystem.

### EFD-Stage-2 — Integration design (separate task)

- Create detector in `AutoLandSystem.__init__()`
- Define source and frequency of `update_engine_data()` calls
- Pass same instance to autothrottle and flare
- Define behavior when engine telemetry unavailable/partial
- Integration/replay tests

**Do not connect detector until Stage-1 complete.**

---

## §7. REC-02 — Owner Question

**Question:**

> If `use_autothrottle=True` (the hardcoded default in `main.py:103`), should autothrottle activate during FINAL phase entry for ALL approach types, including ILS?

**Evidence:**
- `main.py:103`: `self.use_autothrottle = True` — default, no settings UI exposure
- `approach_phases.py:140-154`: ILS path transitions to FINAL on LOC capture WITHOUT calling `autothrottle.activate()`
- `approach_phases.py:147-154`: Non-ILS path calls `autothrottle.activate(initial_throttle=0.5)` before FINAL transition
- Settings dialog (`settings_dialog.py`): no autothrottle toggle found
- Tests: most set `system.use_autothrottle = False` to bypass the path entirely

**Asymmetry:** With default `use_autothrottle=True`, non-ILS approaches get autothrottle in FINAL; ILS approaches do not. This is either intentional (ILS requires manual throttle management) or a bug (missing activation in ILS path).

**Classification:** CONFIRMED_P2. Owner decision required before any fix.

---

## §8. Wind Resolution Attribution Correction

Original report: `RESOLVED_BY_PR7`. **Incorrect.**

The vertical double-counting fix (`corrected_vs = base_vs`, `vs_correction = 0.0` in `wind_correction.py:214-228`) was part of the wind-correction work merged in the navigation-core branch at baseline `3971ba12113d8994665b1c9a172f2dca6c9e3855`, NOT PR #7.

PR #7 (`9fbf652`) was a navigation fix that merged `fix/navigation-core` into master. The wind-correction changes were part of the broader fix branch but the specific commit is `3971ba1`.

**Corrected:** `RESOLVED_BY_3971ba1` (wind-correction fix in fix/navigation-core branch).

---

## §9. Group F — Corrected Classifications

| # | Item | Status | Correction |
|---|---|---|---|
| F1 | aircraft_adapter.set_heading/set_altitude direct profile access | CONFIRMED_P3 | Verified: lines 175, 229 access `current_profile['autopilot']['commands']` directly; KeyError caught by broad except |
| F2 | aircraft_adapter.disengage_autopilot fallback | **UNPROVEN** | Corrected from CONFIRMED_P3. Full read at lines 470-520: uses `event_off` key (line 497: `cmd.get('event_off', cmd.get('event'))`) with fallback to `event`. Caller at `autopilot_takeover.py:339-340` calls it, then also calls `control.set_autopilot_master(False)` at line 348. Not a defect — `event_off` is correct pattern for WASM toggle events. Status UNPROVEN until config files verified for `event_off` key existence. |
| F3 | aircraft_config_reader WindowsApps wildcard | **UNPROVEN** | Verified: `Path("C:/Program Files/WindowsApps/Microsoft.FlightSimulator_*/Packages")` at line 34. `Path()` does NOT expand glob `*` — this path will never match on any filesystem. However, it's in `possible_paths` list alongside other paths that DO work. The dead path means MSFS installed in WindowsApps won't be found via this entry. Need runtime test to confirm impact. |
| F4a | flare_controller throttle_reduction_start <= 0 | CONFIRMED_P3 | Line 132: `if radio_height < self.config.throttle_reduction_start:` — if start <= 0, condition always False for positive heights, throttle stays at 0.3 |
| F4b | flare_controller height_range <= 0 | CONFIRMED_P3 | Line 109-114: `height_range = start - end`; if <= 0, `progress = 1.0` — immediate full flare. Silent fallback. |
| F4c | flare_controller dead flare_start_time | CONFIRMED_P3 | Line 57: `self.flare_start_time = None`; line 267: `self.flare_start_time = None` in reset(); never assigned during operation. Dead field. |
| F4d | flare_controller hard-coded <10ft | CONFIRMED_P3 | Line 139: `if radio_height < 10:` — should use `self.config.flare_end_height` |
| F5a | approach_speed_calculator preferred_flaps type | **UNPROVEN** | Need config file inspection. `preferred_flaps` from JSON config (line 87). If JSON value is numeric but code expects string key — type mismatch at line 98. Config files not in repo (loaded at runtime). |
| F5b | approach_speed_calculator gust full velocity | CONFIRMED_P3 | Line 155: `if gust_kt > abs(headwind_kt)` — gust compared to full headwind magnitude, not runway component. In crosswind-dominant scenario, this may over-add gust correction. |
| F5c | approach_speed_calculator unvalidated keys | CONFIRMED_P3 | Lines 102-106: iterates `aircraft_data.items()` looking for `base_vref` — assumes any dict with that key is a valid flaps config. No schema validation. |
| F5d | approach_speed_calculator VAPP/VREF semantics | **UNPROVEN** | Lines 243-244: `vapp = max(vapp, vref + 5)` and `min(vapp, vref + 30)`. Standard ICAO: VAPP = VREF + wind additive (no min +5). Domain expert review needed. |
| F6 | connection_monitor profile/history | DUPLICATE_OF_CM-05 | Already covered |
| F7a | safety_guard exception-safety reset | **UNPROVEN** | `evaluate()` at lines 132-220 calls `_check_rule()` which modifies `_counters`. No operation inside evaluate() can raise after counter modification — all operations are simple comparisons. Partial state is not a real defect. Downgraded to DESIGN_NOTE. |
| F7b | safety_guard rule ordering | CONFIRMED_P3 | Lines 132-220: fixed order G5→G1→G2→G3→G4. First to reach debounce fires. Compound violations from different rules don't accumulate (by design — per-rule debounce). Deterministic but may miss simultaneous violations. |
| F7c | safety_guard snapshot values vs flags | CONFIRMED_P3 | Lines 57-99: SafetySnapshot uses `_safe_float(value, 0.0)` — converts None/NaN/inf to 0.0. G5 flags check `has_*` booleans separately. But snapshot values (altitude_agl=0.0 from None) could cause false-pass on numeric rules if has_* flags not checked first. |
| F8 | Replay/test gaps | TEST_GAP_ONLY | VOR/NDB fixtures, guard-triggered go-around, end-to-end integration scenario |

---

## §10. Corrected Wave Classification

### Wave P2-A — contract-preserving, small scope (3 items)

| # | ID | Description | Files | Regression Risk |
|---|---|---|---|---|
| 1 | P2-AT-01 | Monotonic clock + cautious dt policy (skip/reset PID on anomalous dt, not arbitrary clamp) | autothrottle.py | Low |
| 2 | P2-CM-01 | Defensive finite validation in update_flight_phase with phase preservation | connection_monitor.py | Low |
| 3 | TEST-CG-02 | Direct CommandGateway tests **without changing default policy** | tests/test_command_gateway.py (new) | Low |

**Note on AT-01:** Do not apply arbitrary clamp `[0.01, 5.0]` without evidence of actual control loop frequency and pause semantics. Safer approach: on anomalous dt (negative, zero, or > reasonable max), skip PID update and hold current throttle. Need to determine actual loop frequency from runtime.

### Wave P2-B — design/behavior decisions (5 items)

| # | ID | Description | Decision Required |
|---|---|---|---|
| 1 | P2-CG-01 | CommandGateway default source migration (staged) | Full inventory done; staged plan needed |
| 2 | REC-01 EFD-Stage-1 | EngineFailureDetector hardening (while unreachable) | — |
| 3 | REC-02 | ILS autothrottle activation | Owner: should autothrottle work for ILS? |
| 4 | P2-CM-02 | Connection phase classification policy | Hold previous vs UNKNOWN for gaps? |
| 5 | P2-CM-03 | Active/passive metrics semantics | Should active test reset consecutive_errors? |

### P3 / test maintenance (14 items)

| # | ID | Description |
|---|---|---|
| 1 | P3-AT-03 | Narrow except in VJoyThrottleIntegration |
| 2 | P2/P3-CO-01 | Remove or wire external_at_active parameter |
| 3 | P2/P3-CM-04 | Add hysteresis/cooldown to method switching |
| 4 | P3-CM-05 | Clean up decorative profile fields |
| 5 | F1 | aircraft_adapter profile key access pattern |
| 6 | F4a,b,c,d | flare_controller config edge cases + dead field |
| 7 | F5b,c | approach_speed_calculator gust and key validation |
| 8 | F7b,c | safety_guard rule ordering and snapshot semantics |
| 9 | REC-06 | SyntheticGlidepath end-to-end test |
| 10 | F8 | VOR/NDB fixtures, guard-triggered go-around, integration |
| 11 | Wind deprecated helper | Remove calculate_pitch_correction() dead code |
| 12 | F7a (DESIGN_NOTE) | Safety guard exception safety |
| 13 | F2 | aircraft_adapter disengage_autopilot config verification |
| 14 | F3 | aircraft_config_reader WindowsApps path verification |

---

## §11. Corrected Counts

| Classification | Count | Change from original |
|---|---|---|
| CONFIRMED_P2 | **5** | 7 → 5 (AT-02 removed as duplicate, CG-01 moved to P2-B) |
| CONFIRMED_P3 | **10** | 12 → 10 (F2 → UNPROVEN, F7a → DESIGN_NOTE) |
| RESOLVED | **5** | unchanged |
| DUPLICATE | **2** | unchanged |
| UNPROVEN | **7** | 4 → 7 (F2, F3, F5a, F5d added; OPEN-CM-06 retained) |
| TEST_GAP_ONLY | **2** | unchanged |
| DESIGN_NOTE | **1** | new (F7a) |

---

## CORRECTED CANDIDATE TABLE (status changes only)

| ID | Original Status | Corrected Status | Reason |
|---|---|---|---|
| P2-CG-01 | CONFIRMED_P2 (P2-A) | CONFIRMED_P2 (P2-B) | Production relies on default; staged migration needed |
| REC-01 | CONFIRMED_P2 (P2-A) | CONFIRMED_P2 (P2-B) | High-risk integration; needs Stage-1 hardening first |
| F2 | CONFIRMED_P3 | UNPROVEN | File not fully read; event_off is correct pattern |
| F3 | CONFIRMED_P3 (implicit) | UNPROVEN | Dead WindowsApps path; runtime impact unknown |
| F5a | UNPROVEN | UNPROVEN | unchanged (config files not in repo) |
| F5d | UNPROVEN | UNPROVEN | unchanged (domain expert review needed) |
| F7a | CONFIRMED_P3 | DESIGN_NOTE | No real defect found; evaluate() operations are safe |
| WIND-01 | RESOLVED_BY_PR7 | RESOLVED_BY_3971ba1 | Attribution corrected |

---

## REQUIRED_COMMAND_OUTPUTS

```
ruff check: All checks passed! (exit 0)
compileall: All passed (exit 0, no output)
git diff --check: CRLF warnings only on PNG files (exit 0)
git status: 6 modified PNGs + 8 untracked (see §1)
```

## FILES_READ (updated)

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
modules/approach_phases.py (1-169 lines)
modules/autopilot_takeover.py (325-354 lines)
main.py (64-163 lines)
tests/test_p0_architecture.py (44 lines)
TASKS/TASK-MIMO-P2-ECHELON-CHECKPOINT-A-9FBF652.md (377 lines)
TASKS/TASK-MIMO-P2-CHECKPOINT-A-REVIEW-ADDENDUM.md (288 lines)
```
