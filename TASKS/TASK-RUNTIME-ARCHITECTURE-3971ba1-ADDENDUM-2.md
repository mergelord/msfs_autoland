# TASK: RUNTIME-ARCHITECTURE-3971ba1 — ADDENDUM 2

## Статус независимой проверки v2

```text
REQUEST_CHANGES — FALSE POSITIVE HARNESS + INVALID MANIFEST + WRONG GATEWAY LIFECYCLE
```

Production-код не менять. Исправлять только `research/runtime_architecture/`. Commit/push не делать.

Baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

---

## 1. `harness 10/10` не подтверждён

Независимая проверка `harness/results.json`, traces и `run_harness.py` показала ложноположительные PASS.

### 1.1 `nonsynthetic_glidepath`

Фактический результат:

```json
{"synth_calls": 0, "vs": 1}
```

Сценарий объявлен PASS, хотя заявленный `synthetic_glidepath.compute_target_vs()` не подтверждён. Код проверяет только наличие VS-команды.

### Требуется

- Assert `system.synthetic_glidepath.compute_target_vs.call_count == 1`.
- Записать вызов `compute_target_vs` в trace.
- Проверить аргументы и влияние возвращённого значения на `set_vertical_speed`.
- Исправить имя scenario ID на `non_ils_synthetic_glidepath`.

### 1.2 `actuator_exception`

Фактический result/trace:

```json
{"exception": null, "phase": null}
```

Все команды в trace имеют `result: OK`. Исключение не было внедрено. Причина: `create_mock_system()` заменяет `MagicMock` методом-wrapper, после чего присваивание `.side_effect` wrapper-функции не заставляет её бросать исключение.

### Требуется

- Реально внедрить исключение в вызываемый sink.
- Assert, что исключение действительно возникло либо было поглощено production-методом.
- Не ставить PASS при `trace.exception is null`, если сценарий ожидает exception.
- Проверить фактический контракт `MSFSControl`: его `set_*` методы ловят `Exception` и логируют без re-raise. Поэтому утверждение `actuator exception propagates to execute_approach error budget` предварительно неверно.
- Построить два отдельных сценария:
  1. `raw_ae_event_exception_swallowed_by_control`;
  2. `gateway_command_rejected_propagates`.
- Для каждого доказать реальное поведение production-кодом.

### 1.3 Синтетические сценарии вместо исполнения production path

Следующие сценарии вручную рисуют ожидаемый результат вместо выполнения соответствующего production-метода:

- `safety_guard_goaround`: вручную вызывает `system.execute_go_around()`;
- `loc_signal_loss`: вручную задаёт `approach_data=None` и вызывает go-around;
- `missing_telemetry`: вручную записывает семь trace entries, не выполняя `execute_approach()`;
- go-around tracker не вызывает настоящий `AutoLandSystem.execute_go_around()`, а только добавляет synthetic entry с индексом 999.

Это не `HARNESS_CONFIRMED` production execution.

### Требуется

Использовать реальные unbound methods на объекте `AutoLandSystem.__new__(AutoLandSystem)` с mock dependencies:

```python
AutoLandSystem._handle_phase(system, telemetry, approach_data)
AutoLandSystem._calculate_approach_data(system, telemetry)
AutoLandSystem.execute_approach(system)
AutoLandSystem.execute_go_around(system)
```

Допускается ограничивать loop детерминированными side effects, но production method должен реально выполняться.

Если сценарий остаётся ручной симуляцией, evidence level = `INFERRED` или `STATIC_CONFIRMED`, не `HARNESS_CONFIRMED`.

### 1.4 Trace неполон

- vJoy-сценарий утверждает `vjoy_calls=1`, но trace не содержит `virtual_joystick.apply_control_inputs`.
- takeover initiation trace не содержит `should_initiate_takeover` и `perform_takeover`.
- go-around traces не содержат реальную последовательность actuator-команд.
- `stabilized_monitor_goaround` заканчивается `phase_after=FINAL`, хотя synthetic flag go_around=true.

### Требуется

Каждый trace обязан содержать все ключевые вызовы, которыми обоснован PASS. Нельзя подтверждать результат отдельным MagicMock call_count, если он отсутствует в обязательном trace.

---

## 2. Harness не тестирует CommandGateway

`create_mock_system()` устанавливает:

```python
system.control = MagicMock()
```

Затем recorder безусловно подписывает каждый вызов как:

```text
GATEWAY_GUARDED
```

Но настоящий `CommandGateway._authorize()` не создаётся и не вызывается. Следовательно, текущие traces не подтверждают authorization, source scope или CommandRejected.

### Требуется

Для gateway-сценариев использовать:

```python
raw_control = FakeRawControl()
gateway = CommandGateway(raw_control, ownership_provider)
system.control = gateway
```

Проверить минимум:

1. AP source + AP owner → allowed;
2. AP source + EXTERNAL owner → `CommandRejected`;
3. EXTERNAL source + EXTERNAL owner → allowed;
4. SAFETY source → bypass;
5. default source behavior;
6. source reset после выхода из context manager.

Trace должен различать:

```text
command_request
authorize
command_allowed / command_rejected
terminal_write
```

---

## 3. Центральный вывод `RAW_CONTROL_BYPASS` неверен

Baseline `main.py` показывает:

```python
self.control = None                         # __init__
...
raw_control = MSFSControl(...)
self.control = CommandGateway(
    raw_control,
    self._current_control_ownership,
)                                           # connect()
```

`AircraftCommandAdapter` также получает `self.control`, то есть gateway proxy.

Следовательно, production-вызовы:

```python
self.system.control.set_*()
```

после успешного `connect()` идут через `CommandGateway.__getattr__()` и `_authorize()`. Они не являются raw bypass только потому, что синтаксически выглядят как `control.set_*`.

Отчёт v2 ошибочно утверждает:

```text
No wrapping/replacement of self.control detected
self.system.control IS raw MSFSControl
RAW_CONTROL_BYPASS
```

При этом `command-paths.csv` противоречит отчёту и правильно пишет `CommandGateway → MSFSControl`.

### Требуется

- Исправить lifecycle во всех артефактах.
- Удалить `RAW_CONTROL_BYPASS` для обычных phase-state путей.
- Переклассифицировать их как `GATEWAY_GUARDED`.
- Найти реальные raw-control escape paths только через доказанную ссылку на `raw_control`/`raw_control` property.
- Если таких production call sites нет, указать `RAW_CONTROL_BYPASS=0`.

---

## 4. Заново проверить SAFETY scope в `execute_go_around()`

Не переносить утверждение, что все go-around команды находятся внутри SAFETY scope, без byte-exact проверки отступов.

Нужно отдельно классифицировать каждую команду:

```text
set_autopilot_master
set_throttle / vjoy_throttle
set_vertical_speed
set_flaps
set_gear
center_all_axes
```

Для каждой указать:

- внутри или после `with source_scope(CommandSource.SAFETY)`;
- ожидаемый owner на момент вызова;
- actual `CommandSource`;
- allow/reject behavior;
- ловится ли `CommandRejected`;
- что произойдёт с оставшейся последовательностью.

Это потенциально более важная находка, чем ошибочный `RAW_CONTROL_BYPASS`.

---

## 5. Manifest недействителен

Независимая SHA-256 проверка ZIP:

```text
29 PASS
3 HASH/SIZE MISMATCH
```

Несовпадающие записи:

```text
harness\results.json
harness\run_harness.py
verify_runtime_architecture.py
```

Кроме того, manifest не включает:

- `RUNTIME-ARCHITECTURE-REPORT.md`;
- `command-flow.mmd`;
- `data-flow.mmd`;
- `safety-flow.mmd`;
- все 10 command traces;
- сам полный список обязательных артефактов.

### Требуется

- Пересоздавать manifest ПОСЛЕ всех изменений.
- Включить все файлы, кроме самого manifest либо использовать документированное self-hash правило.
- Проверять hash и size для КАЖДОЙ записи, не spot-check двух файлов.
- Verifier должен падать при лишнем unmanifested обязательном файле и при любом mismatch.

---

## 6. Упакованный verifier не даёт PASS

При запуске verifier непосредственно из предоставленного ZIP получено:

```text
RESULT: FAIL (13 errors)
exit code 1
```

Причины включают:

- harness paths не найдены;
- depgraph/source tree не найдены;
- file:line bounds не могут быть проверены;
- baseline dependency отсутствует.

ZIP содержит Windows backslashes в именах entries (`harness\results.json`) вместо переносимых каталогов `harness/results.json`. На Linux они распаковываются как имена файлов в корне.

### Требуется

- Создать ZIP со стандартными `/` directory separators.
- Добавить verifier CLI:

```text
--project-root
--artifact-root
--depgraph-path
```

- Либо включить минимальный immutable evidence bundle исходников/DEPGRAPH, необходимый для standalone verification.
- Приложить `verifier-stdout.txt` и реальный exit code.
- Verifier должен успешно запускаться после распаковки ZIP в отдельный каталог по документированной команде.

---

## 7. Verifier слишком поверхностный

Текущий verifier:

- проверяет только наличие scenario IDs и `passed == 10`;
- не валидирует scenario-specific assertions;
- проверяет наличие traces, но не их содержание;
- manifest hash проверяет только у двух файлов;
- `MMD/DOT edges in JSON` фактически проверяет лишь `len(edges)>0`;
- report content проверяет наличие слов;
- не проверяет полную JSON schema.

### Требуется

Добавить semantic validators:

- synthetic glidepath call count > 0;
- actuator exception scenario имеет ожидаемый observed outcome;
- vJoy trace содержит vJoy terminal call;
- takeover traces содержат takeover calls;
- go-around trace содержит реальный ordered sequence;
- gateway scenarios содержат authorization events;
- JSON/MMD/DOT edge-set comparison;
- all manifest hashes;
- exact report/JSON/CSV counters;
- schema validation каждого edge/sink/scenario.

---

## 8. `runtime-architecture.json` не соответствует обязательной schema

Независимая проверка:

```text
data_items = 0
scenarios key = ABSENT
actuator_sinks: 72 entries without evidence_level
edges: evidence_level polluted free-form strings
```

Примеры неверных `evidence_level`:

```text
STATIC_CONFIRMED main.py:896-897
No execute_go_around() call in InitialPhaseState
STATIC_CONFIRMED multiple sites
```

`evidence_level` должен быть enum, а ссылки/комментарии — в отдельных полях.

### Требуется

- Заполнить `data_items` из `data-dictionary.csv`.
- Добавить `scenarios` с 10 scenario records и evidence levels.
- Добавить `evidence_level` каждому actuator sink.
- Нормализовать edge `evidence_level` строго к разрешённым enum.
- Перенести file:line в `evidence_ref`/source fields.
- Не записывать отсутствие несуществующего перехода как edge.

---

## 9. State transition CSV всё ещё содержит старую ошибку

`phase-transitions.csv` содержит 9 строк, включая:

```text
INITIAL → IDLE, reachability=DEAD
LANDING → IDLE, reachability=DEAD
```

Но отчёт правильно говорит `NO_TRANSITION_DEFINED`. Несуществующие переходы не должны находиться в таблице реальных transitions.

Также call site `approach_phases.py:373` относится к FINAL takeover path, а не должен автоматически группироваться с INTERMEDIATE.

### Требуется

- Удалить две несуществующие transition rows.
- Хранить отсутствие перехода в отдельном `missing_transitions`/design-gap разделе.
- Получить 5 forward + 2 фактических abort semantic transitions только после точной phase attribution каждого call site.
- Согласовать CSV, JSON, MMD, DOT, report и verifier.

---

## 10. Actuator counters противоречат друг другу

Отчёт заявляет:

```text
ae.event = 47
set_* = 25
total interactions = 80
```

Verifier фактически считает из `actuator-sinks.csv`:

```text
ae.event = 26
set_* = 46
total rows = 72
```

`runtime-architecture.json` также содержит 72 actuator_sinks.

### Требуется

- Определить отдельные сущности: terminal writes, method definitions, high-level call sites, backend interactions.
- Не смешивать их в одной таблице.
- Устранить double counting.
- Сделать каждый счётчик воспроизводимым SQL/Python-агрегацией по типизированным полям.
- Все артефакты должны показывать одинаковые значения для одинаковой метрики.

---

## 11. Исправить ошибочный вывод об actuator exception

`frame-command-order.csv` утверждает:

```text
control.set_* raises
→ propagates to execute_approach
→ error budget
```

Но `MSFSControl.set_*` на baseline содержит локальные `try/except Exception` и только логирует ошибку. Это означает возможный fail-silent actuator write, который main error budget не видит.

### Требуется

- Проверить каждый terminal actuator method.
- Разделить:
  - swallowed/logged failures;
  - propagated exceptions;
  - returned status failures;
  - CommandRejected.
- Обновить fail-safe matrix и risk verdict.
- Добавить offline tests/harness для fail-silent path и CommandRejected path.

---

## 12. Финальная упаковка v3

Создать:

```text
RUNTIME-ARCHITECTURE-3971ba1-v3.zip
```

Обязательные свойства:

1. стандартная directory structure (`harness/...`);
2. manifest после всех изменений;
3. все hashes совпадают;
4. verifier запускается из распакованного ZIP по документированной команде;
5. `verifier-stdout.txt` включён;
6. harness results и traces семантически проверены;
7. JSON schema заполнена;
8. gateway lifecycle исправлен;
9. production-код не изменён;
10. git proof приложен отдельным текстовым файлом.

Финальный статус до закрытия этих пунктов:

```text
INCOMPLETE_FALSE_POSITIVE_HARNESS
```

---

## Формат ответа MiMo

```text
STATUS
FALSE_POSITIVES_FIXED
GATEWAY_LIFECYCLE
GO_AROUND_SCOPE
HARNESS_SEMANTIC_RESULTS
JSON_SCHEMA
EXACT_COUNTERS
MANIFEST_FULL_CHECK
STANDALONE_VERIFIER
DEPGRAPH_RECONCILIATION
UNRESOLVED_REQUIRING_MSFS
ZIP_PATH
GIT_PROOF
```

Не вставлять MMD/JSON/CSV в чат. Приложить только v3 ZIP и краткие счётчики.

---

## Критерий приёмки

> PASS означает фактическое выполнение заявленного production path и проверку ожидаемого результата. Наличие scenario ID, ручная запись trace или отсутствие исключения не являются доказательством PASS.
