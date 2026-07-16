# TASK: EXTERNAL-AUDIT-PASS-A-BLIND-3971ba1

## 0. Назначение задачи

Провести **полностью независимый комплексный аудит кодовой базы** проекта `msfs_autoland` на фиксированном baseline, не используя ранее построенные архитектурные схемы, отчёты, findings или рекомендации.

Это **Проход A — слепой code-first audit**.

Цель — независимо восстановить фактическую архитектуру, runtime lifecycle, потоки данных, управляющие команды, safety/fail-safe и готовность проекта к испытаниям, опираясь только на исходный код, тесты, конфигурацию и воспроизводимые проверки.

Результат Прохода A должен быть завершён, упакован и зафиксирован SHA-256 **до предоставления аудитору архитектурного snapshot**. Сравнение с существующей документацией будет отдельным Проходом B и в эту задачу не входит.

---

## 1. Repository и baseline

- **Конкретный репозиторий для исследования:**

```text
https://github.com/zhuk-mou-1/msfs_autoland
```

- Git clone URL:

```text
https://github.com/zhuk-mou-1/msfs_autoland.git
```

- Canonical owner/repository:

```text
zhuk-mou-1/msfs_autoland
```

- Branch для чтения:

```text
master
```

Использовать только этот репозиторий. **Не использовать старый репозиторий**:

```text
mergelord/msfs_autoland
```

Если локального checkout нет, создать отдельный каталог для слепого аудита:

```bash
git clone https://github.com/zhuk-mou-1/msfs_autoland.git msfs_autoland-pass-a
cd msfs_autoland-pass-a
git checkout --detach 3971ba12113d8994665b1c9a172f2dca6c9e3855
```

После checkout обязательно подтвердить:

```bash
git remote get-url origin
git rev-parse HEAD
```

Ожидается:

```text
origin = https://github.com/zhuk-mou-1/msfs_autoland.git
HEAD   = 3971ba12113d8994665b1c9a172f2dca6c9e3855
```

Если remote указывает на другой repository, fork с неизвестными изменениями или старый `mergelord/msfs_autoland`, остановиться:

```text
BLOCKED_WRONG_REPOSITORY
```

- Единственный разрешённый baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

- Production scope:

```text
47 Python-файлов в modules/
+ main.py
+ gui.py
= 49 production-файлов
```

Перед аудитом выполнить:

```bash
git rev-parse HEAD
git status --short
git show --no-patch --format=fuller 3971ba12113d8994665b1c9a172f2dca6c9e3855
```

Если HEAD не совпадает с baseline, создать отдельный read-only worktree/checkout именно этого commit.

Если baseline недоступен — остановиться:

```text
BLOCKED_BASELINE_UNAVAILABLE
```

---

## 2. Строгая blind-изоляция

### 2.1 Запрещённые источники

До завершения и хеширования Прохода A **не читать и не искать**:

```text
docs/architecture/**
research/depgraph/**
research/runtime_architecture/**
TASKS/**
любые RUNTIME-ARCHITECTURE-REPORT*.md
любые DEPGRAPH-REPORT*.md
любые AUDIT-*.md
любые BENCH-AUDIT-*.md
любые FINDINGS.json из предыдущих аудитов
Notion-страницы проекта
предыдущую переписку Claude/MiMo/других аудиторов
PR review comments, содержащие архитектурные выводы
GitHub Issues/Discussions с результатами прошлых аудитов
```

Не искать в интернете сочетания:

```text
msfs_autoland audit
msfs_autoland architecture
msfs_autoland findings
3971ba1 audit
```

Если архитектурные docs уже присутствуют в рабочем tree, исключить их из области чтения и поиска.

### 2.2 Разрешённые источники

Разрешено читать:

```text
main.py
gui.py
modules/**/*.py
tests/**/*.py
корневые test_*.py
config/**
requirements*.txt
pyproject.toml
.github/workflows/**
README.md
.gitignore
другие build/runtime configuration files
```

Разрешено обращаться к официальной документации Python, SimConnect, MSFS SDK, vJoy и авиационным/математическим стандартам, если это требуется для проверки контракта. Каждую внешнюю ссылку цитировать. Не использовать внешние статьи, пересказывающие именно этот проект.

### 2.3 Декларация слепоты

В начале создать:

```text
BLINDNESS-DECLARATION.md
```

Указать:

