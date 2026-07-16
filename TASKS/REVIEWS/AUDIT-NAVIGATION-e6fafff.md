# AUDIT-NAVIGATION-e6fafff — Safety-аудит modules/navigation.py (v2)

**Commit:** `e6fafffba4d6047e87664730cbc888738cceae62`
**Дата:** 2026-07-13
**Scope:** `modules/navigation.py` (710 строк), кросс-референсы с `synthetic_glidepath.py`, `approach_phases.py`, `autopilot_takeover.py`, `ils_navigation.py`, `main.py`, `types.py`
**Режим:** read-only, исследование с внешними источниками

---

## 1. Геодезическая математика

### 1.1 calculate_distance (Haversine) — ЧИСТО

**Строки 18-30:** Стандартная Haversine. `R = 3440.065` nm. Корректно.

### 1.2 calculate_bearing — ЧИСТО

**Строки 33-43:** `atan2(x, y)` → `(bearing + 360) % 360`. Корректно.

### 1.3 normalize_angle / angle_difference — ЧИСТО

**Строки 46-58:** Корректная нормализация в ±180.

---

## 2. Глиссадная математика

### 2.1 calculate_required_altitude — ЧИСТО

**Строки 98-114:** `nm → feet → tan(angle) → +elevation`. Корректно.

### 2.2 calculate_descent_rate — ЧИСТО

**Строки 83-96:** `VS = GS × tan(θ) × 101.3`. Корректно.

### 2.3 calculate_glideslope_distance — ЧИСТО

**Строки 277-307:** Обратная операция. Guard на `angle <= 0`.

### 2.4 calculate_glideslope_intercept_point — ЧИСТО

**Строки 309-368:** Координаты точки входа. Корректно.

---

## 3. НАХОДКИ

### NAV-01 [P1] should_start_descent: ideal_altitude считается от точки входа вместо порога

**Строки 403-408:**
```python
if distance_to_intercept <= intercept_point['distance_from_threshold_nm']:
    ideal_altitude = distance_to_intercept * intercept_point['feet_per_nm']
else:
    ideal_altitude = intercept_point['altitude_agl']
```

**Проблема:** `distance_to_intercept` — расстояние от самолёта до **точки входа**. Формула `distance_to_intercept * feet_per_nm` вычисляет理想ную высоту **от точки входа**, а не от порога. Правильно: `(intercept_distance - distance_to_intercept) * feet_per_nm`.

**Влияние (ИСПРАВЛЕНО v1):** Ранее я недооценил влияние. `SyntheticGlidepath.compute_target_vs()` (synthetic_glidepath.py:130-135) использует `status` из `should_start_descent` как прямой gate:

```python
# synthetic_glidepath.py:130-135
if descent_info["status"] == "LOW":
    return 0.0
if not descent_info["should_descend"] and descent_info["status"] != "HIGH":
    return 0.0
```

**Воспроизводимый пример (3°, intercept ~6.29NM / 2000ft):**
1. Самолёт в 1NM от порога (5.29NM от intercept point)
2. Правильная理想ная высота: `(6.29 - 1) × 100 = 529ft`
3. Текущий код: `1 × 100 = 100ft` (от intercept point, неверно)
4. `altitude_error = current - 100 = ~318 - 100 = +218` → статус OK/DEVIATION
5. Но с правильной формулой: `altitude_error = 318 - 529 = -211` → тоже OK/DEVIATION

Однако при других позициях (ближе к intercept point) неверный ideal_altitude может дать **статус LOW** → `compute_target_vs()` вернёт 0.0 → **снижение заблокировано возле порога**.

**Фикс:** `(intercept_point['distance_from_threshold_nm'] - distance_to_intercept) * intercept_point['feet_per_nm']`

---

### NAV-02 [P2] calculate_landing_distance: ZeroDivisionError при ground_speed=0

**Строка 212:**
```python
wind_factor = 1.0 - (headwind / ground_speed * 0.3)
```

При `ground_speed = 0` → `ZeroDivisionError`. Вызывается из `FinalPhaseState._log_approach_parameters()` (approach_phases.py:410). Не直接影响ует управление, но крашит логирование.

---

### NAV-03 [P2] calculate_vor_approach: sign convention cross_track_error

**Строки 151 vs 68:**
```python
# navigation.py:151
cross_track_error = self.angle_difference(current_radial, config.final_approach_course)

# navigation.py:68 (контракт calculate_intercept_heading):
# cross_track_error: Боковое отклонение (градусы, + = справа)
```

`angle_difference(current_radial, final_course)` = `final_course - current_radial`. При `current_radial = 275` (самолёт справа от курса 270): `cross_track_error = 270 - 275 = -5`. Отрицательное = **левее** курса. Но контракт говорит `+ = справа`.

