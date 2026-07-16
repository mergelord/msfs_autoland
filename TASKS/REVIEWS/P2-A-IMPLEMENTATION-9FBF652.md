# P2-A Implementation Report

```
STATUS: COMPLETED_NOT_PUSHED
BASE_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
BRANCH: fix/p2a-contract-preserving
COMMIT_SHA: f52a330a8fd13da3c28fc2eec66b2d0303e4071e
PARENT_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
PR_URL: none
CHANGED_FILES: modules/autothrottle.py, modules/connection_monitor.py, tests/test_autothrottle_pid_timing.py, tests/test_command_gateway.py, tests/test_connection_monitor_defensive.py
```

---

## AT01_DESIGN

- **Clock injection:** `AutothrottleController(..., *, clock: Optional[Callable[[], float]] = None)` — keyword-only, defaults to `time.monotonic`. Backward compatible (all existing callers pass no `clock`).
- **Threshold:** `AutothrottleConfig.max_pid_dt_seconds = 2.0` — documented default, considers nominal 0.5s loop + 1.0s retry. Validated at init: must be finite and > 0.
- **Anomaly policy:** On dt that is non-finite, <= 0, or > max_pid_dt_seconds: set dt=0.0 (freezes I and D), log WARNING, preserve P-term and throttle output. Previous_time updated to current so next normal frame recovers without derivative spike.

## CM01_CONTRACT

- `on_ground=True` → GROUND immediately, regardless of altitude/VS validity.
- `on_ground=False` + non-finite altitude/VS (None, NaN, inf, -inf, bool, str, object) → log WARNING, preserve previous phase, return without classification.
- Boundary behavior byte-for-behavior compatible with Checkpoint A probe matrix.
- `ground_speed` unused and untouched (P3 debt).

## CG02_TESTS

15 tests in `tests/test_command_gateway.py`:

| # | Test | Validates |
|---|---|---|
| 1 | test_ap_owner_unscoped_allowed | AP default contract |
| 2 | test_external_owner_unscoped_rejected | Fail-closed for EXTERNAL |
| 3 | test_external_owner_explicit_scope_allowed | Explicit scope works |
| 4 | test_ap_owner_external_scope_rejected | Scope mismatch rejected |
| 5 | test_safety_scope_bypasses_authorization | SAFETY always allowed |
| 6 | test_scope_restores_after_normal_exit | ContextVar restore |
| 7 | test_scope_restores_after_exception | Exception safety |
| 8 | test_nested_scopes_lifo | LIFO restoration |
| 9 | test_guarded_closure_authorizes_at_call_time | Closure captures behavior |
| 10 | test_contextvar_isolation | Separate instances isolated |
| 11 | test_config_channels | flaps/gear channels |
| 12 | test_nav_channels | nav/adf/obs channels |
| 13 | test_autopilot_channels | AP/nav/approach/speed |
| 14 | test_readback_method_not_guarded | Non-channel passthrough |
| 15 | test_unknown_method_delegated | Unknown method passthrough |

---

## RED_WITHOUT_FIX

```bash
# AT-01: clock parameter doesn't exist
python -m pytest tests/test_autothrottle_pid_timing.py::test_clock_injection -v
# FAILED: TypeError: AutothrottleController.__init__() got an unexpected keyword argument 'clock'

# CM-01: None altitude causes TypeError
python -m pytest tests/test_connection_monitor_defensive.py::test_none_altitude_would_cause_type_error -v
# FAILED: TypeError: '<' not supported between instances of 'NoneType' and 'int'

# CG-02: No test module existed
# (tests/test_command_gateway.py did not exist before this PR)
```

## TARGETED_TESTS

```bash
# AT-01
tests/test_autothrottle_pid_timing.py: 10 passed

# CM-01
tests/test_connection_monitor_defensive.py: 20 passed

# CG-02
tests/test_command_gateway.py: 15 passed

# Existing autothrottle tests (regression)
tests/test_autothrottle.py: 10 passed

# Existing P0 architecture tests (regression)
tests/test_p0_architecture.py: 7 passed
```

## FULL_TESTS

```
391 passed, 1 warning in 5.65s
Baseline was 346 passed, 1 warning → +45 new tests, 0 regressions
```

## RUFF

```
All checks passed!
```

## PY_COMPILE

```
modules/autothrottle.py: OK
modules/connection_monitor.py: OK
```

## DIFF_CHECK

```
CRLF warnings only (pre-existing PNG files + connection_monitor.py line ending)
No actual errors.
```

## CI_CHECKS

- test 3.12: pending (not pushed)
- test 3.13: pending (not pushed)
- mypy: pending
- bandit: pending
- radon: pending
- validate architecture snapshot: pending
- Pre-existing: lint-ruff, check-architecture-freshness

## LEDGER_COUNTS

P2=7, P3=13, RESOLVED=4, DUPLICATE=2, UNPROVEN=5, TEST_GAP=3, DESIGN_NOTE=1

## REPORT_PATH

TASKS/REVIEWS/P2-A-IMPLEMENTATION-9FBF652.md

## MERGED

no
