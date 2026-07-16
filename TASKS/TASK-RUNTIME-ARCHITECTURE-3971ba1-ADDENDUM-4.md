# TASK: RUNTIME-ARCHITECTURE-3971ba1 — ADDENDUM 4

## Статус проверки v4

```text
REQUEST_CHANGES — JSON SCHEMA NOT UPDATED + STANDALONE VERIFIER CLAIM NOT REPRODUCIBLE
```

Production-код не менять. Исправлять только `research/runtime_architecture/`. Commit/push не делать.

Baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

---

## 1. Что в v4 подтверждено и не должно откатываться

Независимая проверка ZIP подтвердила:

- 49 ZIP entries;
- 0 backslash names;
- 0 absolute paths;
- 48 manifest entries, 48/48 hashes и sizes совпадают;
- 0 unmanifested/missing files;
- 0 `__pycache__`/`.pyc`;
- 11 scenario IDs;
- 11 matching trace files;
- IDs уникальны, sets совпадают;
- `loc_signal_loss`: `result is None`, LOC branch вызван, ILS branch не вызван, go-around=true;
- `non_ils_synthetic_glidepath`: вызов synthetic glidepath подтверждён;
- `raw_ae_event_exception_swallowed`: fail-silent подтверждён;
- `gateway_command_rejected`: CommandRejected подтверждён;
- `phase-transitions.csv`: 7 rows, фиктивные INITIAL→IDLE и LANDING→IDLE удалены;
- `RAW_CONTROL_BYPASS = 0` для обычных phase-state paths;
- DEPGRAPH reconciliation 49/49.

Эти результаты сохранить.

---

## 2. Заявленная JSON schema отсутствует в упакованном v4

Фактический `runtime-architecture.json`:

```text
nodes = 49
edges = 91
states = 6
data_items = 0
actuator_sinks = 72
safety_mechanisms = 7
scenarios key = ABSENT
go_around_call_sites = 10
```

У всех 72 actuator sinks отсутствует `evidence_level`.

`edge.evidence_level` всё ещё содержит невалидные свободные строки, например:

```text
STATIC_CONFIRMED main.py:896-897
No execute_go_around() call in InitialPhaseState
STATIC_CONFIRMED multiple sites
```

### Требуется

Пересобрать `runtime-architecture.json` из актуальных CSV/harness results:

1. `data_items` — все строки `data-dictionary.csv`.
2. `scenarios` — все 11 сценариев.
3. `actuator_sinks[*].evidence_level` — обязательный enum.
4. `edges[*].evidence_level` — только допустимый enum.
5. File:line перенести в `evidence_ref`, `source_file`, `source_line`.
6. Отсутствующие переходы не хранить как edges.
7. Добавить schema version в meta.

Допустимые evidence levels:

```text
STATIC_CONFIRMED
TEST_CONFIRMED
HARNESS_CONFIRMED
RUNTIME_CONFIRMED
INFERRED
UNREACHED
DEAD
```

Verifier должен проверять exact schema и завершаться non-zero при:

- `data_items == 0`;
- отсутствии `scenarios`;
- отсутствии evidence level;
- невалидном enum;
- расхождении scenario IDs JSON/results/traces;
- расхождении transition count JSON/CSV/report.

---

## 3. `standalone verifier exit 0` не воспроизводится

Команда из сообщения:

```text
python verify_runtime_architecture.py
```

запущена непосредственно в чистом каталоге после распаковки v4.

Фактический результат:

```text
RESULT: FAIL (11 errors)
EXIT=1
```

Причины:

- `depgraph.json` не включён/не найден;
- production source files не включены/не найдены для file:line bounds.

Verifier по-прежнему печатает:

```text
verify_runtime_architecture v2
```

и вычисляет project root относительно расположения артефакта. Поэтому он проходит только внутри исходного repository layout, но не является standalone verifier ZIP.

### Выбрать один честный вариант

#### Вариант A — настоящий standalone verifier

Включить immutable evidence bundle:

```text
evidence/depgraph.json
evidence/source-line-index.json
```

или необходимые source snapshots/hashes, чтобы baseline, nodes и file:line bounds проверялись без внешнего репозитория.

Команда после распаковки:

```text
python verify_runtime_architecture.py
```

должна вернуть exit 0.

