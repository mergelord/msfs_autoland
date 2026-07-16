# TASK-FIX-WAVE1-3971ba1

## Роль

Ты — MiMo, исполнитель. Baseline: `3971ba12113d8994665b1c9a172f2dca6c9e3855` (ветка `master`, repo `zhuk-mou-1/msfs_autoland`).

Выполни все исправления первой волны в одном PR. Ветка: `fix/wave1-probe-confirmed-3971ba1`.

**Не трогать:** архитектурные проблемы LITE-001 (CommandResult), LITE-002 (go-around state machine), LITE-007 (единый gateway) — это вторая волна.

## Контракт исполнения

1. Каждое исправление — минимальный, изолированный diff. Не рефакторь ничего лишнего.
2. После каждого исправления запускай `pytest tests/ -q --tb=short`. При падении — стоп, разберись, не переходи к следующему фиксу.
3. Перед финальным коммитом: `git status --porcelain` — ни одного лишнего изменённого файла.
4. Не добавляй новых зависимостей.
5. Итоговый прогон: `pytest tests/ -q --tb=short` → **276 passed** (или больше при добавленных тестах, 0 failed).
6. В описании PR для каждого fix указать: Finding ID → LV ID → номер строки до → номер строки после.

---

## FIX-01: LV-003 / LITE-003 — `vjoy.connected` → `vjoy.enabled`

**Файл:** `modules/autothrottle.py`

**Проблема:** `VJoyThrottleIntegration.enable()` читает `self.vjoy.connected`, которого нет в `VirtualJoystick` → `AttributeError` → `AutoLandSystem.connect()` падает при установленном pyvjoy.

**Исправление:**
```python
# БЫЛО:
if self.vjoy.connected:

# СТАЛО:
if self.vjoy.enabled:
```

**Также проверить:** `set_throttle` уже проверяет `self.vjoy.connected` в гарде `if not self.enabled or not self.vjoy.connected:` — заменить на `self.vjoy.enabled`.

**Тест:** добавить в `tests/test_autothrottle.py` (создать файл если нет):
```python
def test_vjoy_enable_no_attribute_error():
    from modules.virtual_joystick import VirtualJoystick
    from modules.autothrottle import VJoyThrottleIntegration
    vj = VirtualJoystick.__new__(VirtualJoystick)
    vj.__init__(device_id=1)
    integration = VJoyThrottleIntegration(vj)
    # Must not raise AttributeError; pyvjoy unavailable so enabled=False
    result = integration.enable()
    assert result is False  # disabled because vj.enabled is False (not connected)
```

---

## FIX-02: LV-004 / LITE-004 — двойное преобразование диапазона тяги

**Файл:** `modules/autothrottle.py`

**Проблема:** `VJoyThrottleIntegration.set_throttle` делает `vjoy_value = (throttle_value * 2.0) - 1.0` и передаёт −1..+1 в `VirtualJoystick.set_throttle`, который ожидает 0..1. Тяга < 50% схлопывается к минимуму оси.

**Исправление:**
```python
# БЫЛО:
# vJoy ожидает значение от -1.0 до +1.0
vjoy_value = (throttle_value * 2.0) - 1.0
self.vjoy.set_throttle(vjoy_value)

# СТАЛО:
# VirtualJoystick.set_throttle ожидает 0.0–1.0
self.vjoy.set_throttle(throttle_value)
```

Удалить строку с `vjoy_value` и `logger.debug` если он ссылается на `vjoy_value` — обновить debug-сообщение.

**Тест:**
```python
def test_vjoy_throttle_range_passthrough():
    from modules.virtual_joystick import VirtualJoystick
    from modules.autothrottle import VJoyThrottleIntegration
    received = []
    vj = VirtualJoystick.__new__(VirtualJoystick)
    vj.__init__(device_id=1)
    vj.set_throttle = lambda v: received.append(v)
    vj.enabled = True  # после FIX-01
    integration = VJoyThrottleIntegration(vj)
    integration.enabled = True
    for t in (0.0, 0.25, 0.5, 0.75, 1.0):
        integration.set_throttle(t)
    assert received == [0.0, 0.25, 0.5, 0.75, 1.0], f"Got {received}"
```

---

## FIX-03: LV-005 / LITE-005 — NaN/inf в safety guard (fail-open)

**Файл:** `modules/safety_guard.py`

**Проблема:** `from_telemetry` подставляет `0.0` вместо `None`, но не проверяет `math.isfinite`. Числовые сравнения с NaN всегда `False` → guard пропускает повреждённую телеметрию как безопасную.

**Исправление в `SafetySnapshot.from_telemetry`:** добавить `import math` вверху файла (если нет), затем хелпер и его использование:

```python
import math

def _safe_float(value, default: float) -> float:
    """Return default if value is None, NaN, or infinite."""
    if value is None:
        return default
    try:
        f = float(value)
    except (TypeError, ValueError):
        return default
    return f if math.isfinite(f) else default
```

