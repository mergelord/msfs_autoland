# REC-01 Stage 1 — EngineFailureDetector Hardening

**Task:** REC-01-STAGE1
**Branch:** `fix/rec01-stage1-detector-hardening`
**Base:** `f2b2f364a3cb50596c3f16e4bab471994f97aca5` (origin/master)
**Author:** MiMo
**Status:** Ready for review

---

## Files Changed

`git diff --stat f2b2f364...HEAD`:

```
 TASKS/REVIEWS/REC-01-STAGE1-F2B2F36.md          |  83 +++++
 modules/engine_failure_detector.py              |  82 ++++-
 tests/test_engine_failure_detector_hardening.py | 417 ++++++++++++++++++++++++
 3 files changed, 568 insertions(+), 14 deletions(-)
```

---

## H1/H2/H5 Summary

| Item | Classification | Fix | Verification |
|------|---------------|-----|-------------|
| H1: Monotonic clock | Hard (NTP corruption) | `time.monotonic` default, injectable `clock` kwarg | Fake clock drives confirmation window; >= 3 invariant preserved |
| H2: Input validation | Hard (NaN silent miss) | `_is_valid_number()` rejects NaN/inf/None/bool; rate-limited warnings | All garbage types tested; confirmed failure NOT cleared by garbage |
| H5: Divide-by-zero | Hard (ZeroDivisionError) | Guard before division; `logger.critical`; return all-zero | All-engines-failed returns `{engine_X: 0.0}`, no exception |

---

## Implementation Details

### H1 — Monotonic clock source

- Moved `import time` to module top level.
- Constructor gains keyword-only `clock: Optional[Callable[[], float]] = None`.
- Default: `time.monotonic`. Replaces `time.time()` in `_check_engine_failure`.
- Keyword-only so existing positional callers are unaffected.

### H2 — Input validation

- Added `_is_valid_number(value)` helper: rejects non-finite, non-numeric, and `bool`.
- `_update_single_engine` validates all 6 numeric fields + `running` flag BEFORE mutation.
- Invalid frame policy: preserve previous state, skip `_check_engine_failure`, no `failure_history` mutation.
- Rate-limited warnings: `_warned_fields: set[Tuple[int, str]]` — one warning per `(engine_idx, field)`.

### H5 — Divide-by-zero guard

- Before `compensation_factor = number / len(working_engines)`: check `if not working_engines`.
- Log `logger.critical("ALL ENGINES FAILED — no working engine for asymmetric compensation")`.
- Return `{engine_X: 0.0}` without dividing.

---

## Verification Results

| Check | Result |
|-------|--------|
| `py_compile` | OK |
| `ruff` | All checks passed (0 errors) |
| `mypy` | Success: no issues found |
| `git stash list` | (empty) |
| `git checkout f2b2f36 && pytest -q --tb=no` | **399 passed**, 1 warning (5.66s) |
| `git checkout fix/rec01-stage1-detector-hardening && pytest -q --tb=no` | **438 passed**, 1 warning (5.71s) |
| Arithmetic | 399 base + 39 new = 438 HEAD |
| Detection checks 1-6 | Unchanged (behaviourally identical) |
| Confirmation debounce | Unchanged (only clock source swapped) |
| Public API | Unchanged (additive keyword-only `clock`) |

---

## Non-negotiable invariants — verified

- [x] Detection checks 1-6 (thresholds + reason strings) unchanged
- [x] Confirmation/recovery debounce algorithm unchanged (only clock source swapped, H1)
- [x] No new detection modes, no recovery-hysteresis, no confirmation redesign
- [x] Public API signatures/return types unchanged (except additive keyword-only `clock`)
- [x] No changes outside `engine_failure_detector.py` and its test file

---

## Commit

- Branch: `fix/rec01-stage1-detector-hardening`
- Unsigned (no GPG key available on this machine)
