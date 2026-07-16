# TASK-MIMO-IMPLEMENT-P2-A-9FBF652

## Решение Checkpoint A

`CHECKPOINT_A_ACCEPTED_WITH_LEDGER_CORRECTIONS`

Разрешена реализация только Wave P2-A:

1. `P2-AT-01` — monotonic PID timing + fail-safe anomalous-dt handling;
2. `P2-CM-01` — defensive finite validation в `update_flight_phase()`;
3. `TEST-CG-02` — прямое покрытие `CommandGateway` без изменения production policy.

P2-B, P3 и Pass B в этой задаче запрещены.

## Репозиторий и база

- Repository: `zhuk-mou-1/msfs_autoland`
- Required base/master SHA: `9fbf652f94f38b9de0f799a298d8194db89d22a3`
- Branch: `fix/p2a-contract-preserving`
- Baseline: `346 passed`, 1 warning.

Перед работой:

```bash
git fetch origin
git rev-parse origin/master
git status --short
pytest tests/ -q
```

Локальный основной checkout содержит pre-existing modified architecture PNG и untracked audit artifacts. Не удалять, не reset и не включать их в commit. Создать чистый изолированный worktree/branch от точного base SHA. Если base изменился — `STOPPED_ON_GATE`.

## Неблокирующие ledger corrections

Финальный аудит принят по существу, но итоговые counts исправить в implementation report:

- `CONFIRMED_P2 = 7`;
- `CONFIRMED_P3 = 13`, а не 12 — перечисленный список содержит 13 IDs;
- `RESOLVED = 4`, а не 5 — `WIND-01`, `REC-03`, `REC-04`, `REC-05`; `REC-06` является `TEST_GAP_ONLY`, не resolved;
- `DUPLICATE = 2`;
- `UNPROVEN = 5`;
- `TEST_GAP_ONLY = 3`;
- `DESIGN_NOTE = 1`.

Gateway inventory caveats:

- команды внутри `main.execute_go_around()` находятся внутри единственного production `SAFETY source_scope` и не должны считаться unscoped;
- adapter получает gateway как `control`, поэтому вызов «через adapter» не автоматически bypass; классифицировать по фактическому внутреннему пути;
- `aileron_compensation.py` и `rudder_compensation.py` исторически изолированы и не являются production-reachable callsites без нового подключения.

Эти corrections вне code scope; достаточно отразить их в отчёте.

---

# FIX P2-AT-01 — Monotonic PID timing

## Подтверждённый дефект

`AutothrottleController.activate()` и `calculate_throttle()` используют `time.time()`. Отрицательный/аномально большой `dt` искажает integral/derivative. Номинальный основной цикл использует `time.sleep(0.5)`, retry path — `time.sleep(1.0)`.

## Требуемый контракт

1. Использовать monotonic clock для interval timing.
2. Сделать clock детерминированно инъецируемым в тестах без изменения существующих production callsites.
3. Первый нормальный кадр после `activate()` использует реальный monotonic interval.
4. Для invalid/anomalous `dt`:
   - non-finite;
   - `dt <= 0`;
   - слишком большой интервал после pause/stall;

   нельзя интегрировать ошибку по всему интервалу и нельзя создавать derivative spike.
5. При аномальном `dt` сохранить базовую/P-коррекцию, но отключить I/D update для этого кадра эквивалентом `effective_dt = 0.0`; обновить временную/previous-error точку так, чтобы следующий нормальный кадр восстановился без kick.
6. Выдать throttled/обычный warning с наблюдаемым `dt`; не падать.
7. Не менять:
   - PID sign convention;
   - anti-windup bounds;
   - throttle clamps/rate limit;
   - wind/drag calculation;
   - engine-failure paths.

## Порог anomalous large dt