В `from_telemetry` заменить все `or 0.0` на `_safe_float(..., 0.0)`:

```python
# БЫЛО:
airspeed_indicated=(speed.get('airspeed_indicated')
    if speed.get('airspeed_indicated') is not None
    else 0.0),
vertical_speed=(speed.get('vertical_speed')
    if speed.get('vertical_speed') is not None
    else 0.0),
bank=abs(attitude.get('bank') if attitude.get('bank') is not None else 0.0),

# СТАЛО:
airspeed_indicated=_safe_float(speed.get('airspeed_indicated'), 0.0),
vertical_speed=_safe_float(speed.get('vertical_speed'), 0.0),
bank=abs(_safe_float(attitude.get('bank'), 0.0)),
```

Аналогично для `altitude_agl` и `radio_height`.

**Важно:** NaN в `vertical_speed` со значением по умолчанию 0.0 означает VS=0 → guard не сработает как fail-open. Это **значительно лучше**, чем текущий fail-open. Однако для полного решения добавить G5-подобную проверку has_valid на конечность:

Добавить в `evaluate` сигнатуру флаги `has_valid_vs: bool = True`, `has_valid_airspeed: bool = True` и передавать `math.isfinite(raw_vs)` при вызове из call-site. Если это слишком большой diff — зафиксировать минимальный `_safe_float`-вариант как FIX-03a, а расширение has_valid-флагов как FIX-03b в следующем PR.

**Минимальный тест:**
```python
def test_safety_guard_nan_no_fail_open():
    import math
    from modules.safety_guard import ApproachSafetyGuard, SafetySnapshot
    from modules.safety_guard import GuardDecision
    # After fix: NaN in telemetry -> from_telemetry replaces with 0.0 -> not fail-open
    # Simulate: build snapshot manually with NaN -> should NOT happen after fix,
    # but verify _safe_float replaces NaN
    from modules.safety_guard import _safe_float
    assert _safe_float(math.nan, 0.0) == 0.0
    assert _safe_float(math.inf, 0.0) == 0.0
    assert _safe_float(None, 0.0) == 0.0
    assert _safe_float(120.0, 0.0) == 120.0
```

---

## FIX-04: LV-009 — деление на ноль при GS=0

**Файл:** `modules/navigation.py`, метод `calculate_landing_distance`

**Проблема:** `wind_factor = 1.0 - (headwind / ground_speed * 0.3)` → `ZeroDivisionError` при `ground_speed=0`. Достижимо в runtime после посадки.

**Исправление:**
```python
# БЫЛО:
wind_factor = 1.0 - (headwind / ground_speed * 0.3)
wind_factor = max(0.5, min(1.5, wind_factor))

# СТАЛО:
if ground_speed > 0:
    wind_factor = 1.0 - (headwind / ground_speed * 0.3)
    wind_factor = max(0.5, min(1.5, wind_factor))
else:
    wind_factor = 1.0  # no wind correction when stationary
```

**Тест:**
```python
def test_landing_distance_zero_gs():
    from modules.navigation import Navigation
    nav = Navigation.__new__(Navigation)
    # Must not raise ZeroDivisionError
    result = nav.calculate_landing_distance(ground_speed=0, headwind=10)
    assert isinstance(result, float)
    result2 = nav.calculate_landing_distance(ground_speed=0, headwind=0)
    assert isinstance(result2, float)
```

---

## FIX-05: LV-008 / LITE-008 — unit mismatch в расчёте скоростей захода

**Файл:** `main.py`, метод `_calculate_approach_speeds`

**Проблема (два бага):**

**5a. runway_length передаётся в футах как метры:**
```python
# БЫЛО (main.py:491):
runway_length_m=config.runway_length if hasattr(config, 'runway_length') else 2500,

# СТАЛО:
runway_length_m=(
    config.runway_length / 3.28084   # ApproachConfig.runway_length is in FEET
    if hasattr(config, 'runway_length')
    else 762   # ~2500 ft в метрах
),
```

**5b. aircraft_weight_kg читается из неверной секции телеметрии:**
```python
# БЫЛО (main.py:478, 490):
aircraft = telemetry.get('aircraft', {})
...
aircraft_weight_kg=aircraft.get('total_weight', 60000),

# СТАЛО:
weight_data = telemetry.get('weight', {})
aircraft = telemetry.get('aircraft', {})
...
aircraft_weight_kg=(
    weight_data.get('total_weight', 132277) * 0.453592   # TOTAL_WEIGHT SimConnect = lbs → kg
    if weight_data.get('total_weight') is not None
    else 60000   # fallback: 60 000 kg остаётся для совместимости
),
```

