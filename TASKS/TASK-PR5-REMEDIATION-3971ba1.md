# TASK-PR5-REMEDIATION-3971ba1

## Контекст и роль

Ты — MiMo, исполнитель remediation для уже открытого PR #5:

- repo: `https://github.com/zhuk-mou-1/msfs_autoland`
- branch: `fix/wave1-probe-confirmed-3971ba1`
- PR: `#5`
- исходный baseline PR: `3971ba12113d8994665b1c9a172f2dca6c9e3855`
- текущий проверенный head на момент выдачи задачи: `5d48fdfcfea148f178dee8ce75fd0153da4cbc2e`

PR #5 **НЕ принят к merge**. Он требует remediation двух code/test defects и документированного разбора CI lint failure.

Работай в существующей ветке PR #5. Не создавай новый PR. Сделай один или несколько новых коммитов поверх текущего head и push в ту же ветку.

## Жёсткие правила

1. Сначала выполни `git fetch origin`, checkout ветки PR и зафиксируй фактический `HEAD`. Если head уже другой — продолжай от последнего head этой ветки, но укажи SHA в отчёте.
2. Не откатывай корректные FIX-01, FIX-02, FIX-04, FIX-05 и CI-policy из PR #5.
3. Не меняй production-код вне нужных файлов без явного обоснования:
   - `modules/safety_guard.py`
   - `main.py`
   - тесты в `tests/`
   - возможно `.github/workflows/ci.yml` / конфиг lint — только если lint regression докажется как PR-specific.
4. Не использовать MagicMock для проверки safety runtime-path. Допустимы простые fake/spy-объекты на IO-границах.
5. Нельзя считать PR исправленным, пока не пройдут новые end-to-end regression tests ниже и CI не будет классифицирована честно.
6. Не менять тест, чтобы он просто соответствовал текущей ошибочной реализации.

---

# REM-01 — BLOCKER: FIX-03 всё ещё fail-open для NaN/inf

## Наблюдаемая проблема

Текущий PR добавил `_safe_float(value, 0.0)`, но превратил невалидную критическую телеметрию в правдоподобные значения `0.0`.

В `main.py` call-site guard до сих пор передаёт флаги вида:

```python
has_vs=speed_data.get('vertical_speed') is not None
has_bank=attitude_data.get('bank') is not None
has_airspeed=speed_data.get('airspeed_indicated') is not None
```

Для `math.nan` и `math.inf` эти выражения дают `True`. После sanitization G5 считает канал присутствующим, а threshold checks на `0.0` могут дать `CONTINUE`. Это не fail-closed и не закрывает LITE-005 / LV-005.

## Требуемое поведение

В FINAL phase любой `NaN`, `+inf`, `-inf`, неконвертируемое значение или `None` хотя бы в одном critical input должен трактоваться как invalid telemetry.

Critical inputs:

- `position.altitude_agl`
- `position.radio_height` (допустимо fallback на finite `altitude_agl`; если оба height channels invalid — invalid)
- `speed.airspeed_indicated`
- `speed.vertical_speed`
- `attitude.bank`

При `debounce_n=1` результат должен быть:

```text
GuardDecision.GO_AROUND
reason == "INVALID_TELEMETRY"
```

При стандартном debounce результат может быть сначала `CONTINUE` с `INVALID_TELEMETRY_debounce`, а на N-м подряд кадре — `GO_AROUND`. Это допустимо, если тест явно фиксирует debounce semantics.

## Требуемая реализация

Сделай явный separation между:

1. **числом, безопасным для хранения/логирования**, и
2. **валидностью исходного telemetry channel**.

Минимально приемлемый путь:

1. В `modules/safety_guard.py` добавить один публичный или module-private helper, например:

```python
def _is_finite_number(value) -> bool:
    try:
        return value is not None and math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
```

2. `_safe_float` можно оставить для числовых полей snapshot, но он **не должен быть единственным** признаком валидности.
3. В `main.py`, перед `self.safety_guard.evaluate(...)`, вычислять `has_*` через finite-проверку исходных raw values, а не через `is not None`.
4. Height contract:
   - `has_altitude` = finite `altitude_agl`;
   - `has_radio_height` = finite `radio_height`;
   - существующая G5-семантика `has_height = has_radio_height or has_altitude` сохраняется;
   - finite altitude остаётся допустимым fallback, если radio height NaN/inf/None;
   - если оба height channel невалидны, G5 обязан сработать.
5. В `SafetySnapshot.from_telemetry` не выбирать NaN radio height вместо валидной altitude как итоговую `radio_height`. Используй finite radio height, иначе finite altitude, иначе numeric default.

Не добавляй silent fallback, который позволяет `NaN` пройти как «0 ft», «0 kts» или «0 fpm» при `has_* == True`.

## Обязательные regression tests

Добавить тесты на **реальный integration path**:

```text
raw telemetry dict
→ SafetySnapshot.from_telemetry(...)
→ guard.evaluate(snapshot, flags derived from raw values)
→ decision/reason assertion
```

Не тестируй только `_safe_float`.

Минимальный matrix при `ApproachSafetyGuard(debounce_n=1)`:

| Case | Expected |
|---|---|
| `vertical_speed = NaN` | `GO_AROUND / INVALID_TELEMETRY` |
| `vertical_speed = +inf` | `GO_AROUND / INVALID_TELEMETRY` |
| `bank = NaN` | `GO_AROUND / INVALID_TELEMETRY` |
| `airspeed_indicated = NaN` | `GO_AROUND / INVALID_TELEMETRY` |
| `radio_height = NaN`, `altitude_agl = 500.0` | NOT invalid solely due to radio; valid altitude fallback works |
| `radio_height = NaN`, `altitude_agl = NaN` | `GO_AROUND / INVALID_TELEMETRY` |
| all finite nominal frame | `CONTINUE / all_checks_passed` |

