# TASK-LOCAL-VERIFICATION-LV-3971ba1

## Роль

Ты — локальный исполнитель верификационных probe-ов (MiMo). У тебя есть shell, Git, Python 3.12+, pytest. MSFS НЕ требуется. Твоя задача — исполнить пакет LV-001…LV-011 из внешнего аудита PASS A-LITE и вынести по каждому пункту вердикт CONFIRMED / DISPROVED / BLOCKED с сырыми доказательствами.

Ты НЕ исправляешь найденные дефекты. Только верификация. Production-код не изменяется.

## 0. Baseline (обязательно)

```bash
git clone https://github.com/zhuk-mou-1/msfs_autoland.git
cd msfs_autoland
git checkout 3971ba12113d8994665b1c9a172f2dca6c9e3855
git rev-parse HEAD   # обязан вывести ровно этот SHA
```

Если SHA не совпадает — остановка со статусом `BLOCKED_BASELINE_UNAVAILABLE`.

Среда:

```bash
python -m venv .venv-lv && source .venv-lv/bin/activate  # или Windows-эквивалент
pip install pytest
pip install pyvjoy gtts pygame || true   # как в CI; допускается недоступность
python --version   # зафиксировать в отчёте
```

## 1. Правила исполнения

1. Все probe-файлы создавать ТОЛЬКО в новой директории `probes_lv/`. Ни один файл в `main.py`, `gui.py`, `modules/`, `tests/`, `.github/` не изменяется. Перед сдачей отчёта выполнить `git status --porcelain` и приложить вывод: кроме `probes_lv/` и отчётных файлов ничего не должно появиться.
2. Каждый probe — отдельный запускаемый файл `probes_lv/lv_XXX_probe.py` (или pytest-файл). В отчёт включается полный stdout/stderr каждого запуска, без сокращений и пересказов.
3. Вердикты:
   - `CONFIRMED` — наблюдаемое поведение совпало с ожиданием finding-а;
   - `DISPROVED` — наблюдаемое поведение опровергает finding (приложить доказательство);
   - `BLOCKED` — probe не удалось исполнить (указать точную причину).
4. Запрещено подгонять probe под ожидаемый результат. Если результат отличается от ожидания — фиксируй фактический и ставь DISPROVED/BLOCKED честно.
5. MagicMock для тестируемых production-классов запрещён: использовать реальные классы, monkeypatch только на границах (SimConnect/pyvjoy/spy).

## 2. Приоритет исполнения

Первая очередь (критичные, дешёвые): **LV-003, LV-004, LV-005, LV-008, LV-009**.
Вторая очередь: LV-001, LV-002, LV-010, LV-011.
Третья очередь: LV-006, LV-007.

---

## 3. Спецификации probe-ов

### LV-003 — vJoy contract: несуществующий атрибут `connected`

**Гипотеза (LITE-003):** `VJoyThrottleIntegration.enable()` читает `self.vjoy.connected`, а `VirtualJoystick` определяет только `enabled` → `AttributeError`.

Probe:

```python
from modules.virtual_joystick import VirtualJoystick
from modules.autothrottle import VJoyThrottleIntegration

vj = VirtualJoystick(device_id=1)   # реальный класс; pyvjoy может быть недоступен — это ок
integration = VJoyThrottleIntegration(vj)
try:
    result = integration.enable()
    print("NO EXCEPTION, result =", result)
except AttributeError as e:
    print("ATTRIBUTE_ERROR:", e)
```

Ожидание при CONFIRMED: `AttributeError: 'VirtualJoystick' object has no attribute 'connected'`.

Дополнительно: `grep -n "connected" modules/virtual_joystick.py` — приложить вывод (проверка, что атрибут/property действительно отсутствует во всём файле).

Также проверить и зафиксировать: где в production вызывается `VJoyThrottleIntegration.enable()` (`grep -rn "\.enable()" main.py gui.py modules/`) и обёрнут ли вызов в try/except — от этого зависит, срывает ли дефект `AutoLandSystem.connect`.

### LV-004 — двойное преобразование диапазона тяги

**Гипотеза (LITE-004):** `VJoyThrottleIntegration.set_throttle` преобразует 0..1 → −1..+1, а `VirtualJoystick.set_throttle` ожидает 0..1 → команды тяги ниже 0.5 схлопываются к минимуму оси.

Probe (spy без MagicMock):

