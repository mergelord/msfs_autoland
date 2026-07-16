# TASK-MIMO-P2-ECHELON-CHECKPOINT-A-9FBF652

## Режим

`AUDIT_AND_REBASELINE_ONLY — NO CODE CHANGES`

Это Checkpoint A второго эшелона P2. Сначала нужно очистить исторический backlog от уже исправленных, устаревших, дублирующих и неверно классифицированных пунктов на текущем master. Только после независимого ревью отчёта будет отдельная задача на реализацию.

## Репозиторий и доверенная база

- Repository: `zhuk-mou-1/msfs_autoland`
- Branch: `master`
- Required base SHA: `9fbf652f94f38b9de0f799a298d8194db89d22a3`
- Этот SHA — независимо подтверждённый merge commit PR #7.
- Baseline suite: `346 passed`, 1 warning.
- Известные pre-existing CI failures:
  - `lint-ruff`;
  - `check-architecture-freshness`.
- Остальные checks на merge commit успешны.

Перед началом:

```bash
git fetch origin
git checkout master
git reset --hard 9fbf652f94f38b9de0f799a298d8194db89d22a3
git status --short
git rev-parse HEAD
git rev-parse origin/master
pytest tests/ -q
```

Если `HEAD` или `origin/master` не равен требуемому SHA, либо рабочее дерево не чистое — `STOPPED_ON_GATE`.

## Цель Checkpoint A

Для каждого кандидата ниже вернуть один статус:

- `CONFIRMED_P1` — обнаружен оставшийся safety/blocker выше заявленного эшелона; не исправлять, остановить планирование P2 до решения;
- `CONFIRMED_P2` — реальный поведенческий/надёжностный долг для текущей волны;
- `CONFIRMED_P3` — реальный, но низкоприоритетный долг;
- `TEST_GAP_ONLY`;
- `RESOLVED_BY_<SHA/PR>`;
- `DUPLICATE_OF_<ID>`;
- `FALSE_POSITIVE`;
- `UNPROVEN` — недостаточно call-graph/runtime evidence.

Нельзя принимать историческую формулировку как доказательство. Все пункты перепроверить на `9fbf652...` по текущему коду и текущим production call sites.

## Обязательный формат доказательства для каждого пункта

1. Точный файл, функция и актуальные номера строк.
2. Byte-exact выдержка текущего кода.
3. Production reachability:
   - caller;
   - producer/consumer;
   - активная ветка;
   - либо доказательство отсутствия production caller.
4. Числовой probe или минимальный исполняемый test, если пункт про математику/границы.
5. Наблюдаемое поведение «сейчас» и ожидаемый контракт.
6. Severity с объяснением impact и likelihood.
7. Минимальный предлагаемый scope фикса — только для планирования, код не менять.
8. Red-without-fix test design.

## Группа A — Autothrottle timing и error handling

### P2-AT-01 — PID `dt` использует wall clock

Текущий кандидат:

```python
current_time = time.time()
dt = current_time - self.previous_time
```

Проверить:

- остаётся ли это в реальном `AutothrottleController.calculate_throttle()`;
- reset/activate/deactivate lifecycle для `previous_time`;
- последствия отрицательного/огромного `dt` для integral и derivative;
- применим ли `time.monotonic()`;
- нужна ли инъекция clock для детерминированных тестов;
- поведение при первом кадре и после длительной паузы.

Ожидаемый минимальный дизайн: monotonic clock + защита/кламп аномального `dt`, без изменения PID sign convention и нормального nominal `dt`.

### P2/P3-AT-02 — `dt <= 0` молча отключает D-term

Проверить, является ли отсутствие warning/telemetry самостоятельной находкой или частью P2-AT-01. Не создавать отдельный фикс, если это один root cause.

### P3-AT-03 — слишком широкий `except Exception` в `VJoyThrottleIntegration.set_throttle`

Проверить реальные исключения `VirtualJoystick.set_throttle`, контракт fail-safe и риск скрытия programming errors. Не сужать исключения без точного инвентаря типов.

## Группа B — Connection monitor

### P2-CM-01 — `update_flight_phase()` не защищён от None/non-finite

Текущий кандидат использует числовые сравнения вида:

```python
altitude_agl < 1500
vertical_speed > 500
```

Проверить все production callers и реальные значения из telemetry. Определить fail-safe контракт для missing/NaN/inf: сохранить прошлую фазу, UNKNOWN или иной вариант — не угадывать.

Обязательные probes: `None`, `NaN`, `+inf`, `-inf` по altitude/VS; `on_ground=True` при отсутствующих числах.

### P2-CM-02 — гэпы в `elif`-цепочке фаз

Проверить текущую таблицу классификации как минимум для:

- 1500–10000 ft и `abs(VS) <= 500`;
- 500–3000 ft и `VS >= 0`;
- ниже 10000 ft в level flight;
- границы 500/1500/3000/10000 ft и ±500 fpm;
- `ground_speed` принимается, но не используется.

Отдельно определить, должна ли фаза удерживаться, вычисляться полностью или иметь `UNKNOWN`. Не превращать design ambiguity в автоматический fix.