- baseline;
- разрешённые источники;
- запрещённые источники;
- были ли какие-либо запрещённые материалы случайно просмотрены;
- `contamination_status`:

```text
CLEAN
PARTIALLY_CONTAMINATED
CONTAMINATED
```

Если запрещённый архитектурный отчёт был прочитан до фиксации собственных выводов:

- немедленно сообщить;
- не скрывать факт;
- по возможности перезапустить аудит в новом чистом контексте;
- финальный статус не может быть `BLIND_AUDIT_COMPLETE` при `CONTAMINATED`.

---

## 3. Режим работы

Это audit-only task.

Запрещено:

- изменять production-код;
- исправлять найденные дефекты;
- менять существующие тесты;
- создавать commit;
- создавать branch;
- делать push/PR;
- ослаблять assertions;
- добавлять suppressions;
- устанавливать постоянные зависимости в repository environment без отчёта;
- выдавать гипотезу за подтверждённый runtime path.

Разрешено:

- запускать существующие тесты;
- запускать линтеры и статические анализаторы;
- создавать локальные audit scripts и mock/probe harness **только вне tracked production tree**;
- создавать временные worktree/venv;
- писать результаты в отдельный каталог аудита;
- удалять только собственные временные файлы после упаковки.

Рекомендуемый output root вне repository:

```text
C:\BAT\external_audits\msfs_autoland\PASS-A-3971ba1\
```

или эквивалентный отдельный каталог.

---

## 4. Главные принципы доказательности

### 4.1 Импорт не доказывает исполнение

Для каждой подсистемы проверять lifecycle:

```text
imported
→ instantiated
→ configured
→ registered/connected
→ called
→ result consumed
→ side effect observed
```

Не считать модуль активным по одному импорту или наличию класса.

### 4.2 Каждый вывод должен иметь evidence

Для значимых утверждений обязательны:

```text
file:line
function/class
trigger condition
execution path
actual behavior
expected behavior
impact
```

### 4.3 Evidence levels

Использовать только:

```text
STATIC_CONFIRMED
TEST_REPRODUCED
PROBE_REPRODUCED
INFERRED
REQUIRES_MSFS
DISPROVED
UNRESOLVED
```

Определения:

- `STATIC_CONFIRMED` — однозначно следует из исходника и call path.
- `TEST_REPRODUCED` — существующий тест выполняет путь и содержит релевантный assertion.
- `PROBE_REPRODUCED` — независимый локальный probe/harness воспроизвёл поведение.
- `INFERRED` — правдоподобно, но путь или эффект не подтверждён полностью.
- `REQUIRES_MSFS` — нельзя подтвердить без реального MSFS/SimConnect/WASM/vJoy.
- `DISPROVED` — кандидат проверен и опровергнут.
- `UNRESOLVED` — доказательств недостаточно, причина указана.

Не использовать слово `confirmed`, если уровень ниже `STATIC_CONFIRMED`.

### 4.4 Разделять типы результатов

Каждый результат классифицировать как:

```text
DEFECT
ARCHITECTURE_RISK
SAFETY_RISK
TEST_GAP
OBSERVABILITY_GAP
MAINTAINABILITY_DEBT
DEAD_OR_UNREACHED_CODE
DOCUMENTATION_MISMATCH
QUESTION
```

---

## 5. Severity и confidence

### Severity

```text
P0 — вероятная неконтролируемая/опасная команда, потеря критического safety-path,
     системный отказ основного контура или отсутствие безопасного выхода;
     блокирует любые управляемые MSFS-тесты.

P1 — существенный дефект критического runtime-path, navigation/control/safety;
     блокирует расширенные полётные тесты до исправления.

P2 — дефект или архитектурный риск, который не обязательно блокирует первый
     контролируемый тест, но блокирует автономные/широкие серии.

P3 — maintainability, observability, cleanup, documentation или низкорисковый edge case.

INFO — подтверждённое архитектурное наблюдение без дефекта.
```

### Confidence

```text
HIGH — прямой call path + source evidence + test/probe либо однозначная логика.
MEDIUM — source evidence полное, но runtime effect требует внешней зависимости.
LOW — гипотеза/неполный путь; не может быть P0/P1 без дополнительного доказательства.
```

Каждая P0/P1 finding обязана иметь:

- `confidence = HIGH` или аргументированное `MEDIUM`;
- полный call path;
- reproducer/probe либо точное объяснение, почему нужен MSFS;
- конкретный operational impact;
- минимальный acceptance test для будущего исправления.