**Примечание:** default fallback 132 277 lbs ≈ 60 000 kg — если SimVar недоступен, поведение не меняется. Добавить комментарий `# SimConnect TOTAL_WEIGHT is in pounds`.

**Тест:** верификационный (не интеграционный — без SimConnect):
```python
def test_runway_length_conversion():
    # 8000 ft -> ~2438 m
    result = 8000 / 3.28084
    assert abs(result - 2438.4) < 1.0

def test_weight_conversion():
    # 132277 lbs -> ~60000 kg
    result = 132277 * 0.453592
    assert abs(result - 59999) < 5
```

---

## FIX-06: LV-002 / LITE-002 (частичный) — `set_gear` вне SAFETY scope

**Файл:** `main.py`, метод `execute_go_around`, строка ~465

**Проблема:** LV-002 зафиксировал, что `set_gear` вызывается вне `with source_scope(CommandSource.SAFETY):`. Все команды go-around должны быть в SAFETY scope.

**Исправление:** переместить `set_gear` внутрь существующего `with source_scope(CommandSource.SAFETY):` блока.

**До (схема):**
```python
with source_scope(CommandSource.SAFETY):
    self.control.set_autopilot_master(True)
    self.control.set_throttle(1.0)
    self.control.set_vertical_speed(1500)
    self.control.set_flaps(2)
self.control.set_gear(False)   # <- вне scope!
```

**После:**
```python
with source_scope(CommandSource.SAFETY):
    self.control.set_autopilot_master(True)
    self.control.set_throttle(1.0)
    self.control.set_vertical_speed(1500)
    self.control.set_flaps(2)
    self.control.set_gear(False)   # <- внутри scope
```

Проверить фактическое расположение строк перед правкой: `grep -n "set_gear" main.py`.

---

## FIX-07: LV-010 — CI не собирает корневые тесты

**Файл:** `.github/workflows/ci.yml`

**Проблема:** `pytest tests/` исключает 6 корневых `test_*.py`. Зафиксировано: `test_aircraft_detection.py`, `test_engine_failure.py`, `test_lvar.py`, `test_mobiflight_wasm.py`, `test_privacy_controls.py`, `test_rudder_compensation.py`.

**Действие — ДВА варианта, выбрать один:**

**Вариант A (включить в CI):** изменить команду на `pytest tests/ . -q --tb=short` (или `pytest` без аргументов если `pyproject.toml` настроен), убедиться что корневые тесты проходят без SimConnect/hardware.

**Вариант B (явно исключить с обоснованием):** добавить в `pyproject.toml`:
```toml
[tool.pytest.ini_options]
# Root test_*.py require hardware (SimConnect/MSFS/WASM) and are excluded from CI
testpaths = ["tests"]
```
и добавить в CI comment почему корневые тесты исключены.

Выбрать вариант по результату `pytest test_*.py --collect-only` — если тесты требуют реального железа, выбрать B; если запускаются в офлайн-режиме — вариант A.

Зафиксировать выбор и причину в PR description.

---

## Порядок выполнения

```
FIX-01 → pytest tests/ → ok
FIX-02 → pytest tests/ → ok
FIX-03 → pytest tests/ → ok
FIX-04 → pytest tests/ → ok
FIX-05 → pytest tests/ → ok
FIX-06 → pytest tests/ → ok  (найди точные строки grep-ом перед правкой)
FIX-07 → pytest (выбранный scope) → ok
финальный pytest tests/ -q → 276+ passed, 0 failed
git status --porcelain → только изменённые production-файлы + тесты
git diff --stat
```

## PR description (шаблон)

```
fix(wave1): 7 probe-confirmed defects from PASS A-LITE / LV-3971ba1

Baseline: 3971ba12113d8994665b1c9a172f2dca6c9e3855

FIX-01 LITE-003/LV-003: autothrottle.py — connected → enabled
FIX-02 LITE-004/LV-004: autothrottle.py — remove double range conversion
FIX-03 LITE-005/LV-005: safety_guard.py — add _safe_float, replace NaN-unsafe patterns
FIX-04 LV-009:          navigation.py — guard GS=0 division
FIX-05 LITE-008/LV-008: main.py — runway ft→m conversion, weight correct section
FIX-06 LITE-002/LV-002: main.py — set_gear inside SAFETY scope
FIX-07 LV-010:          ci.yml / pyproject.toml — document root test exclusion

Tests: 276+ passed, 0 failed
Production code changed: modules/autothrottle.py, modules/safety_guard.py,
                         modules/navigation.py, main.py, .github/workflows/ci.yml
```

## Стоп-условия

- `BLOCKED:<FIX-id>` — конкретный фикс неисполним (указать причину), остальные продолжить.
- `REGRESSION` — после фикса падают ранее проходящие тесты: откатить конкретный фикс, зафиксировать, перейти к следующему.
- Не открывать PR с `0 failed` → `N failed`.