### P2-CM-03 — active-test метрики обновляются несогласованно

`perform_active_test()` обновляет latency/reliability/available, но исторически не синхронизировал `total_operations`, `consecutive_errors`, `error_count` и timestamps.

Проверить:

- может ли это оставить `is_degraded()` истинным после успешного active test;
- является ли active test observation отдельным источником, который не должен сбрасывать passive history;
- точный контракт `LiveMetrics` и `ConnectionOptimizer`;
- влияние на `should_switch_method()` и реальный I/O switching.

Нужен state-transition probe до/после active test.

### P2/P3-CM-04 — переключение при деградации без hysteresis

Проверить реальный риск повторных переключений. Не повторять старое преувеличение «дрожание от малейшей разницы score»: повторное переключение требует отдельной деградации нового метода. Классифицировать только по доказанному сценарию.

### P3-CM-05 — декоративные/несогласованные поля профиля

Проверить:

- `total_flight_time`;
- `performance_history` — история или snapshot по контракту;
- `ground_speed`;
- кто читает эти поля.

Если поля не влияют на runtime decisions — P3/documentation cleanup, не P2.

### OPEN-CM-06 — влияет ли выбранный monitor method на реальный I/O

Исторически не доказано. Трассировать `switch_to_method/current_method` до `telemetry`, `aircraft_adapter`, `connection_optimizer`, SimConnect/WASM/L:Vars. Статус только `CONFIRMED_*` или `UNPROVEN` с точной границей знания.

## Группа C — Control ownership / Command gateway

### P2/P3-CO-01 — `external_at_active` не передаётся production callers

Проверить все вызовы `compute_ownership()`. Сейчас параметр участвует в выборе throttle owner, но исторически production всегда оставлял default `False`.

Определить:

- реальная ли функциональность внешней autothrottle существует;
- параметр должен быть подключён, удалён или переименован;
- не дублирует ли он `use_autothrottle`, active-state контроллера или vJoy readiness.

### P2-CG-01 — permissive default source

Текущий кандидат:

```python
_SOURCE = ContextVar(..., default=CommandSource.AIRCRAFT_AP)
```

Проверить, может ли actuator command без `source_scope()` пройти авторизацию, когда ожидаемый owner — AP. Это design-risk, а не автоматически production bug.

Сравнить варианты:

- default `None/UNSCOPED` с reject;
- обязательный scope только для actuator methods;
- сохранение совместимости для readback/helper methods.

Обязательные tests/probes:

- AP owner + unscoped actuator;
- EXTERNAL owner + unscoped actuator;
- explicit AP/EXTERNAL/SAFETY scopes;
- scope restoration after exception;
- nested scopes;
- ContextVar isolation.

### TEST-CG-02 — нет прямого покрытия `CommandGateway`

Подтвердить актуальный test inventory. Не считать `FakeControl` phase tests прямым покрытием gateway. Предложить минимальный отдельный test module.

### Контроль ложных находок

Не возвращать уже опровергнутые COG-пункты как дефекты:

- `set_rudder` уже есть в `_CHANNELS`;
- `set_gear(False)` после SAFETY scope не доказывает bypass;
- сохранённая guarded closure продолжает вызывать `_authorize()`;
- `ContextVar` сам по себе не является shared-thread race.

## Группа D — Wind correction reconciliation

### RESOLUTION-CHECK-WIND-01 — vertical double-counting

Исторический P2-кандидат: `corrected_vs = base_vs + headwind * 10`, хотя `base_vs` уже вычисляется из ground speed.

На текущем baseline ожидается уже исправленное поведение:

```python
corrected_vs = base_vs
vs_correction = 0.0
```

а `calculate_pitch_correction()` оставлен deprecated для совместимости.

Требуется:

- подтвердить, что production call graph больше не вызывает deprecated helper;
- подтвердить, что все consumers получают `corrected_vs == base_vs`;
- классифицировать старую находку `RESOLVED`, а не чинить второй раз;
- отдельно решить, является ли удаление deprecated dead helper P3 cleanup.

Не менять wind physics в этой задаче.

## Группа E — исторические кандидаты, требующие stale-status reconciliation

Эти пункты могли быть закрыты PR #5/#6/#7 или оставаться вне их scope. Проверить, но не исправлять.

### REC-01 — EngineFailureDetector production integration

Исторически экземпляр не создавался в `AutoLandSystem`, поэтому asymmetric-thrust logic в autothrottle/flare была недостижима. Проверить текущие `main.py`, `autothrottle.py`, `flare_controller.py`, `approach_phases.py` и tests.

Если детектор теперь подключён, обязательно проверить старые latent risks:

- all-engines-failed division by zero;
- `number_of_engines <= 0`;
- recovery/flapping asymmetry;
- wall-clock confirmation window.

Если любой crash/safety path остаётся reachable — `CONFIRMED_P1` и остановка перед P2 implementation.

### REC-02 — ILS autothrottle activation

Исторически ILS transition to FINAL не вызывал `autothrottle.activate()`. Проверить текущую ветку и tests. Если не исправлено и production-reachable — `CONFIRMED_P1`.

