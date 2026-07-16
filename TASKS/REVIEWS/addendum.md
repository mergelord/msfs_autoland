# ADDENDUM: FIX-WIND-CORRECTION-FINITE-OUTPUTS

**Ветка:** `fix/wind-correction`
**Текущий HEAD:** `0d762823299e98f2b2b3ab051a5e4e011234a59e`
**Не amend:** сделать отдельный коммит и push.
**Master не мержить.**

## A1 — действительно finite fail-closed result

В invalid-wind ветке `apply_wind_corrections`:

- warning должен сохранить и вывести фактические входные значения;
- в возвращаемом словаре нормализовать:
  - `wind_speed: 0.0`
  - `wind_direction: 0.0`
- все остальные коррекции оставить нулевыми;
- `corrected_heading = desired_track`;
- `corrected_vs = base_vs`.

Цель: ни одно поле результата не должно содержать NaN/inf.

## A2 — исправить тест без исключений

В `test_all_outputs_finite` удалить:

​
raw_keys = {'wind_speed', 'wind_direction'}
if k in raw_keys:
continue

Проверять `math.isfinite(v)` для КАЖДОГО числового поля результата.

Добавить явные assertions:

​
assert result['wind_speed'] == 0.0
assert result['wind_direction'] == 0.0

для invalid-wind cases.

## A3 — nonfinite glideslope validation

В `calculate_descent_rate` добавить fail-closed guard:

​
if (
not math.isfinite(glideslope_angle)
or glideslope_angle <= 0
or glideslope_angle > 10
):
logger.warning(...)
return 0.0

Добавить parametrized tests для:

- `float('nan')`
- `float('inf')`
- `float('-inf')`

Ожидание для каждого: `0.0`, warning присутствует, исключения нет.

## Gates

1. Только два уже разрешённых файла.
2. `py_compile` для production и test-файла.
3. `git diff --check`.
4. `pytest tests/` — ожидается не менее 276 passed / 0 failed.
5. Отдельный commit:
   `fix: ensure finite wind correction outputs`
6. Push в ту же ветку.
7. Отчёт:
   - новый SHA;
   - parent должен быть `0d762823299e98f2b2b3ab051a5e4e011234a59e`;
   - список файлов;
   - полный счёт pytest;
   - `COMPLETED_AND_PUSHED`.

При расхождении — `STOPPED_ON_GATE`, без импровизации.