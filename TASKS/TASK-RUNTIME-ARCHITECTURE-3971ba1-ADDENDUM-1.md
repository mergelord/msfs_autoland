# TASK: RUNTIME-ARCHITECTURE-3971ba1 — ADDENDUM 1

## Статус ревью

```text
REQUEST_CHANGES
```

Базовый отчёт `RUNTIME-ARCHITECTURE-REPORT.md` пока **не принят**. Production-код не менять. Commit/push не делать. Исправлять только артефакты в `research/runtime_architecture/`.

Baseline остаётся:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

---

## 1. Главный блокер: обязательный harness не завершён

Исходная задача требовала минимум 10 offline-сценариев. Финальный отчёт сообщает:

```text
4 attempted
1 passed
3 failed because telemetry mock was incomplete
```

Неполный mock (`drift_angle`, ошибочный bool attribute и другие отсутствующие поля) — это не ограничение MSFS, а незавершённая реализация harness.

### Требуется

1. Исправить fake telemetry и mock dependencies без изменения production-кода.
2. Реализовать и выполнить все 10 сценариев:
   - ILS FINAL, AP owner;
   - ILS FINAL, vJoy/external owner;
   - non-ILS synthetic glidepath;
   - SafetyGuard GO_AROUND;
   - StabilizedApproachMonitor GO_AROUND;
   - LOC signal loss;
   - takeover initiation;
   - takeover failure;
   - missing telemetry;
   - actuator exception.
3. Для каждого сценария сохранить отдельный trace:

```text
harness/command-traces/<scenario>.json
```

4. Каждый trace должен содержать:
   - ordered call index;
   - requested command;
   - authorization result;
   - backend;
   - final actuator write;
   - arguments;
   - phase before/after;
   - go-around/stop result;
   - exception, если была.
5. `harness/results.json` должен содержать ровно перечисленные сценарии и статусы.
6. Если сценарий не может быть выполнен offline по доказанной технической причине, поставить `UNRESOLVED` с точным объяснением. `FAILED` из-за неполного mock не принимается.
7. Не выдавать существующий pytest-тест за новый harness. Существующие тесты = `TEST_CONFIRMED`; локальные сценарии из `research/runtime_architecture/harness/` = `HARNESS_CONFIRMED`.

---

## 2. Исправить фактический порядок одного кадра

В отчёте есть внутреннее противоречие.

Раздел 21 правильно фиксирует:

```text
takeover
→ weather
→ ownership
→ _control_aircraft
→ _control_throttle
→ _check_stabilization
```

Но раздел 13 снова утверждает:

```text
Safety checks (guard, weather, stabilization)
→ ownership
→ control
→ throttle
```

Это возвращает ошибку capability probe.

### Требуется

Показать два уровня исполнения отдельно.

### Уровень `main._handle_phase()`

Фактический порядок заново подтвердить по строкам baseline, включая относительный порядок:

```text
wind_correction.apply_wind_corrections()
SafetyGuard.evaluate()
phase_state.handle()
```

Не переставлять SafetyGuard и wind correction местами.

### Уровень `FinalPhaseState.handle()`

Точно отразить:

```text
takeover checks
→ weather checks
→ compute_ownership
→ logging
→ _control_aircraft
→ _control_throttle
→ _check_stabilization
→ _deploy_flaps_and_gear
→ DH/LANDING transition guard
```

Указать все early returns.

`StabilizedApproachMonitor` в этом baseline является post-control/post-throttle проверкой текущего кадра. Не объединять его с pre-command `SafetyGuard`.

Исправить согласованно:

- `RUNTIME-ARCHITECTURE-REPORT.md`;
- `frame-command-order.csv`;
- `execution-flow.*`;
- `command-flow.*`;
- `safety-flow.*`;
- `runtime-architecture.json`;
- harness expectations.

---

## 3. Не называть последовательные команды race condition

Фраза о возможной «race condition между SafetyGuard и phase-state commands» пока не доказана.

Основной цикл синхронный. Ситуация:

```text
SafetyGuard = CONTINUE
→ phase sends approach commands
→ StabilizedApproachMonitor triggers GO_AROUND
```

является последовательностью смешанных команд в одном кадре, а не автоматически race condition.

### Требуется

Разделить категории:

- `SEQUENTIAL_MIXED_COMMANDS`;
- `OWNERSHIP_MISMATCH`;
- `CONCURRENT_RACE` — только при доказанной конкурентности;
- `PARTIAL_COMMAND_SEQUENCE`;
- `UNPROVEN`.

Проверить, есть ли реальные threads/tasks/callback concurrency. Если нет доказательства конкурентного доступа, удалить слово `race` и описать последовательный риск.

Также исправить утверждение:

```text
ContextVar is per-frame
```

`ContextVar` является context-local, а не «per-frame». Он хранит `CommandSource`; ownership приходит через provider.

---

## 4. Исправить state/transition counters

Отчёт одновременно говорит:

- `Phase states = 6`;
- `5 states: IDLE → INITIAL → INTERMEDIATE → FINAL → LANDING → COMPLETED` — здесь перечислено 6;
- `Transitions = 9`;
- таблица не объясняет, как получено 9;
- 10 go-around call sites смешиваются с semantic transitions.

### Требуется

Отдельно посчитать и назвать:

1. concrete phase-state classes;
2. abstract/base state classes;
3. lifecycle enum values (`IDLE`, `COMPLETED` и т.д.);
4. forward semantic transitions;
5. go-around/abort semantic transitions;
6. go-around call sites;
7. grouped triggers для одного semantic transition.

Каждый счётчик должен воспроизводиться из `runtime-architecture.json` и совпадать с CSV/отчётом/verifier.

Не называть отсутствие go-around из INITIAL/LANDING `DEAD path`: несуществующая ветка не является dead code. Использовать `NO_TRANSITION_DEFINED`, если это именно отсутствие перехода.

---

## 5. Исправить понятие DEAD/UNREACHED/UNTESTED

Утверждение:

```text
33 modules not imported by tests = 33 untested/unreached modules
```

не доказано. Отсутствие прямого импорта из tests не исключает транзитивное исполнение и покрытие.

### Требуется

Разделить:

- `NO_DIRECT_TEST_IMPORT` — структурная метрика DEPGRAPH;
- `NO_TEST_EXECUTION_EVIDENCE`;
- `UNREACHED_BY_HARNESS`;
- `RUNTIME_UNREACHED`;
- `IMPORT_ISOLATED`;
- `DEAD`.

Для `DEAD` требуется доказанный lifecycle:

```text
not created
AND not called from entry points
AND no callback/registration/dynamic lookup path
```

В отчёте отдельно отразить ранее найденные import-isolated модули, но не автоматически объявлять их runtime-dead без проверки.

Удалить или доказать фразу `33 untested modules` из critical risks.

---

## 6. Исправить data-flow overclaim

Фраза:

```text
Telemetry dict is the sole data bus
```

неверна или как минимум чрезмерна. В проекте также существуют:

- `approach_data`;
- `wind_data`;
- `self.system.*` state;
- `approach_config`;
- ownership objects/provider;
- `ContextVar CommandSource`;
- state objects и их attributes;
- recorder/pending-frame state.

### Требуется

Описать telemetry dict как основной входной telemetry bus, но не единственный data bus системы. Добавить остальные state/data carriers в data dictionary и runtime JSON.

Утверждение «no module writes telemetry dict» либо доказать repository-wide write scan, либо понизить до `STATIC_SCAN_NO_WRITES_FOUND` с описанием метода.

---

## 7. Завершить actuator-sink inventory

Отчёт одновременно утверждает:

```text
72 actuator sinks — all STATIC_CONFIRMED
```

и оставляет unresolved вопрос:

```text
Are there direct ae.event() calls outside control.py and aircraft_adapter.py?
```

Это несовместимо.

### Требуется

1. Выполнить repository-wide scan всех 49 файлов.
2. Закрыть вопрос о direct `ae.event()`.
3. Разделить:
   - unique terminal sink definitions;
   - actuator method definitions;
   - actuator call sites;
   - backend writes;
   - semantic command paths.
4. Не смешивать 47 `ae.event()` call sites и 25 higher-level `set_*()` calls под одним термином sink без явного определения.
5. Убрать приблизительные `~15`, `~10`: финальный inventory должен иметь точные backend counters.
6. Проверить возможный double counting.

---

## 8. Проверить CommandGateway bypass корректно

Для каждого найденного direct `control.set_*()` определить фактический runtime object:

- raw `MSFSControl`;
- `CommandGateway` proxy;
- adapter;
- fake/test control.

Имя вызова `self.system.control.set_*()` само по себе не доказывает bypass: `self.system.control` может быть gateway wrapper.

### Требуется

Для каждого заявленного bypass дать lifecycle evidence:

```text
object creation
→ assignment to self.control
→ possible replacement/wrapping
→ call site
→ actual target
```

Классифицировать:

- `GATEWAY_GUARDED`;
- `RAW_CONTROL_BYPASS`;
- `SAFETY_SCOPE_BYPASS`;
- `VJOY_SEPARATE_BACKEND`;
- `WASM_SEPARATE_BACKEND`;
- `UNRESOLVED`.

Не оставлять общий вывод `some paths bypass CommandGateway` без списка доказанных путей.

---

## 9. Исправить harness/evidence terminology

`offline takeaway instantiation (test_wp0_smoke.py)` содержит две проблемы:

1. вероятная опечатка `takeaway` вместо `takeover`;
2. существующий `test_wp0_smoke.py` не является новым harness автоматически.

### Требуется

Для каждого `TEST_CONFIRMED` указать конкретный test function и assertion.

Для каждого `HARNESS_CONFIRMED` указать:

- harness scenario id;
- trace file;
- expected order;
- observed order;
- pass/fail condition.

---

## 10. Усилить verifier

Текущий verifier не может считаться достаточным, если возвращает `PASS` при:

- 1/10 обязательных harness-сценариев;
- противоречивых state counters;
- приблизительных backend counts;
- unresolved repository-wide actuator question;
- несогласованном command order.

### Требуется

`verify_runtime_architecture.py` должен fail non-zero, если:

1. baseline commit не совпадает;
2. production files != 49;
3. DEPGRAPH reconciliation != 49/49;
4. отсутствует обязательный артефакт;
5. обязательные harness scenario IDs отсутствуют;
6. trace-файл отсутствует для выполненного сценария;
7. counters JSON/CSV/report расходятся;
8. backend counter приблизительный или отсутствует;
9. MMD/DOT edge отсутствует в JSON;
10. file:line выходит за границы файла;
11. manifest hash не совпадает;
12. report содержит старую ошибочную последовательность FinalPhaseState;
13. `RUNTIME_CONFIRMED > 0` без MSFS evidence.

После исправлений запустить verifier и сохранить полный stdout.

---

## 11. Git cleanliness proof

Не достаточно только:

```text
?? TASKS/
?? research/
```

Предоставить:

```powershell
git rev-parse HEAD
git diff --exit-code
git diff --cached --exit-code
git status --short
```

`TASKS/` и существующий `research/depgraph/` являются заранее известными untracked-каталогами. Подтвердить, что новые файлы находятся только в `research/runtime_architecture/`.

---

## 12. Package for independent review

После исправлений упаковать весь каталог:

```text
research/runtime_architecture/
```

в:

```text
RUNTIME-ARCHITECTURE-3971ba1-v2.zip
```

ZIP должен включать:

- все CSV;
- все MMD/DOT/PNG;
- `runtime-architecture.json`;
- отчёт;
- scanner/build scripts;
- verifier;
- manifest;
- весь `harness/`;
- command traces;
- сохранённый verifier stdout.

В чат приложить ZIP как файл. Не копировать Mermaid/JSON/CSV в чат.

---

## 13. Финальный статус

Использовать:

```text
COMPLETED_WITH_UNRESOLVED
```

только если все offline-выполнимые требования закрыты, а unresolved действительно требуют MSFS/оборудование или отсутствующую спецификацию.

Если обязательные offline-сценарии остаются сломаны из-за mock/harness, статус:

```text
INCOMPLETE_HARNESS
```

Финальный ответ должен кратко перечислить:

```text
STATUS
CORRECTIONS_APPLIED
EXACT_COUNTERS
HARNESS_10_SCENARIOS
VERIFIER
DEPGRAPH_RECONCILIATION
UNRESOLVED_REQUIRING_MSFS
ZIP_PATH
GIT_PROOF
```

---

## Критерий приёмки addendum

> Полный runtime snapshot должен быть внутренне непротиворечивым и машинно проверяемым. Красивые диаграммы и `PASS` verifier не компенсируют незавершённый offline harness, смешение evidence levels или неправильный порядок команд.