Дополнительно добавить по меньшей мере один test **реального call-site contract** `_handle_phase` либо выделенного helper, который он использует: доказать, что finite flags, передаваемые из `main.py`, становятся `False` для NaN/inf. Не требуется запускать actuators: phase handler можно изолировать fake-safe объектами только на terminal boundaries.

---

# REM-02 — BLOCKER: FIX-05 tests проверяют константную математику, не production path

## Наблюдаемая проблема

Существующие `test_runway_length_conversion` и `test_weight_conversion` вычисляют:

```python
8000 / 3.28084
132277 * 0.453592
```

Они не вызывают `AutoLandSystem._calculate_approach_speeds()` и не доказывают ни telemetry section, ни kwargs, переданные calculator.

## Требуемый test

Добавь production-path regression test, который:

1. использует реальный метод `AutoLandSystem._calculate_approach_speeds`; 
2. предоставляет fake telemetry с:

```python
{
  "weather": {"wind_direction": 0, "wind_velocity": 0, "wind_gust": 0, "ambient_temperature": 15},
  "aircraft": {"title": "Test Aircraft"},
  "weight": {"total_weight": 132277},
}
```

3. использует spy/fake `speed_calculator.calculate_approach_parameters(**kwargs)`;
4. вызывает метод с реальным `ApproachConfig` или минимальным эквивалентным объектом с:

```python
runway_length = 8000
runway_elevation = 0
final_approach_course = 0
```

5. утверждает на **перехваченных kwargs**:

```python
kwargs["aircraft_weight_kg"] == pytest.approx(132277 * 0.453592)
kwargs["runway_length_m"] == pytest.approx(8000 / 3.28084)
```

6. отдельным test подтверждает documented fallback при отсутствии `weight["total_weight"]`:

```python
kwargs["aircraft_weight_kg"] == pytest.approx(60000)
```

Fake calculator должен вернуть минимальный словарь, нужный методу для последующего логирования и `config.approach_speed` (например `aircraft_name`, `flaps_configuration`, `vref`, `vapp`, `wind_correction`, `gust_correction`, `altitude_correction`, `temperature_correction`, `weight_ok`, `aircraft_weight_kg`, `max_landing_weight_kg`).

Удалить или оставить старые math-only tests — на усмотрение, но они **не считаются** regression coverage без новых production-path tests.

---

# REM-03 — CI: классифицировать `lint-ruff` failure

Head PR #5 имеет успешные test jobs для Python 3.12/3.13, но `lint-ruff` имеет conclusion `failure`.

## Задача

1. Получить точные lint diagnostics (файл, строка, rule, текст) из GitHub Actions или локальным `ruff check .` на том же head.
2. Сравнить с baseline `3971ba1`:

```bash
git checkout 3971ba12113d8994665b1c9a172f2dca6c9e3855
ruff check .
git checkout fix/wave1-probe-confirmed-3971ba1
ruff check .
```

3. В отчёте приложить оба полных вывода и classification:
   - `PRE_EXISTING_ONLY` — те же rule/file/line (с допуском на line shift) уже падают на baseline; PR не вносит нового lint failure;
   - `PR_REGRESSION` — в head есть хотя бы одно новое lint violation.
4. Если `PR_REGRESSION`, исправить только violations, внесённые PR #5, и запустить ruff снова.
5. Если `PRE_EXISTING_ONLY`, **не маскировать** lint через `|| true`, ignore rule или изменение CI. Сохрани честную классификацию в PR comment/отчёте.

PR можно принять при `PRE_EXISTING_ONLY`, но final report обязан содержать доказательство сравнения. При `PR_REGRESSION` PR не сдаётся, пока эта регрессия не исправлена.

---

# Не считать отдельным FIX: SAFETY scope у `set_gear`

Проверка diff показала: текущий PR изменил только комментарий рядом с `set_gear`, а не его indentation/scope. В фактическом head `set_gear(False)` уже находится внутри existing `with self.control.source_scope(CommandSource.SAFETY)`.

Не заявляй FIX-06 как новый code fix Wave 1. В финальном отчёте перепиши его честно так:

```text
FIX-06 verification only: set_gear was already inside SAFETY scope at PR baseline; PR #5 did not change executable scope.
```

Не нужно искусственно менять код ради этого пункта.

---

# Обязательная верификация перед push

Выполнить и включить полный, несокращённый вывод в отчёт:

```bash
python --version
pytest tests/ -q --tb=short
ruff check .
git diff origin/master...HEAD --check
git status --porcelain
git log --oneline origin/master..HEAD
```

Также указать:

- final head SHA;
- фактический count passed/failed;
- результаты REM-01 matrix;
- перехваченные kwargs REM-02;
- baseline/head ruff classification REM-03;
- список изменённых файлов.

## Delivery

1. Push remediation commits в `fix/wave1-probe-confirmed-3971ba1` (PR #5 обновляется).
2. Верни отчёт `PR5-REMEDIATION-REPORT.md`.
3. В chat summary: final SHA, test count, lint classification, список закрытых REM-01/02/03.

## Stop conditions

- Если после изменения тестов появляется regression — не скрывать и не ослаблять assertion; зафиксировать `REGRESSION` в отчёте.
- Если невозможно создать integration-style test из-за import dependency, подготовить минимальный deterministic fake boundary. Не заменять test math-only assertion-ами.
- Не merge PR #5 самостоятельно.
