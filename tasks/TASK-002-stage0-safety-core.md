# TASK-002 — Stage 0: Safety Core, Control Ownership и Replay-тесты

**Проект:** `mergelord/msfs_autoland`  
**Исполнитель:** MiMo Code  
**Постановщик / независимый верификатор:** Notion AI  
**Приоритет:** P0 — не добавлять новые возможности до завершения  
**Допустимый стиль работы:** небольшие логически разделённые коммиты; новые тесты обязательны.

---

## 0. Цель и жёсткие границы

Система управляет виртуальным самолётом, поэтому «команда была отправлена» **не равна** «управление получено». Цель Stage 0 — устранить известные дефекты safety-контуров, формализовать владение каналами управления и создать офлайн replay-набор, который доказывает критические инварианты без MSFS, SimConnect, vJoy, MobiFlight или сети.

### Результат Stage 0

После работы должны быть доказаны тестами следующие свойства:

1. Новый заход после предыдущего successful takeover или go-around начинается с полностью чистого состояния.
2. Провал hard safety check **не может** отключить AP/A/T и не может завершить takeover.
3. Успешный takeover требует наблюдаемого подтверждения: AP действительно выключен; управление не объявляется захваченным только по факту отправки команды.
4. ILS takeover срабатывает при **пересечении** высоты `DH + 50 ft`, а не только если один snapshot попал в узкое окно.
5. При оказании ниже DH без подтверждённого takeover система уходит на второй круг/дизармится — не продолжает flare вслепую.
6. В каждый момент один канал (roll, pitch, throttle) имеет ровно одного владельца. Внешнее vJoy-управление не смешивается с AP-командами того же канала.
7. Единицы длины ВПП не являются неявным `int`: интерфейс явно выражает `*_ft` или `*_m`, и тесты ловят ошибочные смешения.

### Не входит в Scope

Не добавлять RNAV, rollout, autobrake, новые самолёты, новые аэропорты, графический функционал, облачные API, реальный WASM/vJoy-драйвер и массовый рефакторинг GUI.

---

## 1. Правила работы

1. Работать от свежего `master` в отдельной ветке, например `task-002-stage0-safety-core`.
2. До изменений изучить **фактический** код и существующие тесты. Если этот документ расходится с актуальным состоянием — не молча подгонять: зафиксировать расхождение в отчёте.
3. Не менять публичное поведение без теста, который доказывает необходимость изменения.
4. Новые production-классы не должны импортировать `pytest`.
5. Тесты обязаны быть офлайн и детерминированными: не подключаться к MSFS, не требовать установленный vJoy/MobiFlight, не читать пользовательский `config/personal*.json`.
6. Не писать в отчёте «tests/mypy/ruff OK» без полного сырого вывода реально выполненных команд.
7. Не пушить до подтверждения владельца. В каждом коммите префикс: `TASK-002:`.

---

## 2. Карта затрагиваемых модулей

### Основные production-модули

| Модуль | Изменение |
|---|---|
| `main.py` | Граница жизненного цикла захода: создать метод сброса per-approach состояния; вызывать его при старте и после abort. Не раздувать `main.py` новой логикой — только orchestration. |
| `modules/autopilot_takeover.py` | Превратить takeover в проверяемую state machine: hard checks блокируют действия; подтверждение AP/A/T; пересечение высот; timeout на monotonic clock. |
| `modules/approach_phases.py` | Использовать переход по пересечению высоты; hard guard ниже DH без confirmed takeover; не слать competing команды. |
| `modules/control.py` | При необходимости добавить минимальные методы **readback** статусов AP/A/T через уже существующий telemetry/SimConnect слой. Не вводить самолёт-специфичную логику сюда. |
| `modules/aircraft_adapter.py` | Только если нужен унифицированный readback для кастомных профилей: `get_autopilot_state()` / `get_autothrottle_state()`. Fallback должен быть явно определён. |
| `modules/control_ownership.py` **(новый)** | Малый чистый модуль, который вычисляет разрешённого владельца каждого канала. Никаких вызовов SimConnect/vJoy внутри. |
| `modules/types.py` или новый `modules/units.py` | Явные поля/типы длины ВПП и валидаторы единиц. |

### Основные тесты

Создать или дополнить:

```text
tests/
├── conftest.py
├── fakes.py
├── test_approach_lifecycle.py
├── test_takeover_safety.py
├── test_ils_takeover_crossing.py
├── test_control_ownership.py
├── test_runway_units.py
└── replay/
    ├── test_nominal_ils.py
    ├── test_missed_dh_window.py
    ├── test_stale_or_failed_takeover.py
    └── fixtures/
        ├── ils_nominal.jsonl
        ├── ils_crosses_takeover_window.jsonl
        ├── ils_below_dh_without_takeover.jsonl
        └── unsafe_bank_at_takeover.jsonl
```

Если в репозитории уже есть иной тестовый layout — сохранить его стиль, но покрыть все перечисленные сценарии.

---

# 3. Рабочие пакеты

## WP-0 — Базовый тестовый каркас и fakes

### Цель

Сделать тесты независимыми от внешних библиотек и реального симулятора.

### Изменения

Создать `tests/fakes.py` (или эквивалент) с минимальными spy/fake-объектами:

```python
class FakeControl:
    calls: list[tuple[str, object]]
    autopilot_master: bool
    autothrottle_active: bool

    def set_autopilot_master(self, enabled: bool) -> None: ...
    def set_heading_hold(self, enabled_or_heading): ...
    def set_altitude_hold(self, enabled: bool) -> None: ...
    def set_airspeed_hold(self, enabled: bool | float): ...
    def set_vertical_speed_hold(self, enabled: bool): ...
    def set_throttle(self, value: float): ...
    def read_autopilot_state(self) -> bool: ...
    def read_autothrottle_state(self) -> bool: ...

class FakeAircraftAdapter:
    # Конфигурируемые подтверждения/отказы.
    # Нужен для теста custom-aircraft path.
    ...

class FakeVJoy:
    calls: list[tuple[str, object]]
    enabled: bool
    ...
```

Fake не должен дублировать production algorithm; его задача — запомнить команды и выдать заранее установленный observed state.

### Критерии приёмки

- Тест может создать `AutopilotTakeover` и выполнить его без импорта/инициализации SimConnect.
- Spy хранит последовательность calls; тест умеет доказать «никакой команды на отключение AP не было».

---

## WP-1 — Жизненный цикл захода: сброс состояния

### Дефект

`start_approach()` задаёт фазу, но не вызывает `AutopilotTakeover.reset()` и не сбрасывает `takeover_initiated`. После completed takeover следующий заход в одном процессе не может инициировать новый takeover: `should_initiate_takeover()` возвращает False при `status.completed=True`.

### Изменения

**Файл:** `main.py`

1. Добавить небольшой идемпотентный метод, например:

```python
def _reset_approach_session_state(self) -> None:
    self.takeover_initiated = False
    self.autopilot_takeover.reset()
    self._ils_info_logged = False
    self.autothrottle.reset()  # только если метод существует/нужен
    self.flare_controller.reset()  # аналогично
    self.stabilized_monitor.reset()
    # Сбросить только state, относящийся к конкретному заходу.
    # Не рвать подключение к MSFS, профили и connection monitor.
```

2. Вызвать его до создания `InitialPhaseState` в `start_approach()`.
3. Убедиться, что `execute_go_around()`/`stop_approach()` не оставляют опасную комбинацию `running=False`, но `takeover_initiated=True`. Достаточно гарантировать сброс на следующем `start_approach`; если добавляется сброс при stop — документировать, почему это безопасно.
4. Не сбрасывать конфигурацию выбранного захода (`approach_config`) без явного запроса пользователя.

### Тесты: `tests/test_approach_lifecycle.py`

1. **`test_second_approach_resets_completed_takeover`**
   - создать систему с подменёнными зависимостями;
   - выставить completed takeover, `takeover_initiated=True`, `_ils_info_logged=True`;
   - вызвать `start_approach()`;
   - проверить: `completed=False`, `in_progress=False`, `takeover_initiated=False`, `_ils_info_logged=False`, фаза INITIAL.
2. **`test_go_around_then_start_is_clean`**
   - смоделировать незавершённый/завершённый takeover;
   - выполнить go-around с fake control;
   - стартовать новый заход;
   - проверить чистый takeover state.
3. **`test_reset_preserves_approach_configuration_and_connection`**
   - удостовериться, что `approach_config`, `control`, `telemetry` не переинициализируются/не теряются.

---

## WP-2 — Hard safety gates для takeover

### Дефект

`AutopilotTakeover.perform_takeover()` собирает `checks`, логирует провал и всё равно отключает AP/A/T и объявляет controls acquired.

### Изменения

**Файл:** `modules/autopilot_takeover.py`