```python
from modules.virtual_joystick import VirtualJoystick
from modules.autothrottle import VJoyThrottleIntegration

vj = VirtualJoystick(device_id=1)
vj.connected = True          # обход LV-003 для изоляции этого дефекта
received = []
vj.set_throttle = lambda v: received.append(v)   # spy на границе

integration = VJoyThrottleIntegration(vj)
integration.enabled = True
for t in (0.0, 0.25, 0.5, 0.75, 1.0):
    integration.set_throttle(t)
print("received:", received)
```

Ожидание при CONFIRMED: `received == [-1.0, -0.5, 0.0, 0.5, 1.0]` вместо `[0.0, 0.25, 0.5, 0.75, 1.0]`.

Вторая часть: подать эти же значения в реальный `VirtualJoystick.set_throttle` (с заглушкой `joystick.set_axis` как spy, `enabled=True`) и зафиксировать фактические axis-значения после clamp — показать, что −1.0 и −0.5 схлопываются к `axis_min`.

### LV-005 — NaN/inf проходят safety guard (fail-open)

**Гипотеза (LITE-005):** сравнения в `ApproachSafetyGuard.evaluate` при NaN дают False → CONTINUE.

Probe:

```python
import math
from modules.safety_guard import ApproachSafetyGuard, SafetySnapshot

def snap(**over):
    base = dict(altitude_agl=500.0, radio_height=500.0,
                airspeed_indicated=120.0, vertical_speed=-700.0,
                bank=5.0, vref=120.0)
    base.update(over)
    return SafetySnapshot(**base)

cases = {
    "vs_nan": snap(vertical_speed=math.nan),
    "bank_nan": snap(bank=math.nan),
    "ias_nan": snap(airspeed_indicated=math.nan),
    "height_nan": snap(radio_height=math.nan, altitude_agl=math.nan),
    "vs_inf": snap(vertical_speed=math.inf),
}
for name, s in cases.items():
    guard = ApproachSafetyGuard(debounce_n=1)
    r = guard.evaluate(s)
    print(name, "->", r.decision, r.reason)
```

Ожидание при CONFIRMED: все `*_nan` кейсы → `CONTINUE` (fail-open). Отдельно зафиксировать `vs_inf`: `abs(inf) > 1500` истинно, поэтому inf по VS должен дать GO_AROUND — это важный контраст (fail-open только для NaN по этому правилу). Указать по каждому каналу фактическое поведение.

### LV-008 — unit mismatch в расчёте скоростей захода

**Гипотеза (LITE-008):** `_calculate_approach_speeds` передаёт `config.runway_length` (футы) как `runway_length_m` и `aircraft.get('total_weight', 60000)` как кг.

Probe: собрать `AutoLandSystem` без SimConnect (заглушить `telemetry.get_all_data` фиктивным словарём), spy на `speed_calculator.calculate_approach_parameters`, вызвать `_calculate_approach_speeds` с `ApproachConfig(runway_length=8000, ...)`.

Зафиксировать фактические kwargs, попавшие в calculator:

- `runway_length_m` — ожидание при CONFIRMED: `8000` (футы без конверсии; корректно было бы ~2438).
- `aircraft_weight_kg` — зафиксировать источник: содержит ли секция `aircraft` в `modules/telemetry.py` ключ `total_weight` и в каких единицах SimConnect его отдаёт (`grep -n "total_weight" modules/telemetry.py` + название SimVar; TOTAL WEIGHT в SimConnect — фунты). Если ключа в секции `aircraft` нет — зафиксировать, что всегда используется default `60000`, и указать это в вердикте.

Контраст для отчёта: в `configure_approach` тот же `runway_length` корректно конвертируется (`/ 3.28084`, комментарий WP-6) — приложить обе цитаты с номерами строк.

### LV-009 — деление на ноль при GS=0

**Гипотеза:** `Navigation.calculate_landing_distance(ground_speed=0, headwind=10)` → `ZeroDivisionError` в `wind_factor = 1.0 - (headwind / ground_speed * 0.3)`.

Probe: прямой вызов с `ground_speed=0.0, headwind=10.0`. Ожидание при CONFIRMED: `ZeroDivisionError`. Также проверить `ground_speed=0, headwind=0` (0/0) и зафиксировать результат. Затем `grep -rn "calculate_landing_distance" main.py gui.py modules/` — указать все call sites и достижим ли GS=0 в runtime (например, на земле после касания).

### LV-001 — сокрытие ошибок terminal SimConnect writes

**Гипотеза (LITE-001):** каждый `MSFSControl.set_*` проглатывает исключение terminal write и не сообщает caller-у.

Probe: создать `MSFSControl` с фиктивным events-объектом, каждый метод которого бросает `RuntimeError("injected")`. Для КАЖДОГО public `set_*`/командного метода вызвать и зафиксировать: (a) выброшено ли исключение наружу; (b) возвращаемое значение. Ожидание при CONFIRMED: исключение не выходит наружу, возвращается None/False без различения успеха. Приложить таблицу метод → результат.

