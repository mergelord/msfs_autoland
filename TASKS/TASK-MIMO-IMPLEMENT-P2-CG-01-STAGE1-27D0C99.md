# TASK-MIMO-IMPLEMENT-P2-CG-01-STAGE1-27D0C99

STATUS: ASSIGNED
BASE: 27d0c99afbf65440f09be0d59dfc1fd68a2b7a69 (origin/master, PR #8 merge)
BRANCH: fix/p2cg01-stage1-observability
SCOPE ID: P2-CG-01 Stage 1 (observability + explicit nominal scoping)
HARD SCOPE: modules/command_gateway.py, main.py (only loop-boundary scoping),
            new tests. NOTHING else. No behavior change in authorization outcomes.

## Objective

Prepare fail-closed migration of the gateway ContextVar default WITHOUT changing
any authorization outcome. Make every unscoped command path observable.

Stage 2 (separate future task, NOT in this scope): flip the default to
fail-closed (reject unscoped channel commands) — only after Stage-1 telemetry
shows zero unscoped warnings in real runs.

## Required changes

### 1. modules/command_gateway.py — sentinel default + warning

- Change: `_SOURCE = ContextVar("autoland_command_source", default=None)`
- In `_authorize(name)`:
  - `source = _SOURCE.get()`
  - If `source is None`: treat EXACTLY as `CommandSource.AIRCRAFT_AP` for the
    authorization decision (contract-preserving), and emit a rate-limited
    WARNING: unscoped command, implicit AIRCRAFT_AP default, will become
    fail-closed in Stage 2. Include the method name.
  - CAUTION: simply changing the default would send `None` into the existing
    branch `actual = AIRCRAFT_AP if source == AIRCRAFT_AP else EXTERNAL`,
    turning unscoped calls into EXTERNAL — a real behavior change. `None` MUST
    be explicitly mapped to AIRCRAFT_AP.
  - Rate limit: warn at most once per method name per process
    (module- or instance-level set of already-warned names; document choice).
  - SAFETY bypass and EXTERNAL mapping: byte-identical behavior.
- `source_scope()` unchanged.
- Add a test-visible counter or accessor for "unscoped invocations seen"
  (e.g. `gateway.unscoped_call_names` frozen copy) — needed for Stage-2
  readiness evidence and tests.

### 2. main.py — explicit nominal scope at loop boundary

- Wrap the per-iteration control dispatch of the MAIN loop
  (`execute_approach`) in
  `with gateway.source_scope(CommandSource.AIRCRAFT_AP):` — ONE place at the
  iteration boundary, NOT 30 individual callsites.
- Do NOT touch `execute_go_around()` (keeps its SAFETY scope).
- Do NOT add scopes in other threads/callbacks (GUI, monitors): ContextVar is
  NOT inherited across threads, and Stage 1 must REVEAL those paths via
  warnings, not mask them.

## Invariants (violation = task failure)

- Every authorization outcome (allow/reject) identical to base for every
  (source, owner, method) combination, including source=None ≡ AIRCRAFT_AP.
- All 391 existing tests pass UNMODIFIED, including the 15 in
  tests/test_command_gateway.py from PR #8.
- No changes to `_CHANNELS`, `_expected_owner`, `__getattr__` passthrough for
  non-channel methods, `raw_control`.

## New tests (tests/test_command_gateway_stage1.py)

1. Unscoped call → still authorized as AP (allowed under AP ownership),
   WARNING emitted.
2. Warning emitted once per method name (two unscoped calls to same method →
   one warning; different method → new warning).
3. Explicitly scoped AIRCRAFT_AP call → NO warning.
4. SAFETY scope → bypass, no warning.
5. EXTERNAL unscoped-owner rejection unchanged (fail-closed as before).
6. After source_scope exits, subsequent unscoped call again maps None → AP
   (reset restores default, not the previous scope value).
7. Thread isolation: command issued from a fresh thread while main context is
   inside source_scope(AIRCRAFT_AP) → thread sees None default → warning fires
   (documents ContextVar non-inheritance).
8. Unscoped-call counter/accessor reflects the observed method names.

## Red-without-fix evidence

Show at least tests 1 and 7 failing against base 27d0c99 (before your change),
with exact error output.

## Gates (all mandatory in report)

- pytest: full suite, exact counts (expect 391 + new, 0 regressions)
- ruff check . (pre-existing failures listed separately, no NEW findings)
- python -m py_compile on touched files
- git diff --check (pre-existing CRLF only)
- WORKTREE: clean at report time

## Report

TASKS/REVIEWS/P2-CG-01-STAGE1-27D0C99.md — same format as
P2-A-IMPLEMENTATION-9FBF652.md (STATUS / BASE / COMMIT / files /
red-without-fix / gates / derived counts). Commit locally, do not merge;
push + PR after independent review.
