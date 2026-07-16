# TASK: RUNTIME-ARCHITECTURE-3971ba1 — ADDENDUM 3

## Статус проверки v3

```text
REQUEST_CHANGES — CLAIMED FIXES NOT PRESENT IN PACKAGED ARTIFACTS
```

Production-код не менять. Исправлять только `research/runtime_architecture/`. Commit/push не делать.

Baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

---

## 1. `loc_signal_loss` — доказанный false PASS

Фактический `harness/results.json` из v3:

```json
{
  "id": "loc_signal_loss",
  "status": "PASS",
  "detail": {
    "loc_loss_result": "<MagicMock name='mock.calculate_ils_approach()' ...>",
    "go_around": false
  }
}
```

Trace также показывает:

```json
{
  "phase_after": "FINAL",
  "go_around": false,
  "entries": []
}
```

Сценарий не вошёл в LOC-loss ветку, но получил PASS.

### Требуется

- Настроить объект так, чтобы реальный `AutoLandSystem._calculate_approach_data()` вошёл именно в ветку `station.type == 'LOC'`.
- `calculate_loc_approach()` должен вернуть `{"loc_available": false, ...}`.
- Assert:
  - результат `is None`;
  - `execute_go_around` вызван ровно один раз;
  - ILS/VOR альтернативные ветки не вызваны;
  - pending telemetry frame вызван согласно production path.
- PASS запрещён при `go_around != true`.

---

## 2. JSON schema не обновлена, несмотря на заявление

Фактический `runtime-architecture.json` из v3:

```text
data_items = 0
scenarios key = ABSENT
actuator_sinks without evidence_level = 72
```

`edge.evidence_level` всё ещё содержит произвольные строки, например:

```text
STATIC_CONFIRMED main.py:896-897
No execute_go_around() call in InitialPhaseState
STATIC_CONFIRMED multiple sites
```

### Требуется

- Реально пересобрать JSON после изменений.
- `data_items` заполнить из `data-dictionary.csv`.
- Добавить `scenarios` со всеми обязательными сценариями и evidence levels.
- Добавить enum `evidence_level` каждому actuator sink.
- Нормализовать edge evidence строго к enum:

```text
STATIC_CONFIRMED
TEST_CONFIRMED
HARNESS_CONFIRMED
RUNTIME_CONFIRMED
INFERRED
UNREACHED
DEAD
```

- File:line и пояснение хранить отдельно.
- Verifier должен валидировать schema, а не только наличие JSON edges.

---

## 3. Phase transitions CSV не исправлен

Фактический `phase-transitions.csv` v3 по-прежнему содержит 9 строк, включая фиктивные:

```text
INITIAL → IDLE, DEAD
LANDING → IDLE, DEAD
```

Это противоречит заявлению `5 forward + 2 abort transitions`.

### Требуется

- Удалить две несуществующие transition rows.
- Реальные transitions = 7 строк, если подтверждены 5 forward + 2 abort.
- Отсутствующие переходы хранить отдельно как design gaps, не как transitions.
- Согласовать CSV, JSON, MMD, DOT, report и counters.

---

## 4. Standalone verifier фактически FAIL

При запуске непосредственно из предоставленного ZIP:

```text
RESULT: FAIL (14 errors)
EXIT=1
```

Verifier всё ещё печатает заголовок:

```text
verify_runtime_architecture v2
```

и не содержит обещанного standalone CLI.

### Требуется

- Реализовать документированный запуск после распаковки ZIP в произвольный каталог.
- Добавить CLI args:

```text
--artifact-root
--project-root
--depgraph-path
```

либо включить достаточный immutable evidence bundle.
- Добавить `verifier-stdout.txt` с фактическим `RESULT: PASS` и exit code 0.
- Упакованный verifier должен запускаться без предварительного ручного переименования файлов.

---

## 5. ZIP path portability всё ещё не исправлена

В v3 найдено 17 ZIP entries с Windows backslashes:

```text
harness\results.json
harness\run_harness.py
harness\command-traces\...
```

На POSIX это обычные имена файлов в корне, не каталоги. Поэтому verifier не находит harness.

### Требуется

Создавать ZIP через `zipfile` с относительными POSIX arcnames:

```python
arcname = path.relative_to(root).as_posix()
```

После сборки автоматически проверить:

```python
assert all('\\' not in name for name in zip.namelist())
```

---

## 6. В ZIP остались stale v2 artifacts

Присутствуют одновременно:

```text
actuator_exception.json
raw_ae_event_exception_swallowed.json
nonsynthetic_glidepath.json
non_ils_synthetic_glidepath.json
missing_telemetry.json
```

Также включён:

```text
harness/__pycache__/run_harness.cpython-314.pyc
```

Это загрязняет manifest и создаёт неоднозначность актуального набора сценариев.

### Требуется

- Перед генерацией очистить `harness/command-traces/`.
- Удалить `__pycache__`, `.pyc`, старые traces.
- Генерировать traces заново только из текущего `SCENARIOS`.
- Assert: множество trace filenames точно равно множеству scenario IDs.

---

## 7. Обязательный `missing_telemetry` нельзя заменять gateway-тестом

Исходная задача требовала отдельный scenario `missing_telemetry`. Gateway rejection — дополнительный важный сценарий, но не замена telemetry failure.

### Требуется

Итоговый набор должен содержать минимум 11 сценариев:

1. `ils_final_ap`
2. `ils_final_vjoy`
3. `non_ils_synthetic_glidepath`
4. `safety_guard_goaround`
5. `stabilized_monitor_goaround`
6. `loc_signal_loss`
7. `takeover_initiation`
8. `takeover_failure`
9. `missing_telemetry`
10. `raw_ae_event_exception_swallowed`
11. `gateway_command_rejected`

`missing_telemetry` должен выполнять реальный `AutoLandSystem.execute_approach()` с детерминированным ограничением loop и доказать error-budget действие.

---

## 8. Traces не отражают ключевые вызовы

Даже исправленные сценарии имеют пустые `entries`, например:

```text
non_ils_synthetic_glidepath
safety_guard_goaround
loc_signal_loss
```

MagicMock assertion может подтвердить вызов, но обязательный trace должен его отражать.

### Требуется

Trace каждого сценария должен содержать ключевые события, на которых основан PASS:

```text
production_method_enter
condition/branch
command_request
authorize
command_allowed/rejected
backend_call
state_transition
go_around/stop
production_method_exit
```

Verifier должен проверять scenario-specific обязательные events.

---

## 9. Manifest: hashes теперь совпадают, но состав неверен

Положительный результат v3:

```text
50 manifest entries
0 hash mismatches
0 unmanifested files
```

Однако manifest корректно хеширует загрязнённый и непереносимый набор, включая stale traces и pycache. Это не закрывает требования состава.

### Требуется

После очистки сформировать новый manifest и проверять одновременно:

- hashes/sizes;
- отсутствие stale files;
- отсутствие `.pyc/__pycache__`;
- POSIX ZIP names;
- exact trace set == exact scenario set;
- наличие report, verifier stdout, git proof.

---

## 10. Сохранить подтверждённые исправления v3

Не откатывать:

- правильный lifecycle `MSFSControl → CommandGateway`;
- `RAW_CONTROL_BYPASS = 0` для phase-state paths;
- подтверждённый fail-silent `MSFSControl.set_*`;
- gateway rejection scenario;
- точную проверку SAFETY scope;
- 49/49 DEPGRAPH reconciliation;
- 26 `ae.event` + 46 `set_*` rows = 72 для данной CSV-классификации;
- полный manifest hash check.

---

## 11. Финальная упаковка v4

Создать:

```text
RUNTIME-ARCHITECTURE-3971ba1-v4.zip
```

Перед отправкой выполнить на чистом temporary extraction:

```text
1. unzip to empty directory
2. assert no backslash archive names
3. run standalone verifier
4. require exit code 0
5. validate all manifest hashes
6. validate JSON schema
7. validate exact scenario/trace sets
8. validate scenario-specific semantic assertions
```

Финальный статус до этого:

```text
INCOMPLETE_PACKAGED_ARTIFACTS
```

---

## Формат ответа

```text
STATUS
LOC_LOSS_RESULT
SCENARIO_COUNT_AND_IDS
TRACE_EVENT_VALIDATION
JSON_SCHEMA_COUNTS
TRANSITION_COUNTS
ZIP_PORTABILITY
MANIFEST
STANDALONE_VERIFIER_COMMAND
STANDALONE_VERIFIER_EXIT
DEPGRAPH_RECONCILIATION
UNRESOLVED_REQUIRING_MSFS
ZIP_PATH
GIT_PROOF
```

Приложить только v4 ZIP и короткие счётчики. Не вставлять MMD/JSON/CSV в чат.

---

## Критерий приёмки

> Принимается содержимое реально упакованного ZIP, а не описание того, что предположительно было исправлено в рабочем каталоге.