### LV-002 — частичный go-around

**Гипотеза (LITE-002):** отказ любого шага `execute_go_around` не прерывает последовательность; лог `GO AROUND COMPLETED` появляется при mixed state.

Probe: собрать `AutoLandSystem` с fake control, у которого поочерёдно (по одному прогону на шаг) падает `set_autopilot_master` / `set_throttle` / `set_vertical_speed` / `set_flaps` / `set_gear`; остальные вызовы записываются. По каждому прогону зафиксировать: какие команды были отправлены после отказавшей, появился ли лог completion, каково итоговое состояние. Учитывать реальную семантику production `MSFSControl` (swallow — см. LV-001): вариант A — fake, который бросает исключение; вариант B — fake, который молча «теряет» команду (реалистичный режим). Прогнать оба.

### LV-010 — CI не собирает корневые тесты

Probe:

```bash
pytest --collect-only -q > /tmp/collect_all.txt; tail -3 /tmp/collect_all.txt
pytest tests/ --collect-only -q > /tmp/collect_ci.txt; tail -3 /tmp/collect_ci.txt
ls test_*.py 2>/dev/null
diff <(grep -o '^[^:]*' /tmp/collect_all.txt | sort -u) <(grep -o '^[^:]*' /tmp/collect_ci.txt | sort -u)
```

Зафиксировать: существуют ли корневые `test_*.py`, сколько тестов собирается в каждом наборе, разница. Если корневых тестовых файлов нет — вердикт DISPROVED с доказательством.

### LV-011 — фактический полный прогон тестов

```bash
pytest -q --tb=short 2>&1 | tee /tmp/full_suite.txt
pytest tests/ -q --tb=short 2>&1 | tee /tmp/ci_suite.txt
```

Зафиксировать фактические counts pass/fail/error/skip обоих прогонов. Ничего не предполагать; если есть падения — приложить полные traceback-и первых 5.

### LV-006 — отсутствие staleness-контракта телеметрии (третья очередь)

Это design-gap, а не падение: подтверждается статически. Probe минимальный: `grep -n "time\|timestamp\|monotonic\|perf_counter" modules/telemetry.py` и показать, что `get_all_data()` не добавляет frame timestamp/возраст выборки. Динамический frozen-frame probe — опционально: заглушить `get_all_data` возвратом одного и того же словаря и показать, что control loop не отличает свежий кадр от повторённого.

### LV-007 — обход gateway для vJoy/WASM (третья очередь)

Probe: установить ownership так, чтобы владельцем каналов был `AIRCRAFT_AP`; из контекста EXTERNAL вызвать (a) обёрнутый `CommandGateway`-метод — ожидается `CommandRejected`/отказ; (b) прямой `VirtualJoystick.set_aileron` (spy на `set_axis`) — ожидается, что вызов ПРОХОДИТ без какой-либо авторизации. Контраст (a)/(b) и есть доказательство. WASM-часть — аналогично через `aircraft_adapter`, если импортируем без SimConnect; иначе BLOCKED с причиной.

---

## 4. Формат отчёта

Файл `LV-REPORT-3971ba1.md` + JSON-сводка:

```json
{
  "baseline": "3971ba12113d8994665b1c9a172f2dca6c9e3855",
  "python": "<version>",
  "verdicts": {
    "LV-001": {"verdict": "...", "linked_finding": "LITE-001", "evidence_file": "probes_lv/lv_001_probe.py"},
    "...": {}
  },
  "git_status_clean_except_probes": true,
  "full_suite": {"passed": 0, "failed": 0, "errors": 0, "skipped": 0},
  "ci_suite": {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
}
```

По каждому LV в markdown-отчёте: гипотеза → probe-код → полный вывод → вердикт → примечания (номера строк production-кода, цитаты).

## 5. Стоп-условия

- `BLOCKED_BASELINE_UNAVAILABLE` — SHA недоступен.
- `BLOCKED:<LV-id>` — конкретный probe неисполним (не блокирует остальные).
- Отчёт сдаётся даже при частичных BLOCKED: пакет считается завершённым при вынесенных вердиктах по всем 11 пунктам (включая BLOCKED с причинами).

## 6. Запреты

- Не изменять production-код и тесты.
- Не коммитить и не пушить ничего в репозиторий.
- Не «чинить» дефекты по ходу — только верифицировать.
- Не использовать MagicMock для production-классов.
- Не заявлять вердикт без приложенного сырого вывода.
