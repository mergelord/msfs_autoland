# P2-CG-01 Stage 1 Implementation Report

```
STATUS: COMPLETED_NOT_PUSHED
BASE_SHA: 27d0c99afbf65440f09be0d59dfc1fd68a2b7a69
BRANCH: fix/p2cg01-stage1-observability
COMMIT_SHA: 56cedb2
PARENT_SHA: 27d0c99afbf65440f09be0d59dfc1fd68a2b7a69
PR_URL: https://github.com/zhuk-mou-1/msfs_autoland/pull/9
CHANGED_FILES: modules/command_gateway.py, main.py, tests/test_command_gateway_stage1.py
```

## Changes

**modules/command_gateway.py:**
- `_SOURCE` default: `CommandSource.AIRCRAFT_AP` → `None`
- `_authorize()`: `None` mapped to `AIRCRAFT_AP` + rate-limited WARNING
- `_warned_methods: set` for rate limiting
- `_unscoped_methods: set` for observability
- `unscoped_call_names` frozenset accessor

**main.py:**
- `execute_approach()`: `_handle_phase()` wrapped in `source_scope(CommandSource.AIRCRAFT_AP)`

## Tests

8 new tests in `tests/test_command_gateway_stage1.py`:
1. Unscoped call authorized as AP with warning
2. Warning once per method name
3. Explicit scope no warning
4. SAFETY scope no warning
5. EXTERNAL unscoped rejection unchanged
6. Scope exit restores None default
7. Thread isolation sees None default
8. Unscoped call counter

## Gates

```
pytest: 399 passed, 1 warning (baseline 391 + 8 new, 0 regressions)
ruff: All checks passed
py_compile: OK
git diff --check: CRLF warnings only
WORKTREE: clean (modified PNGs pre-existing)
```

## RED_WITHOUT_FIX

```bash
# Tests 1, 2, 4, 8 fail against base 27d0c99:
# - No warning emitted (default was AIRCRAFT_AP, not None)
# - unscoped_call_names attribute doesn't exist
```