---

## 6. Этап 0 — Preflight и environment

Зафиксировать:

```text
OS
Python version
active environment
pytest version
installed project dependencies
Graphviz/Mermaid availability
ruff/mypy/bandit/radon availability
Git commit
Git status
```

Проверить, что audit output не попадает в git status repository.

Запустить минимум:

```bash
python -m compileall main.py gui.py modules tests
pytest tests/
```

Если проектные CI-команды доступны, дополнительно:

```bash
ruff check .
mypy main.py gui.py modules
radon cc main.py gui.py modules -s -a
bandit -r main.py gui.py modules
```

Не трактовать non-blocking mypy/radon/bandit warnings как runtime defect без анализа.

Сохранить полный вывод:

```text
logs/environment.txt
logs/compileall.txt
logs/pytest.txt
logs/ruff.txt
logs/mypy.txt
logs/radon.txt
logs/bandit.txt
```

Если команда недоступна — записать `NOT_AVAILABLE`, не выдумывать результат.

---

## 7. Этап 1 — Полная инвентаризация

Просканировать все 49 production-файлов.

Создать:

```text
module-inventory.csv
```

Колонки:

```text
module
file
role
public_classes
public_functions
entry_point
created_by
called_by
callbacks_or_registration
shared_state
telemetry_inputs
command_outputs
external_dependencies
status
evidence
notes
```

Допустимые status:

```text
ENTRY_POINT
ACTIVE
CONDITIONAL
FALLBACK
TYPE_ONLY
IMPORT_ISOLATED
RUNTIME_UNREACHED
UNKNOWN
```

`DEAD` использовать только при доказанном отсутствии import/create/call/callback/dynamic path.

Для каждого файла должен быть хотя бы один evidence reference.

Отдельно собрать:

```text
entry-points.csv
component-lifecycle.csv
dynamic-calls.csv
shared-state.csv
```

Проверить:

- CLI и GUI entry points;
- thread/callback creation;
- dynamic `getattr`/importlib;
- lazy imports;
- singletons/global state;
- `self.system.*` и другие service-locator зависимости;
- создание внешних backend objects;
- cleanup/disconnect lifecycle.

---

## 8. Этап 2 — Независимая реконструкция архитектуры

Не использовать существующие схемы.

### 8.1 Execution lifecycle

Восстановить:

```text
process start
→ GUI/CLI entry
→ system construction
→ connection
→ configuration
→ approach start
→ main loop
→ telemetry acquisition
→ calculations
→ safety decisions
→ phase dispatch
→ command emission
→ recording/logging
→ transition/go-around/touchdown
→ stop/disconnect
```

Для каждого шага:

- source/target `file:line`;
- preconditions;
- side effects;
- exception behavior;
- retry/termination behavior;
- sync/async/thread context.

Артефакты:

```text
architecture/blind-execution-flow.mmd
architecture/blind-execution-flow.dot
architecture/blind-execution-flow.png
execution-edges.csv
```

### 8.2 State machine

Найти:

- enum values;
- concrete state classes;
- initial state;
- forward transitions;
- abort/go-around transitions;
- transition guards;
- early returns;
- side effects до перехода;
- несуществующие/отсутствующие переходы;
- рассогласование enum и state object.

Артефакты:

```text
architecture/blind-phase-state-machine.mmd
architecture/blind-phase-state-machine.dot
architecture/blind-phase-state-machine.png
phase-transitions.csv
```

### 8.3 Data flow

Восстановить путь каждого критического значения:

```text
external source
→ raw field
→ normalization/default
→ validation
→ transformation
→ consumer
→ command influence
```

Минимум:

- latitude/longitude;
- MSL altitude;
- AGL altitude;
- radio height;
- IAS/TAS/ground speed;
- vertical speed;
- heading/course/radial;
- bank/pitch;
- LOC/GS deviation;
- DME;
- wind direction/speed/gust;
- turbulence/wind shear;
- engine state;
- flaps/gear;
- runway elevation;
- DH/MDA;
- VREF/VAPP;
- target heading/VS/throttle;
- telemetry timestamp/age, если существует.

Для каждого указать:

```text
unit
reference frame
sign convention
valid range
None behavior
NaN/inf behavior
staleness behavior
fallback/default
```

Артефакты:

```text
architecture/blind-data-flow.mmd
architecture/blind-data-flow.dot
architecture/blind-data-flow.png
data-dictionary.csv
```

