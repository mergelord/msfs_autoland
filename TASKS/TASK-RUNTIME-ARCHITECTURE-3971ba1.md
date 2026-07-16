# TASK: RUNTIME-ARCHITECTURE-3971ba1

## 0. Цель

Построить доказательную архитектурную модель исполнения проекта `msfs_autoland`:

1. lifecycle и порядок исполнения;
2. state machine фаз захода;
3. потоки телеметрии и вычисленных данных;
4. формирование, авторизация и отправка управляющих команд;
5. safety/fail-safe, go-around, abort и manual takeover;
6. фактическое подключение либо недостижимость production-модулей.

Результат должен позволить определить готовность проекта к контролируемым полётным тестам в MSFS.

Это **анализ**, а не bugfix-задача.

---

## 1. Baseline

- Repository: `zhuk-mou-1/msfs_autoland`
- Branch: `master`
- Commit: `3971ba12113d8994665b1c9a172f2dca6c9e3855`
- Рабочий каталог: `C:\BAT\msfs_autoland`
- Python: 3.14.5
- Существующий импортный граф: `research/depgraph/`
- Production scope:
  - 47 Python-файлов в `modules/`;
  - `main.py`;
  - `gui.py`;
  - всего 49 узлов.

Перед началом подтвердить:

```powershell
git rev-parse HEAD
git status --short
```

Если HEAD отличается от baseline — остановиться со статусом:

```text
BLOCKED_WRONG_BASELINE
```

---

## 2. Запреты

- Не изменять production-код.
- Не исправлять найденные дефекты.
- Не делать commit.
- Не делать push.
- Не менять существующие тесты.
- Не добавлять instrumentation в production-код.
- Не считать импорт доказательством создания или исполнения компонента.
- Не считать существование класса доказательством его подключения.
- Не считать существование теста доказательством runtime-пути.
- Не пересказывать содержимое `.mmd` в чат.
- Не заявлять `RUNTIME_CONFIRMED` без реального запуска с MSFS.
- Не использовать Mermaid-вставку в чат как артефакт: только файлы на диске.
- Не доверять результатам подагентов без проверки ведущим агентом.

Разрешено создавать только локальные аналитические файлы в:

```text
research/runtime_architecture/
```

Они должны оставаться untracked.

---

## 3. Организация работы

Задача выполняется последовательно в четыре этапа:

1. Inventory + Execution + State Machine
2. Data Flow + Command Flow
3. Safety Flow + Dynamic Harness
4. Cross-validation + Final Report

Допускается делегирование независимых исследований подагентам.

### Правила делегирования

Подагентам можно поручать:

- поиск call sites;
- сбор `file:line`;
- извлечение `self.system.*`;
- анализ отдельных подсистем;
- построение черновых таблиц.

Ведущий MiMo обязан лично перепроверить:

- основной цикл;
- все переходы фаз;
- все actuator sinks;
- `CommandGateway` и ownership;
- все go-around call sites;
- порядок команд внутри одного кадра;
- все выводы уровня `TEST_CONFIRMED` и выше;
- итоговые счётчики и соответствие JSON ↔ MMD ↔ PNG ↔ отчёт.

Если подагенты дали противоречивые результаты, не выбирать наиболее правдоподобный. Вернуться к исходникам и разрешить противоречие через `file:line`.

---

## 4. Обязательные коррекции после capability probe

Не переносить следующие ошибки probe в финальные артефакты.

### 4.1 Wind correction

Неверно:

```text
approach_phases.py:10
→ wind_correction.apply_wind_corrections()
```

Вызов wind correction находится в:

```text
main.py::_handle_phase()
→ self.wind_correction.apply_wind_corrections(...)
```

`approach_phases.py:10` не является этим вызовом. Полную цепочку заново подтвердить по baseline.

### 4.2 Порядок `FinalPhaseState.handle()`

Не использовать ошибочный порядок из probe:

```text
_check_stabilization
→ _control_aircraft
→ _control_throttle
```

На baseline фактическая последовательность включает:

```text
takeover checks
→ weather checks
→ compute_ownership
→ logging
→ _control_aircraft
→ _control_throttle
→ _check_stabilization
→ _deploy_flaps_and_gear
→ DH/LANDING guard
```