### REC-03 — weight units

PR #6 исправил kg/lbs mismatch на boundary вызова autothrottle. Подтвердить `RESOLVED_BY_PR6`, не открывать повторно без нового независимого пути.

### REC-04 — landing distance GS=0

PR #5 добавил guard. Подтвердить `RESOLVED_BY_PR5`.

### REC-05 — safety guard missing VS/bank и finite inputs

PR #5/#6 исправляли G5 и finite checks. Подтвердить resolved status и актуальные integration tests.

### REC-06 — navigation follow-up test gap

PR #7 исправил navigation production defects. Отдельного end-to-end теста `SyntheticGlidepath` для `HIGH before intercept` нет. Классифицировать как `TEST_GAP_ONLY`; не смешивать с P2 production fix.

## Группа F — дополнительные подтверждённые исторические P2/P3 кандидаты

Проверить актуальность и ранжировать, не исправлять:

1. `aircraft_adapter.set_heading/set_altitude` — прямой доступ к profile keys против fail-safe pattern `set_vertical_speed`; production reachability была ограничена.
2. `aircraft_adapter.disengage_autopilot` — fallback с `event_off` на toggle `event`; safety impact смягчён последующим authoritative `control.set_autopilot_master(False)`.
3. `aircraft_config_reader` — wildcard внутри `Path()` для WindowsApps не разворачивается; исторически dead fallback.
4. `flare_controller`:
   - `FlareConfig.throttle_reduction_start <= 0`;
   - `height_range <= 0` silent fallback без warning;
   - мёртвый `flare_start_time`;
   - hard-coded `<10 ft` и wind magic numbers.
5. `approach_speed_calculator`:
   - `preferred_flaps` numeric vs string keys;
   - gust correction относительно полной wind velocity вместо runway component;
   - unvalidated `flaps_config` keys;
   - VAPP/VREF semantics в safety thresholds.
6. `connection_monitor` profile/history fields — не дублировать CM-05.
7. `safety_guard`:
   - exception-safety reset/go-around chain;
   - ordering при одновременном нарушении нескольких rules;
   - snapshot values vs presence flags.
8. Replay/test gaps:
   - VOR/NDB fixtures;
   - guard-triggered go-around;
   - сквозной integration scenario.

Для каждого дать текущий status. Если scope слишком велик, всё равно сделать static/current-code classification; глубокие probes обязательны только для кандидатов, предлагаемых в первую реализационную волну.

## Требуемая разбивка после анализа

Сформировать четыре корзины:

### Wave P2-A — small, contract-preserving

Примерный тип работ: monotonic clock, defensive validation, direct gateway tests, очевидные dead-parameter/documentation cleanups. Не включать behavior redesign без утверждённого контракта.

### Wave P2-B — behavior/design decisions

Connection phase table, active/passive metrics semantics, fail-closed unscoped gateway, approach-speed/VREF-VAPP policy и другие изменения, требующие явного решения.

### P3 / test maintenance

Dead helpers, logging, docs, isolated fallback paths, integration test gaps.

### Resolved / false / duplicate / unproven

С точным PR/SHA или доказательством.

Для P2-A и P2-B дать:

- предлагаемый список файлов;
- зависимости между пунктами;
- риск регрессии;
- тест-план;
- рекомендуемый порядок PR;
- запрет на смешивание несвязанных подсистем в один большой PR.

## Проверки

Без изменений кода всё равно выполнить:

```bash
pytest tests/ -q
ruff check modules/ tests/
python -m compileall -q modules tests
git diff --check
git status --short
```

Отдельно записать фактический baseline global ruff result и не выдавать известный долг за новую регрессию.

## Выходной файл

Создать отчёт:

```text
TASKS/REVIEWS/P2-ECHELON-CHECKPOINT-A-9FBF652.md
```

Файл локальный, не коммитить.

## Формат ответа

```text
STATUS: COMPLETED_NO_CHANGES | STOPPED_ON_GATE
BASE_SHA: <full sha>
HEAD_SHA: <full sha>
WORKTREE: clean/dirty
BASELINE_TESTS: <raw summary>
CANDIDATE_TABLE: <ID -> status -> severity -> evidence>
P2_A_PLAN: <ordered list>
P2_B_PLAN: <ordered list>
P3_TEST_PLAN: <ordered list>
RESOLVED_FALSE_UNPROVEN: <ordered list>
P1_ESCALATIONS: <none or exact blockers>
FILES_READ: <complete list>
COMMANDS_AND_OUTPUTS: <exact>
REPORT_PATH: TASKS/REVIEWS/P2-ECHELON-CHECKPOINT-A-9FBF652.md
CODE_CHANGED: no
COMMIT_CREATED: no
PR_CREATED: no
```

## Запреты

- Не создавать ветку, commit или PR.
- Не менять production/test/docs files.
- Не обновлять architecture snapshot.
- Не чинить global ruff debt.
- Не начинать Pass B.
- Не объединять исторические кандидаты без проверки current baseline.
- Не принимать старые line numbers, quotes или severity без повторной трассировки.
