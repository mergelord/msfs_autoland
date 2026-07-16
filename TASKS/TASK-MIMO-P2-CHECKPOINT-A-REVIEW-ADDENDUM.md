# TASK-MIMO-P2-CHECKPOINT-A — REVIEW ADDENDUM

## Вердикт по отчёту

`REQUEST_CORRECTIONS — NO CODE CHANGES`

Проверенный отчёт: `TASKS/REVIEWS/P2-ECHELON-CHECKPOINT-A-9FBF652.md`

Baseline остаётся:

```text
9fbf652f94f38b9de0f799a298d8194db89d22a3
```

Основная часть candidate inventory полезна, но отчёт пока нельзя использовать как прямое основание для реализации Wave P2-A. Есть фактические ошибки, невыполненные гейты и неправильное разделение contract-preserving/design-changing работ.

## 1. Gate/status inconsistency

Задача требовала `STOPPED_ON_GATE`, если worktree dirty. Отчёт вернул одновременно:

```text
STATUS: COMPLETED_NO_CHANGES
WORKTREE: dirty
```

Нужно:

1. Перечислить все 6 modified PNG и untracked artifacts через точный `git status --short`.
2. Для каждого modified tracked file доказать, что изменение существовало до начала Checkpoint A и не создано аудитом.
3. Если это pre-existing local state, оформить явный `GATE_WAIVER_REQUESTED` с доказательством, а не молча игнорировать гейт.
4. Не reset/checkout/delete пользовательские файлы без разрешения.

## 2. Обязательные команды не выполнены

Исходная задача требовала:

```bash
ruff check modules/ tests/
python -m compileall -q modules tests
git diff --check
git status --short
```

В отчёте прямо указано, что ruff и compileall не запускались; `git diff --check` также не приведён.

Запустить и приложить точные stdout/stderr/exit code. Известный global ruff debt классифицировать отдельно, но сам запуск обязателен.

## 3. P2-CM-02 содержит фактическую ошибку

Отчёт утверждает:

> Above 10000 ft, level flight → no phase assigned

Текущий код содержит:

```python
elif altitude_agl > 10000 and abs(vertical_speed) < 500:
    self.current_phase = FlightPhase.CRUISE
```

То есть level flight **выше** 10000 ft покрыт. Реальный boundary-gap возможен ровно при `altitude_agl == 10000`, потому что используются `< 10000` и `> 10000`.

Переписать таблицу CM-02 по точным интервалам и границам:

- `<500`, `500`, `1500`, `3000`, `10000` ft;
- VS `-500`, `+500` и значения по обе стороны;
- `on_ground=True`;
- NaN/None отдельно в CM-01.

Не смешивать «hold previous phase» с «unclassified»: текущий код при непопадании в ветку фактически сохраняет предыдущее значение. Нужно описать именно это наблюдаемое поведение.

## 4. P2-CM-03 содержит внутреннее противоречие

Отчёт говорит, что active test оставляет `consecutive_errors`, но после успешного active test `is_degraded()` якобы возвращает False.

Текущий `LiveMetrics.is_degraded()` первым условием проверяет:

```python
if self.consecutive_errors >= 3:
    return True
```

Следовательно, если до active test было `consecutive_errors >= 3`, запись `reliability=1.0` не снимает degraded status вообще. Если было 1–2 ошибки, поведение другое.

Нужен исполняемый state-transition probe как минимум для initial consecutive errors `0`, `2`, `3`, с фиксацией:

- `is_degraded()` до active test;
- всех полей после active test;
- `get_score()` и `is_degraded()` после active test;
- поведение после следующей passive success/failure.

После probe разделить:

- подтверждённый defect;
- design question: должны ли active и passive observations иметь раздельное состояние;
- минимальный безопасный фикс.

## 5. P2-CG-01 ошибочно назван готовым small fix

Отчёт утверждает:

> all callers use `source_scope()`

Это неверно. В текущем production-коде есть множество прямых unscoped AP-команд через `self.system.control`, например в `approach_phases.py`:

```python
self.system.control.set_heading_hold(...)
self.system.control.set_vertical_speed(...)
self.system.control.set_throttle(...)
self.system.control.set_flaps(...)
self.system.control.set_gear(...)
```

Также `autopilot_takeover.py::_send_disengage_commands()` вызывает:

```python
control.set_autopilot_master(False)
```

без локального `source_scope()`.

Сейчас default `AIRCRAFT_AP` обеспечивает совместимость этого production path. Простая замена default на `UNSCOPED` с reject сломает штатные команды.

Требуется полный inventory всех вызовов методов из `CommandGateway._CHANNELS` после создания gateway:

- файл/функция/строка;
- scoped/unscoped;
- ожидаемый CommandSource;
- активная production reachability;
- тестовое покрытие.

После этого P2-CG-01 перенести в **P2-B design/migration**, а не P2-A. Предложить поэтапную миграцию:

1. direct gateway tests;
2. явное scope annotation всех production actuator paths;
3. только затем fail-closed default;
4. regression tests на INITIAL/INTERMEDIATE/FINAL/LANDING/go-around/takeover.

Не менять default в текущем fix-пакете.

## 6. REC-01 не является contract-preserving P2-A

Подключение `EngineFailureDetector` активирует ранее мёртвую production-логику и одновременно делает достижимыми latent defects:

- all-engines-failed division by zero;
- invalid `number_of_engines`;
- recovery/flapping;
- wall-clock confirmation window.

Это не small cleanup. Разбить на отдельные стадии:

### EFD-Stage-1 — hardening while still unreachable

- validate engine count;
- all-engines-failed fail-safe contract;
- monotonic confirmation/recovery timing;
- symmetric debounce/recovery decision;
- exhaustive unit tests.

### EFD-Stage-2 — integration design

- создать detector в `AutoLandSystem`;
- определить источник и частоту `update_engine_data()`;
- передать один и тот же instance в autothrottle и flare;
- определить поведение при unavailable/partial engine telemetry;
- integration/replay tests.

До Stage-1 detector не подключать. REC-01 перенести в отдельный P2-B/high-risk workstream.

## 7. REC-02 требует уточнения контракта, но evidence уже сильнее отчёта

В `main.py` default:

```python
self.use_autothrottle = True
```

При этом non-ILS transition активирует autothrottle, а ILS transition — нет. Это сильная асимметрия, а не нейтральное отсутствие информации.

Нужно проверить:

- UI/settings semantics `use_autothrottle`;
- docs;
- lifecycle `start_approach/stop_approach`;
- ILS tests;
- ownership interaction.

Вернуть owner-decision question в точной форме:

> Если `use_autothrottle=True`, должна ли автотяга активироваться при входе в FINAL для всех типов захода, включая ILS?

REC-02 оставить в P2-B до ответа владельца.

## 8. Неверная атрибуция Wind resolution

Отчёт пишет `RESOLVED_BY_PR7`. Vertical double-counting был устранён в wind-correction fix до PR #5, baseline merge `3971ba12113d8994665b1c9a172f2dca6c9e3855`.

Исправить attribution на `RESOLVED_BY_3971ba1` с точным commit/PR, если локальная история это подтверждает. PR #7 был navigation fix и не менял `modules/wind_correction.py`.

## 9. Неподтверждённые Group F пункты нельзя маркировать CONFIRMED

### F2

В таблице F2 стоит `CONFIRMED_P3`, но location содержит `need to check`, а `FILES_READ` показывает только `aircraft_adapter.py (1-264 lines)`. `disengage_autopilot` находится значительно ниже. Статус должен быть `UNPROVEN` до полного чтения функции и caller.

### F3/F5

Для WindowsApps wildcard и `preferred_flaps` нужен фактический config/runtime evidence. Прочитать:

- полный `aircraft_config_reader.py`;
- соответствующие config files;
- полный consumer path `approach_speed_calculator` + `main.py`;
- tests.

Не считать классификацию complete, если supporting file не включён в `FILES_READ`.

### F7a

«Partial counter state persists if exception occurs» само по себе не подтверждает реальный defect. Показать конкретную операцию внутри `evaluate()`/rules, которая может бросить после изменения counter state, либо понизить в `UNPROVEN/DESIGN_NOTE`.

## 10. Пересобрать Wave classification

Текущая `Wave P2-A (8 small, contract-preserving)` неверна: туда включены P3 cleanup, два owner-decision пункта и high-risk integration.

Пересобрать:

### P2-A — только подтверждённые contract-preserving

Предварительно допустимы после коррекции evidence:

1. P2-AT-01 — monotonic clock + осторожный dt policy;
2. P2-CM-01 — defensive finite validation с сохранением текущей фазы;
3. direct CommandGateway tests **без изменения default policy**.

Даже для AT-01 не принимать произвольный clamp `[0.01, 5.0]` без обоснования. Нужны фактическая частота control loop, pause semantics и тесты. Возможно безопаснее skip/reset PID state на аномальном dt, чем подменять длительную паузу на 5 секунд интегрирования.

### P2-B — design/behavior

- P2-CG-01 full scope migration;
- REC-01 detector hardening + later integration;
- REC-02 ILS autothrottle;
- CM-02 phase policy;
- CM-03 active/passive metrics semantics.

### P3 / maintenance

Оставшиеся cleanup/test items — отдельным списком, не добавлять в P2-A ради количества.

## 11. Исправить итоговые counts

После переклассификации пересчитать CONFIRMED_P2/P3/RESOLVED/DUPLICATE/UNPROVEN/TEST_GAP. Не сохранять числа `7/12/5/2/4/2`, если статусы изменились.

## Требуемый выход

Обновить локальный отчёт либо создать:

```text
TASKS/REVIEWS/P2-ECHELON-CHECKPOINT-A-9FBF652-ADDENDUM.md
```

Вернуть:

```text
STATUS: COMPLETED_NO_CHANGES | STOPPED_ON_GATE | GATE_WAIVER_REQUESTED
BASE_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
WORKTREE_EVIDENCE: <exact>
CORRECTED_COUNTS: <table>
CORRECTED_CANDIDATE_TABLE: <all changed statuses>
CM02_BOUNDARY_MATRIX: <exact>
CM03_STATE_PROBES: <exact>
GATEWAY_CALLSITE_INVENTORY: <complete>
REC01_STAGED_PLAN: <Stage-1/Stage-2>
REC02_OWNER_QUESTION: <exact>
CORRECTED_WAVES: <P2-A/P2-B/P3>
REQUIRED_COMMAND_OUTPUTS: <ruff/compileall/diff-check/status>
CODE_CHANGED: no
COMMIT_CREATED: no
PR_CREATED: no
```

## Запреты

- Не менять код.
- Не создавать ветку/commit/PR.
- Не подключать EngineFailureDetector.
- Не менять CommandGateway default.
- Не реализовывать owner-decision пункты.
- Не начинать Pass B.