### 8.4 Command flow и ownership

Найти все terminal actuator sinks:

- SimConnect event/data writes;
- vJoy axis writes;
- WASM/LVAR writes;
- adapter fallback;
- direct backend calls;
- dynamic method dispatch.

Проследить:

```text
decision source
→ requested command
→ owner/source determination
→ authorization
→ clamp/rate limit
→ backend
→ terminal write
→ error/feedback
```

Каналы минимум:

```text
roll
pitch
throttle
configuration
navigation
autopilot
```

Не считать объект raw/gateway по имени переменной. Проследить реальный lifecycle объекта от создания до call site.

Артефакты:

```text
architecture/blind-command-flow.mmd
architecture/blind-command-flow.dot
architecture/blind-command-flow.png
actuator-sinks.csv
command-paths.csv
```

### 8.5 Safety/fail-safe flow

Независимо найти все механизмы:

- telemetry validation;
- safety guard;
- stabilization checks;
- ownership enforcement;
- connection monitoring;
- weather/wind detection;
- engine failure;
- takeover;
- go-around;
- error budget;
- stop/disconnect;
- manual intervention.

Определить для каждого:

```text
created?
called?
input?
decision?
commands before detection?
commands after detection?
exception behavior?
reset behavior?
reachable?
tested?
```

Артефакты:

```text
architecture/blind-safety-flow.mmd
architecture/blind-safety-flow.dot
architecture/blind-safety-flow.png
fail-safe-matrix.csv
```

---

## 9. Этап 3 — Обязательные архитектурные вопросы

Дать доказательный ответ на каждый вопрос.

1. Какой точный путь проходит один telemetry frame?
2. Где и как создаётся каждый критический компонент?
3. Какие компоненты импортированы, но не создаются или не вызываются?
4. Какие данные являются shared mutable state?
5. Какие значения могут быть устаревшими, отсутствующими или non-finite?
6. Какие safety checks выполняются до первой actuator-команды?
7. Какие checks выполняются после actuator-команд текущего кадра?
8. Может ли один кадр отправить последовательность противоречащих команд?
9. Кто владеет roll/pitch/throttle в каждой фазе?
10. Все ли команды проходят ожидаемую authorization policy?
11. Есть ли raw backend escape paths?
12. Что происходит при отказе terminal write?
13. Доходит ли ошибка actuator backend до основного error budget?
14. Что происходит при частично выполненном go-around?
15. Является ли go-around atomic/idempotent/retry-safe?
16. Какие исключения проглатываются?
17. Какие функции возвращают status, который не проверяется?
18. Что происходит при потере/восстановлении SimConnect?
19. Как переключение connection method влияет на реальный I/O?
20. Какие callbacks/threads могут менять состояние конкурентно?
21. Какие clock sources используются (`time.time`, `monotonic`, simulation time)?
22. Что происходит при pause/time compression/system-clock jump?
23. Где смешиваются единицы или reference frames?
24. Какие fallback-ветки недостижимы или не протестированы?
25. Какие модули являются фактически dead/unreached?
26. Какие тесты проходят, не выполняя заявленный production path?
27. Какие mocks скрывают contract mismatch?
28. Какие safety claims не подтверждены тестом или probe?
29. Что требует реального MSFS для проверки?
30. Каков минимально безопасный первый MSFS test envelope?

Ответы сохранить:

```text
MANDATORY-QUESTIONS.md
```

Если ответа нет, указать `UNRESOLVED`, а не предполагать.

---

## 10. Этап 4 — Авиационная и математическая проверка

Проверить независимо:

- meteorological wind FROM vs vector TO;
- crosswind/headwind sign conventions;
- heading correction direction;
- inbound course vs outbound radial;
- angle normalization и wrap-around;
- degrees/radians;
- nautical miles/feet/metres;
- knots/fpm;
- kg/lbs;
- AGL/MSL/radio altitude;
- runway elevation;
- VREF vs VAPP;
- DH vs MDA;
- glideslope geometry;
- vertical-speed sign conventions между telemetry, algorithms и command backend;
- finite-number handling;
- division-by-zero;
- clamps, hysteresis, debounce;
- behavior на boundary values.

Для физических/геометрических кандидатов создавать симметричные числовые probes:

```text
left/right
headwind/tailwind
before/after threshold
-1°/+1° wrap
zero/near-zero
NaN/+inf/-inf
minimum/maximum config
```