1. Разделить проверки на:
   - **hard / abort**: самолёт на земле; unsafe attitude; вышел за допустимый safety envelope; ниже высоты, где разрешён takeover (если применимо);
   - **wait / retry**: скорость/высота ещё не стабилизировались, но есть время ждать.
2. Добавить явное поле статуса, например:

```python
failure_reason: str = ""
waiting_for: tuple[str, ...] = ()
```

Не обязательно сохранять именно эти названия, но причина должна быть машинно проверяема, а не только в строке лога.

3. Поведение:
   - hard fail: `status.failed=True`, причина заполнена; **не вызывать** `_disengage_autopilot`, `_disengage_autothrottle`, `_acquire_controls`;
   - retryable fail: оставить `in_progress=True`, не отключать AP/A/T, вернуть status и ждать следующего snapshot;
   - all checks pass: только тогда переходить к командной последовательности.
4. Время для timeout измерять `time.monotonic()`, не `time.time()`.
5. Не менять policy: кто именно вызывает go-around. Модуль takeover сообщает fail надёжно; phase/orchestrator принимает решение и выполняет go-around ровно один раз.

### Тесты: `tests/test_takeover_safety.py`

1. **`test_unsafe_bank_blocks_takeover_without_commands`**
   - bank = 31°;
   - `perform_takeover()`;
   - `failed=True`, причина содержит unsafe attitude;
   - `FakeControl.calls` не содержит отключения AP, A/T или control acquisition.
2. **`test_on_ground_blocks_takeover_without_commands`**.
3. **`test_unstable_speed_waits_without_disengaging_ap`**
   - скорость отличается от baseline более чем на tolerance;
   - статус in_progress/waiting, но не failed (если выбран retry policy);
   - AP не отключался.
4. **`test_all_checks_pass_starts_command_sequence`**
   - безопасный snapshot;
   - удостовериться, что попытка AP/A/T begin действительно началась.
5. **`test_timeout_uses_monotonic_clock`**
   - не проверять реальными sleep;
   - внедрить clock callable или monkeypatch `time.monotonic`;
   - показать, что переход за timeout делает status failed.

---

## WP-3 — Подтверждённое получение управления

### Дефект

`_disengage_autopilot()` считает AP выключенным после отправки команды, а `_acquire_controls()` вообще ничего не подтверждает и всегда ставит `controls_acquired=True`.

### Изменения

**Файлы:** `modules/autopilot_takeover.py`, при необходимости `modules/control.py`, минимально `modules/aircraft_adapter.py`.

1. Ввести минимальный интерфейс readback. Предпочтительный путь:

```python
# control.py / adapter.py
get_autopilot_engaged() -> bool | None
get_autothrottle_engaged() -> bool | None
```

- `False` = наблюдаемо выключен;
- `True` = наблюдаемо включён;
- `None` = состояние невозможно прочитать.

2. После команды выключения AP/A/T не ставить флаг завершения немедленно.
3. В следующих итерациях `perform_takeover()` читать observed state:
   - AP выключен наблюдаемо → `autopilot_disengaged=True`;
   - AP всё ещё включён → ждать до timeout;
   - readback unavailable → takeover **не должен** объявляться verified. Можно поддержать строго определённый degraded policy только через явный config flag `allow_unverified_takeover=False` по умолчанию.
4. `controls_acquired` разрешено ставить True лишь когда:
   - AP и A/T observed off (или явно задокументированный verified adapter mode);
   - выбран control owner для pitch/roll/throttle;
   - не было ошибки выдачи первой safe command.
5. Не делать “test wiggle” реальными управляющими отклонениями в этом Stage: это может быть небезопасно и самолёт-специфично. На этом этапе proof = readback режима + успешная команда безопасного neutral/hold input.

### Тесты: `tests/test_takeover_safety.py`

1. **`test_sent_disengage_command_is_not_verified_takeover`**
   - fake принимает команду, но readback возвращает `True`;
   - `autopilot_disengaged=False`, `completed=False`, `controls_acquired=False`.
2. **`test_takeover_completes_only_after_readback_off`**
   - первый tick: AP on; второй tick: AP off and AT off;
   - только на втором tick `completed=True`.
3. **`test_unknown_readback_fails_closed_by_default`**
   - readback `None`;
   - takeover не completed; статус отражает unverified state.
4. **`test_adapter_readback_is_used_before_generic_fallback`**
   - custom adapter объявляет readback;
   - проверить порядок вызовов и отсутствие неуместного generic fallback.

