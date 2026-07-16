## Summary

P2-CG-01 Stage 1: Observability + explicit nominal scoping. Prepares fail-closed migration of the gateway ContextVar default WITHOUT changing any authorization outcome.

### What changed

**modules/command_gateway.py:**
- `_SOURCE` ContextVar default changed from `CommandSource.AIRCRAFT_AP` to `None`
- `_authorize()` maps `None` to `AIRCRAFT_AP` (contract-preserving) and emits a rate-limited WARNING per method name
- Added `_warned_methods` set for rate limiting and `_unscoped_methods` set for observability
- Added `unscoped_call_names` frozenset accessor for Stage 2 readiness evidence

**main.py:**
- Wrapped `_handle_phase()` call in `source_scope(CommandSource.AIRCRAFT_AP)` at the `execute_approach()` loop boundary — ONE place, not 30 individual callsites
- `execute_go_around()` keeps its existing SAFETY scope (untouched)

### What did NOT change

- All authorization outcomes identical to base (None == AIRCRAFT_AP)
- `_CHANNELS`, `_expected_owner`, `__getattr__` passthrough, `raw_control` unchanged
- `execute_go_around()` SAFETY scope untouched
- No scopes added in threads/callbacks (ContextVar non-inheritance is intentional — warnings reveal those paths)

## Test Results

```
399 passed, 1 warning (baseline: 391 -> +8 new, 0 regressions)
Ruff: All checks passed
py_compile: OK
```

## Changed Files

```
 modules/command_gateway.py              |  33 ++-
 main.py                                 |   3 +-
 tests/test_command_gateway_stage1.py    | 191 +++++++++++++++++++++++++++++++
 3 files changed, 211 insertions(+), 2 deletions(-)
```

## Review focus

- Verify `None` → `AIRCRAFT_AP` mapping in `_authorize()` is byte-identical to previous behavior for all (source, owner, method) combinations
- Verify rate-limited warning fires correctly (once per method name)
- Verify `source_scope(AIRCRAFT_AP)` at loop boundary covers all control dispatch paths
- Verify `execute_go_around()` SAFETY scope is untouched
- Verify thread isolation: ContextVar non-inheritance means threads see `None` default

## Stage 2 readiness

After Stage 1 is merged and telemetry shows zero unscoped warnings in real runs, Stage 2 will flip the default to fail-closed (reject unscoped channel commands). The `unscoped_call_names` accessor provides the evidence needed.