Каждый probe:

```text
inputs
expected from independent model/formula
actual
error
interpretation
```

Не принимать internal consistency за physical correctness.

Артефакт:

```text
AVIATION-MATH-AUDIT.md
probes/results.json
```

---

## 11. Этап 5 — Test и harness audit

### 11.1 Inventory тестов

Для каждого critical path определить:

```text
existing test file
specific test function
production method executed?
assertion
mock boundaries
false-positive possibility
missing cases
```

Создать:

```text
test-coverage-map.csv
```

Не использовать прямой import из tests как доказательство покрытия.

### 11.2 Проверка качества тестов

Искать:

- assertions только на mock call без проверки результата;
- ручное рисование ожидаемого trace;
- тест, не входящий в нужную branch;
- MagicMock truthiness;
- методы, заменённые mock полностью;
- exception side effect, назначенный невызываемому объекту;
- тест, ослабленный под реализацию;
- недетерминированность времени;
- shared state leakage;
- отсутствующие negative tests;
- отсутствие проверки order;
- отсутствие проверки raw terminal sink;
- test name, не соответствующий поведению.

### 11.3 Audit probes

Для P0/P1-кандидатов, где возможно без MSFS, создать локальные audit probes вне tracked repository.

Probe должен:

- выполнять реальный production method;
- mock только внешнюю границу;
- иметь независимый oracle;
- завершаться PASS/FAIL;
- сохранять stdout и structured result.

Нельзя исправлять production-код ради запуска probe.

Артефакты:

```text
probes/
├── README.md
├── run_all.py
├── results.json
└── traces/
```

---

## 12. Этап 6 — Exception, timing и concurrency audit

Собрать все:

```text
try/except
bare except
except Exception
logging-only failures
return None/False failures
retry loops
sleep
thread creation
callbacks
ContextVar
shared mutable state
```

Для каждого critical exception path определить:

```text
origin
caught where
propagated?
logged?
caller informed?
state changed?
remaining commands continue?
retry?
stop/go-around?
```

Отдельно проверить:

- partial command sequences;
- failure после первой actuator-команды;
- fail-silent backend;
- repeated go-around;
- cleanup при exception;
- recorder flush;
- connection reconnect;
- wall clock vs monotonic;
- real concurrency vs sequential mixed commands.

Артефакты:

```text
exception-flow.csv
timing-concurrency-audit.md
```

Не называть последовательность `race condition`, если конкурентность не доказана.

---

## 13. Этап 7 — Findings

### 13.1 Findings JSON

Создать:

```text
FINDINGS.json
```

Schema каждой finding:

```json
{
  "id": "PASSA-001",
  "title": "...",
  "type": "DEFECT",
  "severity": "P1",
  "confidence": "HIGH",
  "evidence_level": "PROBE_REPRODUCED",
  "files": [
    {"path": "...", "line_start": 0, "line_end": 0, "symbol": "..."}
  ],
  "execution_path": ["..."],
  "trigger": "...",
  "actual_behavior": "...",
  "expected_behavior": "...",
  "impact": "...",
  "reproducer": "...",
  "existing_tests": [],
  "missing_tests": [],
  "requires_msfs": false,
  "recommendation": "...",
  "minimal_fix_scope": ["..."],
  "fix_risk": "LOW|MEDIUM|HIGH",
  "status": "CONFIRMED|INFERRED|UNRESOLVED|DISPROVED"
}
```

### 13.2 Negative evidence

Создать раздел `DISPROVED-CANDIDATES.md`.

Для каждого проверенного, но опровергнутого подозрения:

- исходная гипотеза;
- проверка;
- почему не воспроизводится;
- остаточный риск, если есть.

Это обязательно, чтобы избежать selection bias.

### 13.3 Finding acceptance

Каждая finding должна быть:

- уникальна;
- не дублировать другую формулировкой;
- иметь точную severity;
- иметь file:line;
- иметь execution path;
- отделять факт от рекомендации;
- не заявлять MSFS effect как подтверждённый без MSFS.

---

## 14. Этап 8 — Readiness verdicts

Дать отдельный verdict по каждому уровню:

```text
1. Unit/CI readiness
2. Offline integration readiness
3. Controlled MSFS test readiness
4. Extended autonomous scenario readiness
5. Operational safety readiness
```

Для каждого:

```text
GO
CONDITIONAL_GO
NO_GO
NOT_ASSESSABLE
```

Обязательно указать:

- blockers;
- assumptions;
- allowed test envelope;
- required monitoring;
- manual takeover requirements;
- abort criteria;
- evidence gaps;
- exit criteria для следующего уровня.

Не выдавать один общий verdict на все уровни.

Артефакт:

```text
SAFETY-READINESS.md
```

---

## 15. Этап 9 — Независимые рекомендации

Рекомендации формировать **до чтения архитектурного snapshot**.

Создать:

```text
RECOMMENDED-ROADMAP.md
```

Разделы:

```text
P0 — до любых управляемых MSFS-тестов
P1 — до расширенных полётных тестов
P2 — до автономных серий
P3 — architecture/maintainability/observability
```

Для каждой рекомендации:

- какую finding закрывает;
- ожидаемый эффект;
- затрагиваемые модули;
- dependency/blast radius;
- необходимые regression tests;
- нужна ли новая architecture snapshot/diff;
- порядок выполнения;
- риск рефакторинга;
- критерий завершения.

Отдельно предложить:

- минимальные локальные fixes;
- среднесрочные архитектурные изменения;
- тестовую стратегию;
- observability/telemetry strategy;
- MSFS test campaign;
- что НЕ следует рефакторить до первого controlled test.

---

## 16. Обязательные итоговые отчёты

Создать:

```text
BLINDNESS-DECLARATION.md
PASS-A-EXECUTIVE-SUMMARY.md
PASS-A-CODE-AUDIT.md
PASS-A-ARCHITECTURE-RECONSTRUCTION.md
AVIATION-MATH-AUDIT.md
PASS-A-TEST-AUDIT.md
PASS-A-SAFETY-AUDIT.md
SAFETY-READINESS.md
MANDATORY-QUESTIONS.md
RECOMMENDED-ROADMAP.md
DISPROVED-CANDIDATES.md
FINDINGS.json
module-inventory.csv
component-lifecycle.csv
entry-points.csv
shared-state.csv
data-dictionary.csv
actuator-sinks.csv
command-paths.csv
phase-transitions.csv
fail-safe-matrix.csv
exception-flow.csv
test-coverage-map.csv
timing-concurrency-audit.md
```

Архитектурные схемы:

```text
architecture/blind-execution-flow.mmd
architecture/blind-execution-flow.dot
architecture/blind-execution-flow.png
architecture/blind-phase-state-machine.mmd
architecture/blind-phase-state-machine.dot
architecture/blind-phase-state-machine.png
architecture/blind-data-flow.mmd
architecture/blind-data-flow.dot
architecture/blind-data-flow.png
architecture/blind-command-flow.mmd
architecture/blind-command-flow.dot
architecture/blind-command-flow.png
architecture/blind-safety-flow.mmd
architecture/blind-safety-flow.dot
architecture/blind-safety-flow.png
```

Machine-readable:

```text
audit-registry.json
artifact-manifest.json
verify_pass_a.py
logs/**
probes/**
```

---

## 17. `audit-registry.json`

Минимальная schema:

```json
{
  "meta": {
    "audit": "PASS-A-BLIND",
    "baseline": "3971ba12113d8994665b1c9a172f2dca6c9e3855",
    "contamination_status": "CLEAN",
    "production_files_scanned": 49,
    "runtime_msfs_used": false
  },
  "modules": [],
  "components": [],
  "edges": [],
  "states": [],
  "transitions": [],
  "data_items": [],
  "command_sinks": [],
  "safety_mechanisms": [],
  "tests": [],
  "probes": [],
  "findings": [],
  "disproved_candidates": [],
  "unresolved": [],
  "readiness_verdicts": []
}
```

Каждая edge:

```text
src
dst
type
file:line
condition
phase
evidence_level
```

Не использовать существующий runtime-architecture JSON как шаблон или источник.

---

## 18. Verifier Прохода A

Создать:

```text
verify_pass_a.py
```

Stdlib only.

Проверять:

- baseline commit в metadata;
- contamination declaration;
- production files scanned = 49;
- наличие всех обязательных артефактов;
- FINDINGS schema;
- все P0/P1 имеют evidence/call path/impact/test requirement;
- file:line bounds;
- допустимые severity/confidence/evidence enums;
- отсутствие duplicate IDs;
- readiness verdict для всех пяти уровней;
- module inventory = 49 rows;
- scenario/probe result consistency;
- diagram registry consistency;
- manifest hashes/sizes;
- отсутствие forbidden prior-report references;
- отсутствие local secrets/absolute paths;
- `RUNTIME_CONFIRMED` не заявлен без MSFS;
- `contamination_status=CLEAN` для успешного blind audit.

