## Summary

Wave P2-A contract-preserving fixes from Checkpoint A audit. Three independent, minimal-scope changes with no behavior redesign.

### P2-AT-01: Monotonic PID timing
- Replaced `time.time()` with `time.monotonic()` (default) in `AutothrottleController`
- Added injectable `clock` parameter for deterministic testing
- Added `max_pid_dt_seconds` config (default 2.0s) with validation
- Anomalous dt (non-finite, negative, too large) freezes I/D, logs warning, preserves P-term
- 10 new tests

### P2-CM-01: Defensive flight-phase inputs
- `update_flight_phase()` now guards against None/NaN/inf/str/bool/object inputs
- Invalid inputs preserve previous phase with warning instead of raising TypeError
- `on_ground=True` works even with missing numeric values
- Boundary behavior byte-for-behavior compatible with Checkpoint A probe matrix
- 20 new tests

### TEST-CG-02: Direct CommandGateway test coverage
- 15 tests covering authorization, scopes, ContextVar isolation
- AP/EXTERNAL/SAFETY scope interactions, nested scopes, exception recovery
- Config/nav/autopilot channel coverage, readback/helper delegation

## Test Results

```
391 passed, 1 warning (baseline: 346 -> +45 new, 0 regressions)
Ruff: All checks passed
py_compile: OK
```

## Changed Files

```
 modules/autothrottle.py                    |  33 ++-
 modules/connection_monitor.py              |  46 ++--
 tests/test_autothrottle_pid_timing.py      | 308 +++++++++++++++++++++++++++
 tests/test_command_gateway.py              | 324 +++++++++++++++++++++++++++++
 tests/test_connection_monitor_defensive.py | 298 ++++++++++++++++++++++++++
 5 files changed, 988 insertions(+), 21 deletions(-)
```

## Review focus

- Verify monotonic clock default is correct for MSFS SimConnect timing
- Verify `max_pid_dt_seconds=2.0` threshold is appropriate for 0.5s nominal loop + 1.0s retry
- Verify CM-01 validation doesn't change existing boundary behavior (probe-verified)
- Verify CG-02 tests accurately document current CommandGateway contract (default AIRCRAFT_AP)

## Scope exclusions

This PR intentionally does NOT include:
- CM-02 phase classification redesign (P2-B owner decision needed)
- CM-03 active/passive metrics semantics (P2-B)
- CG-01 default source migration (P2-B staged plan)
- REC-01 EngineFailureDetector hardening (P2-B)
- REC-02 ILS autothrottle activation (P2-B owner decision)
- Any P3 cleanup