В `calculate_intercept_heading` (строка 76): `if cross_track_error > 0: return target_radial - intercept_angle` — «отклонились вправо, нужно лететь левее». При actual sign = отрицательный для правого отклонения → условие `> 0` не срабатывает → самолёт летит **ещё правее** вместо коррекции.

**Severity:** P2. Неверный intercept heading при VOR-заходе с правым отклонением.

---

### NAV-04 [P1] check_beacon_passage: course_error через normalize_angle вместо angle_difference

**Строка 638:**
```python
course_error = self.normalize_angle(current_heading - expected_course)
```

`normalize_angle(x) = x % 360` → результат всегда 0-360. При `current_heading = 265, expected_course = 270`: `normalize_angle(-5) = 355`. `abs(355) = 355` > tolerance 5.0 → **ложное нарушение курса** (фактически отклонение всего 5°).

Должно быть `angle_difference(current_heading, expected_course)` → `-5` → `abs(-5) = 5` → OK.

**Влияние:** Все пролёты приводов с курсом, отклонённым влево от expected_course, получают ложное `course_ok = False` → `status = "WARNING"` или `CRITICAL` → рекомендация "GO AROUND" на ближнем приводе (строка 688).

**Severity:** P1. Ложные go-around рекомендации при штатном полёте.

---

### NAV-05 [P2] should_start_descent: gap при altitude_error 200-300

**Строки 422-451:**
```python
if distance_to_intercept <= tolerance_nm:    status = "INTERCEPT"
elif altitude_error > 300:                   status = "HIGH"
elif altitude_error < -300:                  status = "LOW"
elif abs(altitude_error) <= 200:             status = "ON_PROFILE"
else:                                        status = "DEVIATION"
```

При `altitude_error = 250` (модуль): ни `> 300`, ни `< -300`, ни `<= 200` → `else` → `status = "DEVIATION"`. Это корректно.

При `altitude_error = 300` (ровно): ни `> 300` (строго), ни `< -300`, ни `<= 200` → `else` → `status = "DEVIATION"`. Корректно.

**Однако:** `> 300` и `< -300` — **строгие** неравенства. При `altitude_error = 300.001` → HIGH, при `altitude_error = 300.0` → DEVIATION. Граница 300 не включена в ни одну категорию. Это не дефект (300.0 и 300.001 — одинаковые по существу), но может сбивать при анализе логов.

**Severity:** P3 (косметика, не влияет на поведение).

---

### NAV-06 [P3] calculate_runway_beacons: мёртвый код строки 540-543

**Строки 540-543:** Сложная формула для `outer_altitude_agl`, которая **сразу перезаписывается** простой формулой на строке 546. Мёртвый код. На поведение не влияет.

---

### NAV-07 [P3] main._calculate_headwind дублирует Navigation.calculate_wind_components

**main.py:516-537:** Дублирование логики из `wind_correction.py:16-40`. Risk: расхождение при рефакторинге.

---

### NAV-08 [P2] Нет прямых unit-тестов для navigation.py

В `tests/` нет `test_navigation.py`. Все тесты идут через mock. Реальные `calculate_distance`, `calculate_bearing`, `calculate_landing_distance` **не тестируются** напрямую.

---

## Сводка

| # | Severity | Находка | Строка |
|---|----------|---------|--------|
| NAV-01 | **P1** | should_start_descent: ideal_altitude от intercept вместо порога → блокировка снижения | 403-408 |
| NAV-04 | **P1** | check_beacon_passage: course_error через normalize_angle → ложные go-around | 638 |
| NAV-02 | P2 | calculate_landing_distance: ZeroDivisionError при GS=0 | 212 |
| NAV-03 | P2 | calculate_vor_approach: sign convention cross_track_error | 151 vs 68 |
| NAV-05 | P2 | should_start_descent: gap 200-300 (косметика) | 432-442 |
| NAV-08 | P2 | Нет прямых unit-тестов navigation.py | tests/ |
| NAV-06 | P3 | calculate_runway_beacons: мёртвый код | 540-543 |
| NAV-07 | P3 | _calculate_headwind дублирует Navigation | main.py:516 |

## Рекомендации

1. **NAV-01 (P1):** `(intercept_distance - distance_to_intercept) * feet_per_nm`
2. **NAV-04 (P1):** Заменить `normalize_angle` на `angle_difference` в строке 638
3. **NAV-02 (P2):** `if ground_speed <= 0: return 0.0`
4. **NAV-03 (P2):** Инвертировать sign в строке 151 или исправить контракт в строке 68
5. **NAV-08 (P2):** Добавить `test_navigation.py` с реальными координатами