Номера строк и все early-return подтвердить заново.

Обязательно разделить:

- глобальный `SafetyGuard` в `main._handle_phase()` — pre-command;
- phase-level `StabilizedApproachMonitor` — в текущем baseline вызывается после control/throttle-команд внутри FINAL.

Не объединять эти проверки в один абстрактный «safety before commands».

### 4.3 Actuator paths

Неверно утверждать:

```text
Все команды проходят через self.system.control → control.py
```

Исследовать как минимум отдельные выходы:

1. `CommandGateway` / `control.py` → SimConnect events;
2. `virtual_joystick.py` → vJoy;
3. `aircraft_adapter.py` → WASM/LVAR;
4. SimConnect fallback внутри `aircraft_adapter`;
5. любые прямые обращения к `ae.event`, SimConnect, WASM или vJoy вне этих файлов.

Провести repository-wide search по всем 49 файлам.

### 4.4 `ContextVar` и ownership

Не утверждать, что `ControlOwnership` хранится в `ContextVar`.

На baseline:

- `_SOURCE: ContextVar` хранит `CommandSource`;
- ownership получается через `ownership_provider`;
- `CommandGateway._authorize()` сравнивает фактический источник с владельцем канала;
- конкретные runtime-значения ownership зависят от состояния системы.

На схеме отдельно показать:

```text
compute_ownership()
→ ownership_provider
→ expected owner by channel

source_scope()
→ ContextVar CommandSource
→ actual source

CommandGateway._authorize()
→ allow / CommandRejected
```

### 4.5 Go-around call sites

Не использовать фразу «4 места» из probe: там было перечислено 6, а список не был доказан полным.

Автоматически собрать **все** вызовы `execute_go_around(...)` по всем 49 production-файлам.

Для каждого указать:

- файл и строку;
- enclosing function/method;
- trigger condition;
- phase;
- вызываются ли actuator-команды до go-around;
- evidence level;
- достижимость;
- тест, если существует.

Отдельно проверить LOC-loss путь в `main._calculate_approach_data()`.

### 4.6 Scope

Deep review может охватывать 15–20 критических файлов, но inventory и автоматический scan обязаны охватить **все 49 production-файлов**.

---

## 5. Evidence model

Каждому ребру назначить ровно один основной уровень доказательства:

```text
STATIC_CONFIRMED
TEST_CONFIRMED
HARNESS_CONFIRMED
RUNTIME_CONFIRMED
INFERRED
UNREACHED
DEAD
```

### Определения

#### `STATIC_CONFIRMED`

Вызов, чтение, запись или переход непосредственно доказан исходником с `file:line`.

#### `TEST_CONFIRMED`

Путь фактически выполнен существующим pytest-тестом. Требуется указать:

- тест;
- test function;
- assertion;
- production path, который он подтверждает.

Одного имени тестового файла недостаточно.

#### `HARNESS_CONFIRMED`

Путь выполнен новым локальным harness из `research/runtime_architecture/harness/` с mock/stub-зависимостями.

#### `RUNTIME_CONFIRMED`

Использовать только для данных реального запуска с MSFS. Если MSFS не запускался, ожидаемое количество таких рёбер: `0`.

#### `INFERRED`

Связь логически предполагается, но прямого исполнения или однозначного статического доказательства нет.

#### `UNREACHED`

Путь присутствует, но не достигнут тестами/harness.

#### `DEAD`

Компонент или путь доказанно не создаётся и не вызывается от entry points на baseline.

---

## 6. Типы рёбер

Каждое ребро в JSON должно иметь один из типов:

```text
create
call
callback
signal
read
write
transform
state_transition
command_request
ownership_compute
authorize
command_allowed
command_rejected
actuator_write
feedback
fallback
exception
retry
go_around
abort
takeover
shutdown
```

При необходимости можно добавить новый тип, но задокументировать его в отчёте.

---

## 7. Этап 1 — Inventory, Execution Flow, Phase State Machine

### 7.1 Production inventory

Для каждого из 49 файлов определить:

- module name;
- role;
- entry point status;
- создаваемые классы;
- global/singleton state;
- production callers;
- callbacks/signals;
- status: `ACTIVE`, `CONDITIONAL`, `FALLBACK`, `UNREACHED`, `DEAD`, `ENTRY_POINT` или `TYPE_ONLY`.

Сохранить:

```text
research/runtime_architecture/module-inventory.csv
```

Обязательные колонки:

```text
module
file
role
status
created_at
called_from
entry_point
actuator_access
telemetry_access
shared_state_access
evidence
notes
```

### 7.2 Execution flow

Построить фактический lifecycle:

```text
GUI / CLI start
→ AutoLandSystem construction
→ component construction
→ connection setup
→ configuration loading
→ approach start
→ main loop
→ telemetry acquisition
→ approach calculation
→ safety guard
→ phase dispatch
→ actuator commands
→ recording
→ retry / failure
→ touchdown / go-around / stop
→ shutdown
```

Для каждого шага:

- source file/line;
- target file/line;
- condition;
- exception behavior;
- whether it can terminate the loop;
- evidence level.

Артефакты:

```text
execution-flow.mmd
execution-flow.dot
execution-flow.png
```

### 7.3 Phase State Machine

Найти все классы состояний и все переходы:

- source state;
- destination state;
- guard condition;
- telemetry/config inputs;
- side effects before transition;
- actuator commands before transition;
- failure/early-return path;
- go-around path;
- reachability;
- evidence.

Артефакты:

```text
phase-state-machine.mmd
phase-state-machine.dot
phase-state-machine.png
phase-transitions.csv
```

Обязательно проверить:

- количество state classes;
- начальное состояние;
- все места изменения `phase_state`;
- соответствие `phase_state` и enum `phase`;
- переходы в LANDING/COMPLETED;
- возврат `None`;
- go-around и stop paths;
- manual takeover.

---

## 8. Этап 2 — Data Flow и Command Flow

### 8.1 Data-flow inventory

Проследить минимум следующие данные:

- latitude/longitude;
- altitude MSL;
- altitude AGL;
- radio height;
- indicated airspeed;
- ground speed;
- vertical speed;
- heading/course;
- bank/pitch;
- localizer deviation;
- glideslope deviation;
- ILS/LOC availability;
- DME;
- wind;
- turbulence/wind shear;
- engine state;
- flap/gear state;
- approach configuration;
- runway elevation;
- decision height/MDA;
- telemetry timestamp/age, если существует;
- calculated target heading;
- target vertical speed;
- target throttle;
- vJoy axis commands.

Для каждого значения указать:

```text
source
raw key / attribute
unit
sign convention
normalization
validation
fallback/default
consumers
final command influence
file:line evidence
```

Сохранить:

```text
data-dictionary.csv
data-flow.mmd
data-flow.dot
data-flow.png
```

Отдельно отметить:

- смешение AGL/MSL;
- sign conventions для vertical speed;
- преобразования `float → int`;
- возможные `None`, missing key, NaN, inf;
- stale telemetry handling;
- значения, для которых источник или единица не доказаны.

### 8.2 Command sink inventory

Repository-wide scan всех 49 файлов на:

- `self.ae.event(...)`;
- SimConnect event/data writes;
- `set_*` actuator methods;
- WASM/LVAR writes;
- vJoy writes;
- direct joystick writes;
- adapter fallbacks;
- dynamic dispatch через `getattr`;
- callbacks, которые могут отправить команду.

Сохранить:

```text
actuator-sinks.csv
```

Колонки:

```text
sink_id
file
line
enclosing_function
backend
channel
command
input_unit
range
clamp
owner_required
source_scope
failure_behavior
callers
evidence
```

### 8.3 Command flow

Для каждого управляющего канала построить цепочку:

```text
telemetry
→ calculation
→ requested command
→ ownership computation
→ source classification
→ CommandGateway authorization
→ clamp/rate limit
→ backend
→ actuator write
```

Каналы как минимум:

```text
roll
pitch
throttle
configuration
navigation
autopilot
```

Отдельно показать альтернативные backends:

```text
AIRCRAFT_AP / SimConnect
EXTERNAL / vJoy
WASM / LVAR
SAFETY override
```

