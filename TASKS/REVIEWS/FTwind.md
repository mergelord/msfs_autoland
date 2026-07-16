ЗАПРЕЩЕНО: менять формулу/докстринг-контракт `calculate_wind_components`
(`crosswind > 0` = ветер справа — контракт корректен, его потребители не должны пострадать).
ОБЯЗАТЕЛЬНО: клампованный вариант с `max(-1.0, min(1.0, ...))` — незаклампованный
`min(1.0, ...)` даёт ValueError от asin при crosswind/TAS < -1.

### F-W2 [P1] Валидация входов (WCB-04 + WCB-03)
В начале `apply_wind_corrections`: если `wind_speed` или `wind_direction` не проходят
`math.isfinite()`, либо `wind_speed < 0` → `logger.warning(...)` с фактическими значениями
и fail-closed результат: все коррекции нулевые, `corrected_heading = desired_track`,
`corrected_vs = base_vs` (по валидному ground_speed). Исключение НЕ выбрасывать,
NaN НЕ пропускать дальше (сейчас NaN доходит до `int()` в approach_phases → ValueError → error budget).

### F-W3 [P2] Double-counting headwind (WCB-07)
`apply_wind_corrections`: убрать `vs_correction` из итога — `corrected_vs = base_vs`
(геометрическая `VS = GS × tan(γ)` уже полностью определена фактической ground speed;
`headwind*10` — недокументированная эвристика, повторно учитывающая ветер).
Ключи словаря результата сохранить для совместимости: `vs_correction: 0.0`, `base_vs` как есть.
`calculate_pitch_correction` пометить deprecated в докстринге (не удалять — отдельное решение).

### F-W4 [P2] Валидация glideslope angle (WCB-05)
`calculate_descent_rate`: если angle вне диапазона (0, 10] градусов → `logger.warning` + `return 0.0`
(fail-closed). Убирает 1.65e20 при 90° и инверсию знака при 91°.

### F-W5 [P3] Консистентность знака drift + dead code
- `calculate_drift_angle`: привести к той же конвенции — снос по ветру:
  `drift = degrees(asin(max(-1.0, min(1.0, -crosswind / true_airspeed))))`
  (ветер справа, cw>0 → снос ВЛЕВО → drift < 0). Обновить докстринг (положительный = вправо).
- Удалить мёртвый `calculate_crab_angle` (0 вызовов в проде и тестах — подтверждено твоим же аудитом).

## Обязательные тесты (новый файл `tests/test_wind_correction.py`)
1. `test_ground_track_maintained_with_crosswind` — твой regression-тест из отчёта v2:
   4 кейса (track 0/wind FROM 90, 0/270, 90/0, 90/180), TAS=120, W=20; ground track
   по FROM-векторной математике; ошибка < 1.0°.
2. `test_corrected_heading_both_signs` — track=0: wind FROM 90 → heading ≈ 9.59° (±0.1);
   wind FROM 270 → ≈ 350.41° (±0.1).
3. `test_invalid_wind_fail_closed` — NaN/inf/отрицательный wind_speed и NaN/inf wind_direction:
   `apply_wind_corrections` не бросает исключений, все выходы finite,
   `corrected_heading == desired_track`, warning в логе.
4. `test_descent_rate_validation` — GS=100: angle=3.0 → ≈530.9 (±1); angle=90 → 0.0; angle=0 → 0.0; angle=-3 → 0.0.
5. `test_no_headwind_double_counting` — одинаковый GS, headwind 0 vs 20 → `corrected_vs` идентичен.
6. `test_drift_angle_sign` — cw=+20, TAS=120 → drift ≈ -9.59; cw=-20 → ≈ +9.59.
7. `test_saturated_crosswind_no_exception` — |crosswind| > TAS (например W=200, TAS=120) → без исключений, |crab| = 90°.

## Приёмка
- Все существующие тесты зелёные: 251 passed / 0 failed (изменять/ослаблять существующие asserts ЗАПРЕЩЕНО; если какой-то старый тест зашивает багованное поведение — СТОП, статус STOPPED_ON_GATE, не править молча).
- Все новые тесты зелёные. Ожидаемый итог: ≥258 passed / 0 failed.
- `py_compile` на изменённых файлах до запуска тестов.
- Гейт перед началом: подтверди, что рабочее дерево чистое и HEAD = e6fafff. Иначе — СТОП.

## Отчёт
`TASKS\FIXES\FIX-WIND-CORRECTION-e6fafff.md` + JSON-отчёт по шаблону fail-closed:
per-fix статус (WRITTEN/SKIPPED/FAILED), вывод pytest (полностью: passed/failed счётчики),
sha ветки после push, итоговый статус: `COMPLETED_AND_PUSHED | COMPLETED_NOT_PUSHED | STOPPED_ON_GATE | APPLY_FAILED`.
При любой неоднозначности (old-код не совпадает с ожиданием, тест падает не по твоей вине) — СТОП и вопрос, а не импровизация.