Не хардкодить необоснованное значение внутри метода. Добавить именованный параметр конфигурации с документированным default, учитывающим nominal 0.5 s loop и 1.0 s retry. Рекомендуемый initial default: `max_pid_dt_seconds = 2.0`, но до кода подтвердить probe/тестом, что штатный retry interval не будет отброшен. Если предлагается иное значение — обосновать.

Валидация конфигурации: finite и `> 0`; invalid config должен fail fast при создании контроллера.

## Clock injection

Допустимый дизайн:

```python
AutothrottleController(..., clock: Callable[[], float] = time.monotonic)
```

Сохранить backward compatibility всех текущих positional/keyword callers. Предпочтительно сделать `clock` keyword-only, если это не ломает существующий API.

## Обязательные тесты

1. Clock source monotonic/injected; тест без реального sleep.
2. Nominal sequence `0.5s → 0.5s` обновляет I/D как раньше.
3. Retry-like interval около `1.0–1.5s` остаётся допустимым при выбранном default.
4. `dt == 0` → I/D не меняются, finite output.
5. `dt < 0` → I/D не меняются, finite output, warning.
6. `dt = NaN/inf` через injected clock/controlled state → fail-safe.
7. `dt > max_pid_dt_seconds` → I/D не интегрируются, finite output, warning.
8. Следующий нормальный кадр после anomaly восстанавливает PID без derivative spike.
9. activate/reset lifecycle не сохраняет stale timestamp.
10. Red-without-fix evidence минимум для wall-clock/negative-or-large interval поведения.

---

# FIX P2-CM-01 — Defensive flight-phase inputs

## Подтверждённый дефект

`ConnectionMonitor.update_flight_phase()` напрямую сравнивает `altitude_agl` и `vertical_speed`. `None` вызывает TypeError; NaN/inf дают некорректный hold/ветку без явного контракта.

## Требуемый контракт

1. Если `on_ground is True`, немедленно установить `FlightPhase.GROUND`, даже если altitude/VS отсутствуют или non-finite.
2. Если `on_ground is False` и `altitude_agl` или `vertical_speed` не finite real number:
   - не бросать исключение;
   - сохранить previous `current_phase`;
   - залогировать warning с безопасным представлением inputs;
   - вернуть без дальнейшей классификации.
3. Не менять текущую `elif`-таблицу и boundary semantics CM-02. CM-02 — P2-B owner decision.
4. `ground_speed` пока не использовать и не удалять — это P3/design debt вне scope.
5. Не менять switching/metrics logic.

## Числовая проверка

Не считать `bool` допустимым числом, несмотря на наследование от `int`. Допустимы только finite `int/float` real values.

## Обязательные тесты

1. `on_ground=True` + altitude/VS `None` → GROUND, no exception.
2. `on_ground=True` + NaN/inf → GROUND.
3. `on_ground=False` + altitude `None`, NaN, +inf, -inf → previous phase preserved.
4. То же для vertical_speed.
5. Строки, bool и произвольный object → previous phase preserved.
6. Валидные boundary cases остаются byte-for-behavior совместимыми с probe Checkpoint A, минимум:
   - 499/+501 → TAKEOFF;
   - 499/0 → LANDING;
   - 500/-1 → APPROACH;
   - 500/0 → hold previous;
   - 1500/+501 → CLIMB;
   - 3000/-1 → hold previous;
   - 10000/all representative VS → hold previous;
   - 10001/-501 → DESCENT.
7. Warning проверяется без требования хрупкого полного текста.
8. Red-without-fix evidence для `None` TypeError.

---

# TEST TEST-CG-02 — Direct CommandGateway coverage

## Scope

Добавить отдельный тестовый модуль, предпочтительно:

```text
tests/test_command_gateway.py
```

Production `modules/command_gateway.py`, default `_SOURCE`, channel map и authorization policy **не менять**.

## Обязательные тесты

