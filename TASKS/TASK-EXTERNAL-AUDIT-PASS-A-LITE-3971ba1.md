# TASK: EXTERNAL AUDIT — PASS A-LITE (BLIND, NO SHELL)

## 0. Цель

Провести **независимый слепой статический аудит** production-кода проекта `msfs_autoland` в среде без shell, Git checkout, Python/pytest/probes, Graphviz и создания ZIP.

PASS A-LITE не является заменой полного исполняемого аудита. Его задача — независимо реконструировать архитектуру по исходникам, выявить статически доказуемые дефекты и риски, а все гипотезы, требующие исполнения, превратить в точные заявки локальному верификатору.

Сравнение с ранее созданными схемами и отчётами запрещено: оно будет выполнено отдельно в Проходе B.

---

## 1. Репозиторий и фиксированный baseline

**Исследовать только этот репозиторий:**

```text
https://github.com/zhuk-mou-1/msfs_autoland
```

**Baseline commit:**

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

Запрещено использовать старый репозиторий `mergelord/msfs_autoland`, forks, текущий `master` или другой commit.

Читать файлы по URL, привязанным к SHA, например:

```text
https://raw.githubusercontent.com/zhuk-mou-1/msfs_autoland/3971ba12113d8994665b1c9a172f2dca6c9e3855/main.py
```

Для инвентаризации разрешено использовать GitHub tree/API именно этого commit:

```text
https://api.github.com/repos/zhuk-mou-1/msfs_autoland/git/trees/3971ba12113d8994665b1c9a172f2dca6c9e3855?recursive=1
```

Ожидаемый production scope:

```text
main.py
+ gui.py
+ modules/**/*.py (47 файлов)
= 49 production-файлов
```

Самостоятельно построить фактический список. Если число отличается, зафиксировать расхождение, не подгонять результат.

Если указанный commit или ключевые файлы недоступны, завершить со статусом `BLOCKED_BASELINE_UNAVAILABLE`.

---

## 2. Blind-изоляция

До сдачи PASS A-LITE запрещено читать, искать или использовать:

```text
docs/architecture/**
ветку docs/runtime-architecture-3971ba1
research/depgraph/**
research/runtime_architecture/**
TASKS/**
RUNTIME-ARCHITECTURE-*.md
DEPGRAPH-*.md
AUDIT-*.md
FINDINGS.json
PR/Issues/Discussions с результатами прежних аудитов
отчёты и выводы других моделей
предыдущую переписку об архитектуре проекта
```

Не искать в интернете сочетания названия проекта со словами `audit`, `architecture`, `findings`, `depgraph`.

**Полный запрет поиска (критично):**

- ЗАПРЕЩЕНО использовать любой workspace search (Notion, подключённые источники, unified search) по любым терминам, связанным с проектом: имя репозитория, имя задачи, SHA, названия модулей.
- ЗАПРЕЩЕНО искать текст этой задачи по названию: задача передаётся только как приложенный файл в первом сообщении. Если файл не приложен — запросить его у пользователя, а не искать.
- ЗАПРЕЩЕНО использовать GitHub search (code/issues/PR search). Единственные разрешённые обращения к GitHub — прямые SHA-pinned REST/raw endpoints из раздела 1.
- Любой выполненный поиск по проекту до или во время аудита = потенциальная contamination и должен быть задекларирован в BLINDNESS-DECLARATION.
- Запускать PASS A-LITE только в новом чистом треде, где нет предыдущей истории об этом проекте.

Разрешено читать на baseline:

```text
main.py
gui.py
modules/**/*.py
tests/**/*.py и test_*.py
config/**
requirements*.txt
pyproject.toml
.github/workflows/**
README.md
.gitignore
```

Разрешена официальная документация Python, SimConnect/MSFS SDK, vJoy и авиационные стандарты при явном цитировании.

В отчёте обязательна декларация:

```text
BLINDNESS-DECLARATION
contamination_status: CLEAN | PARTIALLY_CONTAMINATED | CONTAMINATED
sources_used:
  - ...
forbidden_material_seen:
  - NONE | точный перечень
```

Случайную contamination не скрывать. При существенной contamination, влияющей на независимость выводов, остановиться.

---

## 3. Ограничения среды и правила доказательности

В PASS A-LITE не требуется:

- clone/checkout, проверка локальных `HEAD` и `git status`;
- запуск Python, pytest, линтеров, probes или verifier;
- Graphviz/PNG;
- создание файлов, ZIP и SHA-256.

Компенсирующие правила:

1. Максимальный уровень доказательности — `STATIC_CONFIRMED`.
2. Нельзя заявлять, что тест или probe «прошёл».
3. Каждая P0/P1 finding и каждый критический архитектурный вывод должны содержать точную цитату кода и прослеженный call path.
4. Не выдумывать номера строк. Если точный номер недоступен, указывать функцию/класс и точную цитату с `approx_location`.
5. Если веб-инструмент вернул усечённый файл, догрузить остальные диапазоны. Непрочитанные диапазоны перечислить.
6. Не домысливать содержимое непрочитанных файлов.
7. Всё, что зависит от исполнения, помечать `REQUIRES_LOCAL_EXECUTION` или `REQUIRES_MSFS`.
8. Deliverables выдавать прямо в ответе как Markdown, JSON, CSV и Mermaid. Допускается серия сообщений.

### Evidence levels

```text
STATIC_CONFIRMED          однозначно следует из прочитанного исходника и полного call path
INFERRED                  правдоподобно, но путь или эффект прослежен не полностью
REQUIRES_LOCAL_EXECUTION  требует локального запуска без MSFS
REQUIRES_MSFS             требует симулятора/оборудования
DISPROVED                 кандидат статически опровергнут
UNRESOLVED                доказательств недостаточно; причина указана
```

### Severity и confidence

```text
Severity:   P0 | P1 | P2 | P3 | INFO
Confidence: HIGH | MEDIUM | LOW
```

P0/P1 без полного call path и дословной цитаты запрещены. Такой кандидат понизить до P2/QUESTION и запросить локальную проверку.

---

## 4. Порядок работы

Режим audit-only: production-код, ветки и репозиторий не менять.

Рекомендуемый порядок чтения:

1. `main.py` полностью.
2. Оркестрация фаз и состояний.
3. Command gateway, ownership и terminal control.
4. Telemetry, connection monitoring и safety.
5. Navigation, guidance, wind correction и takeover.
6. Остальные production-модули.
7. Тесты и CI.
8. `gui.py`: минимум entry points, actuator/go-around/takeover paths, callbacks, threading и exception handling. Если файл не прочитан полностью — указать точные диапазоны.

Не переносить предположения из имён классов/переменных. Например, наличие имени `gateway` не доказывает, что runtime-объект действительно является gateway: проследить создание и присваивания.

---

## 5. Этап A — Инвентаризация 49/49

Выдать `MODULE-INVENTORY`:

```text
module | role | key_classes/functions | entry_point | created_by | called_by | shared_state | telemetry_in | commands_out | status | evidence | read_coverage
```

`read_coverage`:

```text
FULL
PARTIAL(<прочитанные/непрочитанные диапазоны>)
NOT_READ
```

Допустимые `status`:

```text
ENTRY_POINT | ACTIVE | CONDITIONAL | FALLBACK | TYPE_ONLY |
IMPORT_ISOLATED | RUNTIME_UNREACHED | UNKNOWN
```

`DEAD` использовать только при доказанном отсутствии всех runtime-путей.

Отдельно ��еречислить:

- entry points;
- runtime, lazy, conditional и `TYPE_CHECKING` imports;
- dynamic dispatch/factories;
- global/singleton/shared mutable state;
- зависимости через `self.system.*`;
- threads, callbacks, timers и context-local state.

---

## 6. Этап B — Независимая реконструкция архитектуры

Построить без чужих схем пять Mermaid-диаграмм и таблицы рёбер с `file + location + code_quote`.

### B1. Execution lifecycle

От запуска процесса до завершения/посадки/остановки: создание компонентов, connect/reconnect, главный цикл, получение telemetry, расчёты, phase handling, safety, команды, запись/логирование, sleep, исключения и stop paths.

### B2. Phase state machine

Все состояния, forward/abort transitions, guards, ранние возвраты, side effects, переходы по ошибкам и отсутствующие переходы.

### B3. Critical data flow

Проследить источники, преобразования, единицы, знаки, default values и sinks для:

```text
latitude/longitude
MSL/AGL/radio altitude/runway elevation
IAS/TAS/GS/vertical speed
heading/track/course/bearing
LOC/GS deviations and validity
DME/distance
wind direction/speed/components/correction
runway/course/glideslope configuration
DH/MDA
VREF/VAPP
timestamps/age/staleness
```

### B4. Command flow и ownership

Найти все terminal actuator sinks (SimConnect/vJoy/WASM и аналоги). Для каждого проследить путь от решения до terminal write, runtime-тип control object, authorization/ownership, source scope, clamps, exception handling и escape paths.

### B5. Safety/fail-safe flow

Все safety mechanisms, порядок относительно команд текущего кадра, reset/latch behavior, исключения, достижимость, go-around/takeover/stop и частично выполненные последовательности.