Артефакты:

```text
command-flow.mmd
command-flow.dot
command-flow.png
command-paths.csv
```

### 8.4 Command-order analysis

Для каждой фазы определить точный порядок в одном кадре:

- safety checks;
- ownership calculation;
- heading/roll;
- pitch/vertical speed;
- throttle;
- flaps/gear;
- recorder;
- phase transition;
- go-around;
- exception handling.

Не считать порядок доказанным только по списку методов. Учитывать `if`, early return, exceptions, callbacks, fallback, разные ownership и разные approach types.

Построить минимум следующие сценарии:

1. ILS FINAL, AP owner;
2. ILS FINAL, vJoy/external owner;
3. non-ILS synthetic glidepath;
4. SafetyGuard GO_AROUND;
5. stabilized monitor GO_AROUND;
6. LOC signal loss;
7. takeover initiation;
8. takeover failure;
9. missing telemetry;
10. actuator exception.

Сохранить:

```text
frame-command-order.csv
```

---

## 9. Этап 3 — Safety Flow и Dynamic Harness

### 9.1 Safety inventory

Проверить:

- `SafetyGuard`;
- `StabilizedApproachMonitor`;
- `AutopilotTakeover`;
- wind shear;
- turbulence;
- connection monitoring;
- error budget;
- engine failure detector;
- telemetry validation;
- command ownership;
- go-around;
- stop/shutdown;
- manual takeover;
- actuator exceptions.

Для каждого механизма определить:

```text
created?
stored?
updated?
called?
phase?
inputs?
decision?
side effects?
actuator commands?
fallback?
test?
reachable?
```

Особенно проверить lifecycle:

```text
imported
→ instantiated
→ configured
→ called
→ result consumed
```

Не считать модуль рабочим, если доказан только импорт или создание.

### 9.2 Fail-safe matrix

Сохранить:

```text
fail-safe-matrix.csv
```

Сценарии минимум:

- missing telemetry key;
- stale telemetry;
- `None`;
- NaN/inf;
- SimConnect read exception;
- SimConnect write exception;
- connection loss;
- reconnect;
- ILS loss;
- LOC loss;
- glideslope loss;
- excessive deviation;
- unstable approach;
- wind shear;
- turbulence;
- engine failure;
- ownership mismatch;
- `CommandRejected`;
- vJoy unavailable;
- WASM unavailable;
- aircraft adapter fallback;
- takeover failure;
- go-around failure partway through command sequence;
- telemetry recorder exception;
- main-loop consecutive error budget.

Для каждого:

```text
detection
decision
commands before detection
final action
hold-last?
neutral?
retry?
go-around?
stop?
exception swallowed?
logging?
test/harness coverage
```

### 9.3 Safety flow

Артефакты:

```text
safety-flow.mmd
safety-flow.dot
safety-flow.png
```

На схеме явно различать:

- pre-command protection;
- post-command detection;
- authorization;
- fallback;
- go-around;
- stop;
- manual intervention required.

### 9.4 Local dynamic harness

Создать только локально:

```text
research/runtime_architecture/harness/
```

Не менять production-код и существующие тесты.

Harness должен:

- создавать систему или phase states с Fake/MagicMock dependencies;
- подавать детерминированную telemetry;
- перехватывать вызовы CommandGateway/control, raw SimConnect event sink, vJoy, WASM/LVAR и aircraft adapter;
- фиксировать глобальный порядок вызовов;
- сохранять аргументы;
- фиксировать phase transitions;
- фиксировать go-around/stop;
- фиксировать rejected commands;
- отличать requested command от фактического actuator write.

Минимальные сценарии harness соответствуют десяти сценариям из раздела 8.4.

Результаты:

```text
harness/results.json
harness/command-traces/*.json
harness/README.md
```

Если какой-либо backend невозможно перехватить без production-изменений, отметить это как ограничение — не имитировать успешную проверку.

---

## 10. Этап 4 — Cross-validation

### 10.1 JSON registry

Создать:

```text
runtime-architecture.json
```

Минимальная структура:

```json
{
  "meta": {
    "repository": "zhuk-mou-1/msfs_autoland",
    "commit": "3971ba12113d8994665b1c9a172f2dca6c9e3855",
    "generated_at": "...",
    "production_files_scanned": 49
  },
  "nodes": [],
  "edges": [],
  "states": [],
  "data_items": [],
  "actuator_sinks": [],
  "safety_mechanisms": [],
  "scenarios": [],
  "unresolved": []
}
```

Каждое edge:

```json
{
  "id": "...",
  "src": "...",
  "dst": "...",
  "type": "call",
  "source_file": "...",
  "source_line": 0,
  "target_file": "...",
  "target_line": 0,
  "enclosing_function": "...",
  "phase": "...",
  "condition": "...",
  "channel": "...",
  "backend": "...",
  "evidence_level": "STATIC_CONFIRMED",
  "evidence_ref": "...",
  "notes": "..."
}
```

Не объединять разные call sites в одно ребро без сохранения всех evidence locations.

Отдельно считать:

- unique semantic edges;
- call-site entries;
- test-confirmed edges;
- harness-confirmed edges;
- inferred;
- unreached;
- dead;
- unresolved.

### 10.2 Cross-check JSON ↔ схемы

Автоматически проверить:

- каждый узел MMD/DOT существует в JSON;
- каждое ребро MMD/DOT существует в JSON;
- все `file:line` находятся внутри соответствующих файлов;
- production scan count = 49;
- actuator sink count одинаков в JSON и CSV;
- state transition count одинаков в JSON и CSV;
- go-around call-site count одинаков в JSON и отчёте;
- PNG построены из соответствующих `.dot`;
- SHA-256 всех артефактов записаны в manifest.

Создать:

```text
artifact-manifest.json
verify_runtime_architecture.py
```

`verify_runtime_architecture.py` должен завершаться `PASS` или ненулевым exit code при расхождении.

---

## 11. Итоговые артефакты

Все файлы:

```text
research/runtime_architecture/
├── module-inventory.csv
├── data-dictionary.csv
├── actuator-sinks.csv
├── command-paths.csv
├── phase-transitions.csv
├── frame-command-order.csv
├── fail-safe-matrix.csv
├── execution-flow.mmd
├── execution-flow.dot
├── execution-flow.png
├── phase-state-machine.mmd
├── phase-state-machine.dot
├── phase-state-machine.png
├── data-flow.mmd
├── data-flow.dot
├── data-flow.png
├── command-flow.mmd
├── command-flow.dot
├── command-flow.png
├── safety-flow.mmd
├── safety-flow.dot
├── safety-flow.png
├── runtime-architecture.json
├── RUNTIME-ARCHITECTURE-REPORT.md
├── verify_runtime_architecture.py
├── artifact-manifest.json
└── harness/
    ├── README.md
    ├── results.json
    └── command-traces/
```

Если какой-то обязательный файл не создан, финальный статус не может быть `COMPLETED`.

---

## 12. Требования к диаграммам

### Цвета

- зелёный — `HARNESS_CONFIRMED` или `TEST_CONFIRMED`;
- синий — `STATIC_CONFIRMED`;
- жёлтый — `INFERRED` или `UNREACHED`;
- красный — `DEAD`, rejected, unsafe/error path;
- серый пунктир — optional/fallback/TYPE_CHECKING;
- красный пунктир — go-around/abort/failure.

### Читаемость

- использовать subgraph/layers;
- не помещать 200–300 рёбер на один PNG без группировки;
- при необходимости создавать дополнительные detail diagrams;
- master-схема должна оставаться читаемой;
- PNG строить через Graphviz;
- `.mmd` сохранять как исходный Mermaid;
- содержимое `.mmd` в чат не вставлять.

---

## 13. Финальный отчёт

`RUNTIME-ARCHITECTURE-REPORT.md` должен содержать:

1. Executive verdict.
2. Baseline и scope.
3. Методологию.
4. Полный lifecycle.
5. Phase state machine.
6. Data-flow findings.
7. Command-flow findings.
8. Ownership и authorization.
9. Actuator sinks.
10. Safety/fail-safe.
11. Go-around call sites.
12. Manual takeover.
13. Dead/unreached/conditional modules.
14. Command-order findings.
15. Test/harness coverage.
16. Что нельзя подтвердить без MSFS.
17. Архитектурные риски.
18. Блокеры контролируемых полётных тестов.
19. Блокеры автономных тестов.
20. Рекомендованный runtime test plan.
21. Все unresolved вопросы.
22. Таблицу исправлений относительно capability probe.

