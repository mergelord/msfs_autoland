# TASK-MIMO-P2-CHECKPOINT-A — REVIEW ADDENDUM 2

## Вердикт

`REQUEST_FINAL_CORRECTIONS — NO CODE CHANGES`

Исправленный отчёт существенно лучше, но всё ещё содержит несколько проверяемых фактических ошибок. После их исправления Checkpoint A можно закрыть.

Baseline: `9fbf652f94f38b9de0f799a298d8194db89d22a3`.

## Что принято

- Gate waiver принимается только для read-only аудита; локальные PNG и artifacts не трогать.
- Обязательные ruff/compileall/diff-check выполнены.
- CG-01 перенесён в P2-B.
- REC-01 разбит на Stage-1 hardening и Stage-2 integration.
- REC-02 сформулирован как owner decision.
- Wind attribution перенесён с PR #7 на baseline `3971ba1`.
- Group F понижен там, где evidence недостаточно.
- P2-A ограничен AT-01, CM-01 и direct gateway tests.

## 1. CM-02 boundary matrix всё ещё неверна

Матрица должна учитывать порядок `elif`, а не только отдельные условия.

Ошибочные строки отчёта:

- `<500 | any → LANDING` — неверно: при `VS > 500` раньше срабатывает `TAKEOFF`.
- `500–1500 | abs(VS) <= 500 → HOLD` — неверно для `VS < 0`: срабатывает `APPROACH`.
- `1500–3000 | VS >= 0 → HOLD` — неверно при `VS > 500`: срабатывает `CLIMB`.
- `exactly 500 | any (not >500) → HOLD` — неверно при `VS < 0`: срабатывает `APPROACH`.
- `exactly 1500 | any → HOLD` — неверно: `VS > 500 → CLIMB`, `VS < 0 → APPROACH`.

Не пересчитывать вручную. Написать временный read-only probe, который создаёт `ConnectionMonitor`/минимальный объект и вызывает реальный `update_flight_phase()` по декартовой сетке:

```text
altitude = 499, 500, 501, 1499, 1500, 1501, 2999, 3000, 3001, 9999, 10000, 10001
VS = -501, -500, -1, 0, 1, 500, 501
on_ground = False
```

Перед каждым вызовом задавать различимую предыдущую фазу, чтобы `HOLD PREVIOUS` был виден. Приложить raw output и построить матрицу непосредственно из результата.

## 2. CM-03 probe всё ещё содержит ошибку

В `LiveMetrics.add_operation(..., success=True)` есть:

```python
self.consecutive_errors = 0
```

Но таблица отчёта для initial `3` и `5` говорит:

```text
Next passive success → True (consecutive_errors still 3/5)
```

Это неверно. После passive success counter сбрасывается в 0. Итоговый `is_degraded()` затем зависит от пересчитанной historical reliability/latency, но не от старого consecutive counter.

Запустить реальный executable probe через `LiveMetrics.add_operation()`; не использовать ручную таблицу. Для initial counters `0, 2, 3, 5` показать:

1. before active test;
2. after active test field assignments;
3. after one passive success;
4. отдельный fresh scenario after one passive failure.

Убрать вариант фикса «skip consecutive_errors when available=True»: `available=True` не доказывает отсутствие passive degradation и может ослабить fail-safe. До owner decision оставить только варианты:

- reset passive counter on successful active test;
- separate active/passive observations.

## 3. Gateway inventory не полный

Отчёт утверждает:

> All `source_scope()` callsites: None found in production code.

Это неверно. `main.py::execute_go_around()` содержит production SAFETY scope:

```python
scope = (
    self.control.source_scope(CommandSource.SAFETY)
    if hasattr(self.control, "source_scope") else nullcontext()
)
with scope:
    ...
```

Файл `main.py` был прочитан только в диапазоне 64–163, поэтому полный inventory заявлен без полного чтения.

Требуется:

- прочитать полный `main.py` и полный `approach_phases.py`;
- выполнить repo-wide text search по `source_scope(` и по каждому имени из `_CHANNELS`;
- дать точные line numbers, без `~200+`, `460+`, `600+`;
- отличить вызовы через gateway от `virtual_joystick`, adapter и raw control;
- включить `main.execute_go_around` SAFETY scope.

Bottom line остаётся тем же: default нельзя менять в P2-A. Но inventory должен быть фактически точным.

## 4. Wind attribution: исправить название ветки

`3971ba1` — merge ветки `fix/wind-correction`, а не `fix/navigation-core`. PR #7/navigation-core появился позже.

Исправить текст на:

```text
RESOLVED_BY_3971ba1 — merge of fix/wind-correction
```

## 5. Counts снова не сходятся со статусами

Перенос `CONFIRMED_P2` из P2-A в P2-B не уменьшает число `CONFIRMED_P2`.

В corrected waves перечислены как P2:

- AT-01;
- CM-01;
- CG-01;
- REC-01;
- REC-02;
- CM-02;
- CM-03.

Это семь confirmed P2 IDs, если статусы не меняются. `TEST-CG-02` — test gap, а не отдельный production P2 defect.

Пересчитать counts из единой machine-readable таблицы всех IDs. Для каждого ID должна быть ровно одна итоговая classification. Wave placement хранить в отдельной колонке и не смешивать с severity/classification.

## 6. P2-A readiness

После этих редакций разрешается подготовить implementation task только для:

1. `P2-AT-01` — monotonic clock; anomalous-dt policy должна учитывать nominal loop `time.sleep(0.5)` и retry pause `1.0s`. Не выбирать threshold без тестового обоснования.
2. `P2-CM-01` — finite/None guard с сохранением previous phase; `on_ground=True` должен работать даже при missing numeric values.
3. `TEST-CG-02` — direct tests без изменения gateway policy/default.

CM-02, CM-03, CG-01, REC-01 и REC-02 не реализовывать до решений P2-B.

## Требуемый ответ

```text
STATUS: COMPLETED_NO_CHANGES
CM02_EXECUTABLE_PROBE: <command + raw output>
CM02_CORRECTED_MATRIX: <table>
CM03_EXECUTABLE_PROBE: <command + raw output>
CM03_CORRECTED_TABLE: <table>
GATEWAY_REPO_WIDE_SEARCH: <exact results>
GATEWAY_CORRECTED_INVENTORY: <exact lines>
WIND_ATTRIBUTION: RESOLVED_BY_3971ba1 / fix/wind-correction
FINAL_ID_TABLE: <one row per ID>
FINAL_COUNTS: <derived from table>
P2_A: AT-01, CM-01, TEST-CG-02
P2_B: CG-01, REC-01, REC-02, CM-02, CM-03
CODE_CHANGED: no
COMMIT_CREATED: no
PR_CREATED: no
```

## Запреты

- Не менять код.
- Не создавать ветку/commit/PR.
- Не очищать пользовательские artifacts.
- Не начинать implementation или Pass B.