---

## WP-4 — ILS crossing detection и нижний DH guard

### Дефект

Текущая проверка запуска takeover только при текущей высоте `(DH, DH+50]`. Один пропущенный telemetry tick может перескочить окно. После прохождения DH система не имеет жёсткого запрета продолжать посадку без confirmed takeover.

### Изменения

**Файлы:** `modules/autopilot_takeover.py`, `modules/approach_phases.py`.

1. В `AutopilotTakeover` хранить последнюю валидную высоту (предпочтительно radio height для flare):

```python
self._previous_radio_height: float | None
```

Либо передавать `previous_radio_height` явно из phase state. Выбрать один владелец history, не дублировать состояние в обоих классах.

2. Добавить метод с чистой семантикой, например:

```python
def crossed_takeover_height(
    previous_height_ft: float | None,
    current_height_ft: float,
    decision_height_ft: float,
) -> bool:
    ...
```

Условие должно срабатывать при переходе сверху вниз через `DH+50`. Первый snapshot внутри или ниже trigger height тоже должен обрабатываться консервативно.

3. Сделать policy явной:
   - выше threshold: ждать;
   - crossing threshold: стартовать takeover;
   - ниже DH без `status.completed`: hard fail `MISSED_TAKEOVER_BELOW_DH`;
   - ниже DH с completed takeover: разрешить Landing/flare flow.
4. Выбрать единый источник высоты для этого решения: если radio altitude доступна — использовать её; если нет, documented fallback на AGL. В логах писать, какой источник использован.
5. При отсутствующей/устаревшей высоте не принимать решение “можно продолжать”; fail closed.

### Тесты: `tests/test_ils_takeover_crossing.py`

Использовать DH = 200 ft.

1. **`test_crossing_dh_plus_50_starts_takeover`**
   - snapshots: 270 → 244;
   - takeover должен стартовать, хотя итоговый snapshot не находится в старом диапазоне `(200, 250]`? Он находится, да. Добавить также 270 → 190 ниже.
2. **`test_large_step_across_entire_window_starts_or_aborts_safely`**
   - snapshots: 270 → 190;
   - система не должна “молча ничего не делать”; допустимы только два document-обоснованных результата: успела начать takeover на crossing event либо немедленно failed/go-around ниже DH. Никогда `Landing` без completed takeover.
3. **`test_first_snapshot_below_dh_without_takeover_fails_closed`**.
4. **`test_below_dh_with_completed_takeover_is_allowed`**.
5. **`test_radio_height_is_preferred_over_baro_agl`**
   - AGL и radio altitude намеренно расходятся;
   - решение следует radio height.
6. **`test_stale_height_fails_closed`** — если реализуется timestamp в snapshot.

---

## WP-5 — Владение control channels: исключить смешение AP / vJoy / external A/T

### Дефект

На FINAL одновременно могут выполняться `set_heading_hold`, `set_vertical_speed` (AP/SimConnect) и прямые aileron/elevator inputs через vJoy. Для тяги при `is_stable=False` после внешнего значения может отправляться `control.set_throttle(0.5)`. Это создаёт гонку двух владельцев одного канала.

### Изменения

**Новый чистый файл:** `modules/control_ownership.py`

Минимальная модель:

```python
from dataclasses import dataclass
from enum import Enum

class ControlOwner(Enum):
    NONE = "none"
    AIRCRAFT_AP = "aircraft_ap"
    EXTERNAL = "external"

@dataclass(frozen=True)
class ControlOwnership:
    roll: ControlOwner
    pitch: ControlOwner
    throttle: ControlOwner
```

И чистая функция/класс planner, получающий как минимум:

- текущую phase;
- confirmed takeover state;
- `use_vjoy` / readiness vJoy;
- `use_autothrottle` / external A/T state;
- aircraft capabilities (если уже доступны).

### Обязательная policy Stage 0

| Условие | Roll | Pitch | Throttle |
|---|---|---|---|
| До confirmed takeover | AIRCRAFT_AP | AIRCRAFT_AP | AIRCRAFT_AP или уже установленный aircraft A/T |
| FINAL, takeover ещё не подтверждён | AIRCRAFT_AP | AIRCRAFT_AP | выбранный единственный текущий owner |
| External flare после confirmed takeover + vJoy ready | EXTERNAL | EXTERNAL | EXTERNAL **или** AIRCRAFT_AP, но ровно один |
| External mode без vJoy | NONE (не посылать прямые команды) | NONE | выбранный owner |
| Go-around / abort | не посылать residual external vJoy-команды; ownership сброшен к безопасной стратегии |