Не исправлять найденные проблемы — только документировать.

---

## 14. Обязательные итоговые вопросы

Отчёт должен дать доказательные ответы:

1. Какой точный путь проходит один telemetry frame?
2. Какие проверки выполняются до первой actuator-команды?
3. Какие проверки выполняются после actuator-команд?
4. Может ли один кадр отправить конфликтующие команды?
5. Все ли SimConnect-команды проходят через `CommandGateway`?
6. Можно ли обойти ownership через raw control, adapter, WASM или vJoy?
7. Что происходит при `CommandRejected`?
8. Что происходит, если go-around частично отправил команды и затем получил исключение?
9. Какие команды могли быть отправлены до решения о нестабилизированном заходе?
10. Какие safety-модули импортированы, но не включены в runtime?
11. Где существует hold-last-command?
12. Где ошибки проглатываются через `except Exception`?
13. Какие telemetry values не имеют проверки возраста или валидности?
14. Какие пути подтверждены harness, но не реальным MSFS?
15. Что необходимо проверить первым в реальном simulator run?

---

## 15. Acceptance criteria

Задача принимается только если:

- baseline commit подтверждён;
- все 49 production-файлов просканированы;
- каждый файл классифицирован;
- все phase states и transitions перечислены;
- все `execute_go_around()` call sites перечислены;
- все actuator sinks перечислены;
- SimConnect, vJoy и WASM показаны раздельно;
- `CommandSource` и `ControlOwnership` не смешаны;
- pre-command и post-command safety разделены;
- порядок команд проверен по веткам и early returns;
- для каждого значимого ребра есть `file:line`;
- существующие тесты привязаны к конкретным assertions;
- harness результаты воспроизводимы;
- `RUNTIME_CONFIRMED = 0`, если MSFS не запускался;
- JSON, CSV, MMD, DOT, PNG и отчёт согласованы;
- verifier возвращает `PASS`;
- production-код не изменён;
- commit отсутствует;
- `git status --short` показывает только `research/runtime_architecture/`.

---

## 16. Формат финального ответа в чат

Не вставлять Mermaid и содержимое больших CSV/JSON.

Начать ровно с одного статуса:

```text
COMPLETED
```

или:

```text
COMPLETED_WITH_UNRESOLVED
```

или:

```text
BLOCKED
```

Затем:

```text
BASELINE
SCOPE
COUNTERS
EVIDENCE_LEVELS
KEY_FINDINGS
CRITICAL_RISKS
UNRESOLVED
HARNESS_RESULTS
VERIFICATION
ARTIFACT_PATHS
GIT_STATUS
```

В `COUNTERS` указать:

- production files scanned;
- nodes;
- semantic edges;
- call-site entries;
- phase states;
- transitions;
- `self.system.*` accesses;
- actuator sinks by backend;
- go-around call sites;
- safety mechanisms;
- test-confirmed;
- harness-confirmed;
- static-only;
- inferred;
- unreached;
- dead;
- runtime-confirmed;
- unresolved.

В `ARTIFACT_PATHS` перечислить только пути файлов. Содержимое `.mmd` в чат не копировать.

---

## 17. Stop conditions

Остановиться с `BLOCKED`, если:

- baseline неверен;
- часть production tree недоступна;
- невозможно доказать номера строк;
- verifier не проходит;
- артефакты противоречат друг другу;
- пришлось бы изменять production-код;
- результаты подагентов невозможно перепроверить.

Остановиться с `COMPLETED_WITH_UNRESOLVED`, если статическая модель завершена, но отдельные пути невозможно подтвердить без MSFS. Это допустимый и честный результат.

---

## Главный принцип задачи

> Не строить красивую историю о работе системы. Построить воспроизводимую карту доказанных путей, отдельно обозначив предположения, недостижимые ветки и то, что невозможно подтвердить без MSFS.