1. AP owner + unscoped actuator сейчас разрешён — зафиксировать текущий compatibility contract.
2. EXTERNAL owner + unscoped actuator отклонён `CommandRejected`.
3. EXTERNAL owner + explicit EXTERNAL scope разрешён.
4. AP owner + explicit EXTERNAL scope отклонён.
5. SAFETY scope разрешает command независимо от owner.
6. Scope восстанавливается после нормального выхода.
7. Scope восстанавливается после исключения внутри context manager.
8. Nested scopes восстанавливаются LIFO.
9. Guarded closure, сохранённая до/вне scope, выполняет `_authorize()` в момент вызова и не bypass-ит policy.
10. ContextVar isolation — детерминированный тест с отдельными contexts/threads без sleep/race assumptions.
11. Configuration/navigation/autopilot channels покрыты минимум по одному representative method.
12. Неизвестный readback/helper method делегируется без actuator authorization.

Использовать минимальный fake raw control с call ledger и ownership provider. Не подключать SimConnect/vJoy.

---

# Scope и файлы

Ожидаемые production-файлы:

- `modules/autothrottle.py`;
- `modules/connection_monitor.py`.

Ожидаемые tests:

- существующий или новый autothrottle test module;
- существующий или новый connection-monitor test module;
- `tests/test_command_gateway.py`.

Любой иной production-файл — `STOPPED_ON_SCOPE_GATE` до изменения.

## Запреты

Не делать в этом PR:

- CM-02 phase redesign;
- CM-03 active/passive metrics changes;
- CommandGateway default/source migration;
- EngineFailureDetector hardening или integration;
- ILS autothrottle activation;
- P3 cleanup;
- architecture snapshot update;
- global lint cleanup;
- Pass B.

## Процесс

1. Создать чистый worktree/branch от exact base.
2. Сначала добавить red tests и показать failures на base.
3. Реализовать минимальные fixes.
4. Запустить targeted tests.
5. Запустить full suite.
6. Выполнить static checks.
7. Один логический commit допустим; PR не мержить.

## Обязательные проверки

```bash
pytest <targeted test files> -q
pytest tests/ -q
ruff check modules/autothrottle.py modules/connection_monitor.py <changed test files>
python -m py_compile modules/autothrottle.py modules/connection_monitor.py
git diff --check
git status --short
git diff --stat 9fbf652f94f38b9de0f799a298d8194db89d22a3...HEAD
```

GitHub CI после push:

- test 3.12;
- test 3.13;
- mypy;
- bandit;
- radon;
- validate architecture snapshot;
- отдельно классифицировать pre-existing `lint-ruff` и `check-architecture-freshness`.

## Выходной отчёт

```text
TASKS/REVIEWS/P2-A-IMPLEMENTATION-9FBF652.md
```

Локальный task/report artifacts не коммитить.

## Формат ответа

```text
STATUS: COMPLETED_AND_PUSHED | COMPLETED_NOT_PUSHED | STOPPED_ON_GATE | STOPPED_ON_SCOPE_GATE
BASE_SHA: 9fbf652f94f38b9de0f799a298d8194db89d22a3
BRANCH: fix/p2a-contract-preserving
COMMIT_SHA: <full>
PARENT_SHA: <full>
PR_URL: <url or none>
CHANGED_FILES: <exact>
AT01_DESIGN: <clock injection, threshold, anomaly policy>
CM01_CONTRACT: <exact>
CG02_TESTS: <list>
RED_WITHOUT_FIX: <commands + raw failures>
TARGETED_TESTS: <raw summary>
FULL_TESTS: <raw summary>
RUFF: <raw>
PY_COMPILE: <raw>
DIFF_CHECK: <raw>
CI_CHECKS: <full list>
LEDGER_COUNTS: P2=7, P3=13, RESOLVED=4, DUPLICATE=2, UNPROVEN=5, TEST_GAP=3, DESIGN_NOTE=1
REPORT_PATH: TASKS/REVIEWS/P2-A-IMPLEMENTATION-9FBF652.md
MERGED: no
```