Конкретная стратегическая деталь (например, удерживать aircraft A/T при external flare) допустима, но должна быть единообразна и покрыта тестом.

### Встраивание

1. В `FinalPhaseState._control_aircraft()` сначала получить ownership.
2. Если owner roll/pitch = `EXTERNAL`, не слать одновременно AP `heading_hold` / `vertical_speed` команды по соответствующему каналу.
3. Если owner = `AIRCRAFT_AP`, не слать vJoy aileron/elevator commands.
4. В `_control_throttle()` вычислить одно окончательное значение и применить **один раз** через owner. Убрать последовательность “сначала calculated throttle, затем 0.5”.
5. При нестабильном PID выбрать и документировать одну safety policy: `hold_last_safe`, `bounded_fallback`, либо `disarm + go-around` по высоте. В тесте доказать отсутствие двойной команды.

### Тесты: `tests/test_control_ownership.py`

1. **`test_unconfirmed_takeover_keeps_ap_as_roll_pitch_owner`**.
2. **`test_confirmed_external_flare_uses_vjoy_without_ap_pitch_roll_commands`**.
3. **`test_no_vjoy_means_no_direct_pitch_roll_commands`**.
4. **`test_each_channel_has_exactly_one_owner`** — параметризовать все supported combinations.
5. **`test_unstable_autothrottle_sends_exactly_one_throttle_command_per_tick`**.
6. **`test_go_around_clears_external_ownership`**.

Тесты должны проверять фактический список `FakeControl.calls` / `FakeVJoy.calls`, а не только ownership object.

---

## WP-6 — Явные единицы длины ВПП

### Дефект

В README `runway_length=8000` обозначена как футы, а `AutopilotTakeover.get_recommended_takeover_point()` принимает параметр `runway_length_m` и сравнивает с 1500. Это создаёт возможность тихой ошибки в расчётах.

### Изменения

1. Выбрать один из вариантов:

**Вариант A (минимальный):** переименовать все соответствующие границы API в явные `runway_length_ft` / `runway_length_m`, конвертировать в одном именованном месте.

**Вариант B (лучше):** маленькие frozen dataclass types:

```python
@dataclass(frozen=True)
class RunwayLength:
    meters: float

    @classmethod
    def from_feet(cls, feet: float) -> "RunwayLength": ...

    @property
    def feet(self) -> float: ...
```

2. Внутренний критерий short runway обязан использовать одну выбранную единицу и иметь константу с единицей в названии:

```python
SHORT_RUNWAY_THRESHOLD_M = 1500.0
```

3. Обновить docstrings и config loading. Не делать скрытых heuristic guesses “если >5000, наверное футы”. Ошибочные данные должны валидироваться/отклоняться явно.

### Тесты: `tests/test_runway_units.py`

1. **`test_8000_ft_is_not_interpreted_as_8000_m`**.
2. **`test_short_runway_threshold_is_consistent_in_meters`**.
3. **`test_feet_to_meters_conversion`** (несколько boundary cases).
4. **`test_invalid_nonpositive_runway_length_is_rejected`**.
5. **`test_takeover_recommendation_receives_explicit_unit`**.

---

## WP-7 — Минимальный replay harness

### Цель

Запускать safety-сценарии как последовательность snapshots без MSFS. Это не замена реальному полёту; это регрессионная сетка для логики.

### Формат fixture

JSON Lines, один snapshot на строку. Минимальный пример:

```json
{"t": 0.0, "position": {"altitude_agl": 270, "radio_height": 270, "on_ground": false}, "attitude": {"bank": 0, "pitch": 2.5, "heading_magnetic": 270}, "speed": {"airspeed_indicated": 140, "vertical_speed": -700}}
{"t": 0.5, "position": {"altitude_agl": 190, "radio_height": 190, "on_ground": false}, "attitude": {"bank": 0, "pitch": 2.5, "heading_magnetic": 270}, "speed": {"airspeed_indicated": 140, "vertical_speed": -700}}
```

Может быть иной формат, если существующая telemetry abstraction требует другое. Но fixture не должна быть нечитабельным pickle/binary blob.

### Harness

Создать test-only runner, например `tests/replay_runner.py`, который:

1. Читает fixture;
2. Передаёт каждый snapshot в phase/takeover logic;
3. Использует fakes для контроллеров;
4. Собирает transitions, status и commands;
5. Позволяет тесту проверить инварианты.

Не создавать второй production state machine в тестах. Runner должен тонко вызывать production methods.

### Обязательные replay tests

1. `ils_nominal.jsonl` — crossing trigger → confirmed takeover → разрешённый landing transition.
2. `ils_crosses_takeover_window.jsonl` — 270 → 190 ft; нет silent continuation без confirmed ownership.
3. `ils_below_dh_without_takeover.jsonl` — первая запись уже ниже DH; abort/fail-closed.
4. `unsafe_bank_at_takeover.jsonl` — bank 31°; ни AP/A/T command, ни completion.

---

# 4. Порядок реализации

Строго соблюдать порядок, потому что каждый шаг создаёт проверяемую основу следующему:

1. **WP-0**: test fakes.
2. **WP-1**: reset lifecycle + tests.
3. **WP-2**: hard safety gates + tests.
4. **WP-3**: readback-verified takeover + tests.
5. **WP-4**: crossing + DH guard + tests.
6. **WP-5**: ownership planner + integration tests.
7. **WP-6**: units + tests.
8. **WP-7**: replay fixtures/harness + scenario tests.

После каждого WP запускать релевантный тестовый файл прежде, чем идти дальше. Не делать единый огромный неразборчивый коммит.

---

# 5. Definition of Done

Задача считается выполненной **только если**:

- [ ] Все WP реализованы либо чётко помечены BLOCKED с технической причиной.
- [ ] Нет вызова AP/A/T disengage после hard safety failure.
- [ ] `controls_acquired=True` нельзя получить без observed AP/A/T readback или явной opt-in degraded policy (по умолчанию выключенной).
- [ ] Нельзя оказаться ниже DH без completed takeover и продолжить normal landing flow.
- [ ] За один control tick нет конфликтующих owner-команд одного канала.
- [ ] Повторный заход после go-around проходит тест сброса state.
- [ ] Все новые tests проходят офлайн.
- [ ] Отчёт содержит полный raw output команд.
- [ ] Отчёт включает diffstat, перечень изменённых файлов, SHA коммитов и известные остаточные ограничения.

---

# 6. Команды верификации

Сначала определить существующий test runner (`pytest`, `unittest`, и т.д.) по репозиторию. Затем выполнить и приложить **полный вывод**:

```bash
python -m pytest -q tests/test_approach_lifecycle.py \
  tests/test_takeover_safety.py \
  tests/test_ils_takeover_crossing.py \
  tests/test_control_ownership.py \
  tests/test_runway_units.py \
  tests/replay/
```

Затем весь suite:

```bash
python -m pytest -q
```

Минимальная статическая проверка (если инструмент реально установлен):

```bash
python -m compileall -q main.py modules tests
```

Если доступен `ruff`/`mypy`, запускать лишь с реальным конфигом репозитория и приложить output. Не заявлять о них без запуска.

Перед коммитом:

```bash
git diff --check
git status --short
git diff --stat
```

После коммита:

```bash
git show --stat --oneline HEAD
git status --short
```

---

# 7. Отчёт для верификатора

Создать файл:

```text
tasks/reports/TASK-002-stage0-safety-core-report.md
```

Структура:

```markdown
# TASK-002 — отчёт

## Статус
DONE | PARTIAL | BLOCKED

## Решения по дизайну
- safety policy: ...
- degraded/readback policy: ...
- control ownership table: ...
- единицы: ...

## Изменённые файлы
- `path`: кратко что и почему

## Коммиты
- `<sha> TASK-002: ...`

## Тестовая матрица
| Инвариант | Тест(ы) | Результат |
|---|---|---|

## Сырой вывод команд
### <команда>
```text
<полный stdout/stderr>
```

## Остаточные ограничения
- Реальные MSFS/vJoy/MobiFlight smoke tests НЕ выполнены / выполнены: ...
- Что нужно проверить в живом симуляторе: ...

## Отклонения от задания
- ...
```

---

# 8. Важное напоминание

Это симуляторный проект, не реальная авиационная система. Ценность Stage 0 — не “сделать вид, что самолёт гарантированно сядет”, а построить систему, которая **не продолжает молча управлять при неопределённом состоянии**, воспроизводимо доказывает safety-инварианты офлайн и даёт понятный след для проверки в MSFS.
