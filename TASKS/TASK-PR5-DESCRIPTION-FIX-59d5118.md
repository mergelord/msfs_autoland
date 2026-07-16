# TASK-PR5-DESCRIPTION-FIX-59d5118

## Статус
PR #5 (`fix/wave1-probe-confirmed-3971ba1` → `master`), head `59d5118779ec18017b138a09b172f5c321ec1dbe`.

Независимая проверка кода, тестов и CI на этом SHA завершена и **принята**:
- REM-01 (BLOCKER): `_is_finite_number()` / `_safe_float()` в `modules/safety_guard.py`, call-site в `main.py` использует `_is_finite_number(...)` для всех `has_*` флагов вместо `is not None`, интеграционные тесты в `tests/test_safety_guard.py` реально проходят через `AutoLandSystem._handle_phase` — подтверждено.
- REM-02 (BLOCKER): `test_calculate_approach_speeds_kwargs` и `test_calculate_approach_speeds_fallback_weight` в `tests/test_autothrottle.py` реально вызывают `AutoLandSystem._calculate_approach_speeds(config)` и перехватывают kwargs у `speed_calculator` — подтверждено, это не math-only тесты.
- REM-03: check-run `lint-ruff` на `59d5118` → `success` (было `failure`). Все 6 check-runs зелёные.

**Код и тесты не отклоняются. Остался только один пункт — документация PR, не диф.**

## Единственная задача: обновить описание (body) PR #5

Текущее описание PR #5 всё ещё показывает текст раунда 1 (создан `2026-07-14T17:59:53Z`, не обновлялся с `updated_at 2026-07-14T18:24:30Z` — то есть после пуша remediation-коммита текст не менялся):

```
## Summary
fix(wave1): 7 probe-confirmed defects from PASS A-LITE / LV-3971ba1
...
FIX-06 LITE-002/LV-002: main.py:448-453 - set_gear inside SAFETY scope
...
## Tests
282 passed, 0 failed (+6 new tests)
```

Это не отражает: (a) round-2 remediation коммит (REM-01/02/03), (b) честную переклассификацию FIX-06.

### DOC-01: Добавить секцию Remediation в описание PR
Добавить после существующей секции `## Fixes` новую секцию, например:

```
## Remediation (round 2, commit 59d5118)

REM-01 (BLOCKER, was CHANGES REQUIRED): FIX-03/safety_guard NaN/inf handling was fail-open
(has_* flags used `is not None`, which is true for NaN/inf floats). Fixed:
- Added `_is_finite_number()` to modules/safety_guard.py
- main.py has_* flags now use `_is_finite_number(...)` instead of `is not None`
- from_telemetry prefers finite radio_height, falls back to finite altitude_agl
- Added integration tests exercising real AutoLandSystem._handle_phase (not just evaluate())

REM-02 (BLOCKER, was CHANGES REQUIRED): FIX-05 unit-conversion tests were math-only,
not testing the real production code path. Fixed:
- test_calculate_approach_speeds_kwargs and test_calculate_approach_speeds_fallback_weight
  now call the real AutoLandSystem._calculate_approach_speeds(config) and spy on the
  kwargs passed to speed_calculator.calculate_approach_parameters

REM-03: lint-ruff was failing on round-1 diff (undisclosed). Fixed:
- Removed unused imports in tests/test_navigation.py and tests/test_safety_guard.py
- ruff check main.py modules/ tests/ -> All checks passed
```

### DOC-02: Переклассифицировать FIX-06 в описании
Заменить строку:
```
FIX-06 LITE-002/LV-002: main.py:448-453 - set_gear inside SAFETY scope
```
на честную формулировку, например:
```
FIX-06 LITE-002/LV-002: VERIFICATION ONLY - set_gear(False) in execute_go_around was
already inside the SAFETY scope before this PR (baseline 3971ba1). This PR's diff at
that location is comment-only; no behavior change. Confirmed via diff review, not a new fix.
```

### DOC-03: Обновить тестовый счётчик
Заменить:
```
## Tests
282 passed, 0 failed (+6 new tests)
```
на фактические числа для коммита `59d5118` (заявлено 293 passed, +11 new — подтвердить фактическим выводом `pytest` перед публикацией, не копировать без проверки).

## Условие приёмки
- Описание PR #5 отражает оба коммита (round 1 + round 2 remediation), включая честную классификацию FIX-06.
- Никаких изменений кода/тестов не требуется — это правка только текста PR description.
- После обновления описания PR готов к merge.