---

## 7. Этап C — 30 обязательных вопросов

На каждый вопрос дать ответ с evidence level и цитатой либо `UNRESOLVED` с причиной.

1. Как один telemetry frame проходит от источника до actuator commands?
2. Где и когда создаётся каждый критический компонент?
3. Какие импортированные production-компоненты не вызываются в runtime?
4. Какое shared mutable state существует и кто его изменяет?
5. Где проверяются `None`, `NaN`, infinity и отсутствующие поля?
6. Где проверяется возраст/staleness telemetry и что происходит при stale frame?
7. Какие safety-проверки выполняются до команд кадра, а какие после?
8. Могут ли разные компоненты выдать противоречащие команды в одном кадре?
9. Кто владеет управлением в каждой фазе?
10. Как terminal write авторизуется и существуют ли обходные пути?
11. Что происходит при отказе одного terminal actuator write?
12. Узнаёт ли caller об отказе terminal write?
13. Доходит ли такой отказ до error budget/stop/go-around logic?
14. Может ли go-around выполниться частично и продолжить полёт с mixed state?
15. Является ли go-around атомарным или компенсируемым?
16. Какие исключения проглатываются после logging-only handling?
17. Какие safety/status claims нельзя подтвердить наблюдаемым состоянием?
18. Что происходит при потере и восстановлении SimConnect/источника telemetry?
19. Возможна ли смена connection/control backend в runtime и как она синхронизируется?
20. Какие threads/callbacks/timers конкурируют за состояние или commands?
21. Какие clock sources используются; возможны ли wall-clock jumps?
22. Как pause, sim-rate/time compression или задержки цикла влияют на логику?
23. Где смешиваются единицы, системы координат или соглашения о знаке?
24. Какие fallback paths недостижимы или не активируются?
25. Какой код доказуемо dead/unreached, а какой лишь редко достижим?
26. Какие тесты не исполняют заявленный production path?
27. Какие mocks способны скрыть contract mismatch или false-positive PASS?
28. Какие safety claims требуют локального исполнения для подтверждения?
29. Что принципиально требует реального MSFS/оборудования?
30. Каков минимальный безопасный первый test envelope и его exit criteria?

---

## 8. Этап D — Авиационная и математическая проверка

Статически проверить:

- wind FROM/TO;
- знаки crosswind/headwind и heading correction;
- inbound/outbound radial;
- нормализацию углов и wrap-around 0/360;
- градусы/радианы;
- NM/ft/m, kt/fpm, kg/lbs;
- AGL/MSL/radio altitude/runway elevation;
- VREF/VAPP, DH/MDA;
- геометрию глиссады;
- знак vertical speed от telemetry через guidance до commands;
- finite checks, деление на ноль, clamps, hysteresis и границы.

Вместо executable probes выполнить ручные символьные трассировки для подозрительных формул:

1. левый и правый ветер одинаковой силы;
2. углы по обе стороны 0/360;
3. zero input/zero divisor;
4. минимальные и экстремальные допустимые значения;
5. положительный и отрицательный vertical deviation/VS.

Показать исходные значения, вычисления по шагам и независимую контрольную формулу. Каждую трассировку, требующую подтверждения, добавить в `LOCAL-VERIFICATION-REQUESTS`.

---

## 9. Этап E — Статический аудит тестов

Составить `TEST-COVERAGE-MAP`:

```text
critical_path | test_file/test | production_method_reached? | mocked_boundary | assertions | false_positive_risk | missing_cases | evidence
```

Искать особенно:

- assertions только на mock calls;
- production-метод, полностью заменённый mock;
- `MagicMock` truthiness;
- `side_effect`, назначенный не тому объекту;
- synthetic/manual traces вместо production path;
- тесты, подогнанные под текущую реализацию;
- отсутствие negative/failure tests;
- tests, заявляющие gateway/safety path без реальног�� runtime object lifecycle.

Не заявлять результаты запуска тестов.

---

## 10. Этап F — Exceptions, timing и concurrency

Собрать критические:

```text
try/except
logging-only handlers
retry/reconnect
sleep/timeouts
threads/callbacks/timers
ContextVar/thread-local state
shared mutable state
```

Для каждого exception path указать: origin → catch → observable result → узнаёт ли caller → продолжаются ли остальные команды кадра.

Не использовать термин `race condition`, если конкурентность не доказана. Последовательные conflicting commands описывать как `sequential conflicting/mixed commands`.

---

## 11. Findings

Выдать `FINDINGS` как валидный JSON-массив. Схема записи:

```json
{
  "id": "LITE-001",
  "title": "...",
  "type": "DEFECT|ARCHITECTURE_RISK|SAFETY_RISK|TEST_GAP|OBSERVABILITY_GAP|MAINTAINABILITY_DEBT|DEAD_OR_UNREACHED_CODE|QUESTION",
  "severity": "P0|P1|P2|P3|INFO",
  "confidence": "HIGH|MEDIUM|LOW",
  "evidence_level": "STATIC_CONFIRMED|INFERRED|REQUIRES_LOCAL_EXECUTION|REQUIRES_MSFS|UNRESOLVED",
  "file": "...",
  "location": "line N | approx: class/function/context",
  "code_quote": "дословная цитата 1–5 строк",
  "execution_path": ["..."],
  "trigger": "...",
  "actual_behavior": "...",
  "expected_behavior": "...",
  "impact": "...",
  "missing_tests": ["..."],
  "recommendation": "...",
  "fix_risk": "LOW|MEDIUM|HIGH",
  "local_verification_request": "точная проверка | null"
}
```

Выдать counters по severity/type/evidence.

Отдельно `DISPROVED-CANDIDATES`: проверенные и опровергнутые подозрения с цитатами и объяснением, почему они неверны. Это обязательная защита от selection bias.

---

## 12. Readiness и roadmap

Пять отдельных вердиктов:

```text
Unit/CI readiness
Offline integration readiness
Controlled MSFS test readiness
Autonomous scenario readiness
Operational safety readiness
```

Для каждого:

```text
GO | CONDITIONAL_GO | NO_GO | NOT_ASSESSABLE
blockers
evidence
exit criteria
```

Статический PASS A-LITE сам по себе не может дать безусловный operational `GO`.

Затем выдать независимый `RECOMMENDED-ROADMAP` P0–P3, сформированный до чтения любой прежней архитектурной документации.

---

## 13. LOCAL-VERIFICATION-REQUESTS

Сформировать точный список для отдельного локального исполнителя:

```text
id | цель | prerequisites | точная команда или probe-spec | ожидаемый результат если гипотеза верна | counter-result | связанные findings | requires_msfs
```

Включить:

- все P0/P1-кандидаты;
- все findings с `REQUIRES_LOCAL_EXECUTION`;
- math/aviation probes;
- тесты failure paths actuator writes;
- telemetry stale/None/NaN cases;
- gateway ownership/bypass paths;
- partial go-around/exception injection;
- verifier/test/coverage commands, которые невозможно выполнить в текущей среде.

Не писать расплывчатое «запустить тесты». Команда/probe должна быть воспроизводимой локальным агентом.

---

## 14. Формат сдачи

Итоговый статус — ровно один:

```text
BLIND_LITE_AUDIT_COMPLETE
COMPLETED_WITH_UNRESOLVED
BLOCKED
```

Разделы в порядке:

```text
1. STATUS
2. BLINDNESS-DECLARATION
3. BASELINE-VERIFICATION-METHOD
4. READ-COVERAGE-SUMMARY (FULL/PARTIAL/NOT_READ и непрочитанные диапазоны)
5. MODULE-INVENTORY (ожидается 49 строк)
6. ARCHITECTURE-RECONSTRUCTION (5 Mermaid-схем + evidence tables)
7. MANDATORY-QUESTIONS (30)
8. AVIATION-MATH-AUDIT
9. TEST-COVERAGE-MAP
10. EXCEPTION-TIMING-CONCURRENCY-AUDIT
11. FINDINGS + counters
12. DISPROVED-CANDIDATES
13. READINESS-VERDICTS
14. RECOMMENDED-ROADMAP
15. LOCAL-VERIFICATION-REQUESTS
16. UNRESOLVED
17. LIMITATIONS-OF-PASS-A-LITE
```

Если ответ слишком велик, разрешена последовательность `PART 1/N ... PART N/N`. Не сокращать evidence, findings или read coverage ради помещения в одно сообщение.

---

## 15. Stop conditions

Завершить `BLOCKED`, если:

- baseline commit недоступен;
- невозможно прочитать целиком ключевые orchestration/control/telemetry/safety модули;
- невозможно установить фактический production scope;
- существенная contamination уничтожила независимость аудита.

`COMPLETED_WITH_UNRESOLVED` допустим, если статический аудит выполнен, а исполняемые пробелы честно обозначены.

Запрещено выдавать PASS A-LITE за полный blind audit, утверждать прохождение тестов/probes, придумывать hashes или скрывать неполное чтение.

---

## Главный принцип

> Ценность PASS A-LITE — независимый доказательный взгляд на исходный код, а не имитация отсутствующей исполняемой среды. Честно обозначенный пробел ценнее уверенного, но непроверенного вывода.