#### Вариант B — repo-bound verifier

Если source/DEPGRAPH намеренно не включаются, перестать называть verifier standalone.

Добавить CLI:

```text
python verify_runtime_architecture.py \
  --artifact-root <unpacked-dir> \
  --project-root C:\BAT\msfs_autoland \
  --depgraph-path C:\BAT\msfs_autoland\research\depgraph\depgraph.json
```

Verifier должен:

- проверить HEAD baseline;
- проверить source line bounds;
- проверить DEPGRAPH;
- вернуть exit 0.

В отчёте и финальном сообщении честно указать `REPO_BOUND_VERIFIER`, не `STANDALONE`.

Предпочтителен вариант A, поскольку задача требовала независимую проверку ZIP.

---

## 4. `verifier-stdout.txt` не доказывает standalone запуск

Текущий stdout был получен в исходном repository layout. Он не совпадает с результатом запуска из ZIP.

### Требуется

Сохранить в `verifier-stdout.txt`:

- exact command;
- current working directory;
- Python version;
- artifact root;
- project root/depgraph path, если используются;
- полный stdout;
- exit code.

Для standalone варианта command должен выполняться в freshly extracted temporary directory.

---

## 5. Verifier всё ещё не проверяет semantic claims

Текущий verifier проверяет наличие IDs/traces и `passed == 11`, но не scenario-specific semantics. Также manifest проверяется spot-check способом внутри verifier, хотя отдельная независимая проверка всех hashes дала PASS.

### Требуется

Добавить проверки минимум:

- `loc_signal_loss`: result None, loc called, ILS not called, go-around true;
- `synthetic_glidepath`: synth call event и VS event;
- `safety_guard_goaround`: guard GO_AROUND и go-around event;
- `stabilized_monitor_goaround`: control/throttle до stabilization/go-around;
- `missing_telemetry`: real execute_approach event, три ошибки, stop/go-around согласно takeover;
- `raw_ae_event_exception_swallowed`: ae exception + swallowed/logged;
- `gateway_command_rejected`: rejected + raw control not called;
- exact scenario set == exact trace set;
- каждый trace имеет минимум один event;
- все 48 manifest hashes/sizes;
- MMD/DOT/JSON reconciliation не через `len(edges)>0`, а через типизированные IDs/registry mapping.

---

## 6. Trace wording

Не утверждать, что каждый trace содержит полный generic набор:

```text
production_method_enter, command_request, authorize, backend_call, go_around/stop
```

Не каждому сценарию применимы все события. Формулировать:

> Каждый trace содержит обязательные scenario-specific events, проверяемые verifier.

---

## 7. Финальная упаковка v5

Создать:

```text
RUNTIME-ARCHITECTURE-3971ba1-v5.zip
```

Acceptance gate:

```text
ZIP paths portable                 PASS
manifest full hashes/sizes         PASS
11 scenario IDs/traces             PASS
scenario-specific semantics        PASS
JSON schema complete               PASS
data_items > 0                     PASS
scenarios = 11                     PASS
sink evidence levels complete      PASS
edge evidence enum valid           PASS
transitions JSON/CSV/report = 7     PASS
fresh extraction verifier exit 0   PASS
DEPGRAPH 49/49                     PASS
production unchanged               PASS
```

Финальный статус до закрытия двух блокеров:

```text
INCOMPLETE_JSON_AND_VERIFIER
```

---

## Формат ответа

```text
STATUS
JSON_SCHEMA_VERSION
JSON_COUNTS
EVIDENCE_LEVEL_VALIDATION
SCENARIO_SEMANTIC_VALIDATION
TRANSITION_RECONCILIATION
VERIFIER_MODE
FRESH_EXTRACTION_COMMAND
FRESH_EXTRACTION_CWD
FRESH_EXTRACTION_EXIT
MANIFEST
DEPGRAPH_RECONCILIATION
UNRESOLVED_REQUIRING_MSFS
ZIP_PATH
GIT_PROOF
```

Приложить только v5 ZIP и короткие счётчики.

---

## Критерий приёмки

> Утверждения финального сообщения должны воспроизводиться из файлов внутри переданного ZIP. Если verifier требует исходный repository layout, это должно быть явно объявлено и передано параметрами, а не называться standalone.