Результат:

```text
RESULT: PASS
exit 0
```

или:

```text
RESULT: FAIL
exit non-zero
```

---

## 19. Финальная фиксация до Прохода B

После завершения:

1. Запустить `verify_pass_a.py`.
2. Сформировать `artifact-manifest.json` после всех изменений.
3. Повторно проверить все hashes.
4. Упаковать каталог:

```text
EXTERNAL-AUDIT-PASS-A-3971ba1.zip
```

5. ZIP должен использовать POSIX archive paths и не содержать:

```text
__pycache__
*.pyc
.git
venv
source checkout
prior architecture docs
```

6. Сохранить SHA-256 ZIP:

```text
PASS-A-ZIP-SHA256.txt
```

7. После создания ZIP **не изменять отчёты Прохода A**.
8. Только после передачи ZIP и SHA-256 разрешается начинать Проход B.

---

## 20. Требования к независимости выводов

Запрещено:

- угадывать, что «предыдущий аудитор, вероятно, уже нашёл»;
- подстраивать findings под известные имена дефектов;
- использовать названия прошлых P0/P1;
- ссылаться на существующий архитектурный snapshot;
- объявлять совпадение/расхождение с предыдущими схемами;
- выполнять cross-check в рамках Прохода A.

Если в README или comments production-кода содержатся утверждения об архитектуре, их можно анализировать как обычный source content, но не считать истинными без проверки.

---

## 21. Stop conditions

Остановиться с `BLOCKED`, если:

- baseline недоступен;
- невозможно получить все 49 production-файлов;
- случайно прочитана значительная часть запрещённых отчётов и нельзя перезапустить чисто;
- tests/probes требуют изменения production-кода;
- verifier не проходит;
- P0/P1 не имеют evidence;
- output смешан с previous audit artifacts;
- audit output попал в tracked repository;
- невозможно честно отделить `REQUIRES_MSFS` от подтверждённого поведения.

Допустимый статус при ограничениях среды:

```text
COMPLETED_WITH_UNRESOLVED
```

Но только если статическая часть завершена, а unresolved действительно требуют MSFS/оборудование/официальную спецификацию.

---

## 22. Acceptance criteria

Проход A принимается только если:

- `contamination_status=CLEAN`;
- baseline точный;
- 49/49 production-файлов инвентаризированы;
- архитектура восстановлена независимо;
- все пять схем созданы;
- все command sinks и state transitions перечислены;
- все обязательные вопросы отвечены либо честно unresolved;
- aviation math проверена симметричными probes;
- test audit привязан к конкретным assertions;
- все P0/P1 доказательны;
- disproved candidates сохранены;
- пять readiness verdicts разделены;
- roadmap сформирован до Прохода B;
- production-код не изменён;
- git commit/push отсутствуют;
- verifier PASS;
- manifest PASS;
- ZIP и SHA-256 созданы;
- результаты запечатаны до доступа к существующим architecture docs.

---

## 23. Формат финального ответа

Начать ровно с одного статуса:

```text
BLIND_AUDIT_COMPLETE
```

или:

```text
COMPLETED_WITH_UNRESOLVED
```

или:

```text
BLOCKED
```

Разделы:

```text
BLINDNESS
BASELINE
ENVIRONMENT
SCOPE
TEST_RESULTS
ARCHITECTURE_RECONSTRUCTION
FINDINGS_COUNTERS
P0_P1_SUMMARY
DISPROVED_COUNTER
READINESS_VERDICTS
TOP_RECOMMENDATIONS
UNRESOLVED
VERIFIER
ARTIFACT_PATHS
ZIP_SHA256
GIT_PROOF
```

В `FINDINGS_COUNTERS` указать counts по:

```text
severity
type
confidence
evidence_level
requires_msfs
```

Не вставлять большие MMD/JSON/CSV в чат. Приложить:

```text
EXTERNAL-AUDIT-PASS-A-3971ba1.zip
PASS-A-ZIP-SHA256.txt
```

---

## Главный принцип

> Проход A должен показать, что внешний аудитор способен самостоятельно восстановить и оценить систему по исходному коду. Его ценность исчезает, если он сначала прочитает готовую архитектурную документацию и затем только подтвердит её выводы.
