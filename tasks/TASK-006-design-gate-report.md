# DESIGN GATE REPORT — TASK-006

## Checkpoint A: Design Gate

---

### 1. Mode-Scope Matrix

| Режим | Guard активен | Причина |
|-------|--------------|---------|
| FINAL | **Да** | Критические нарушения до команд управления |
| INITIAL | Нет | Перехват курса, команды простые, нет DH/glideslope |
| INTERMEDIATE | Нет | Снижение до глиссады, takeover ещё не завершён |
| LANDING | Нет | Flare-контур — отдельная задача, не вмешиваться |
| COMPLETED | Нет | Заход завершён |
| IDLE | Нет | Заход не активен |

**ILS / LOC / VOR / NDB** — guard применим ко всем типам в фазе FINAL.

---

### 2. Текущий код — обязательная проверка

#### 2.1. Что делает StabilizedApproachMonitor

`stabilized_approach.py:77-199` — `check_stabilization()`:
- Speed deviation (±tolerance от Vref)
- Vertical speed (> max_vertical_speed)
- Glideslope deviation (в dots)
- Localizer deviation (в degrees)
- Bank angle (> max_bank_angle)
- Landing config (flaps ≥ 90%, gear ≥ 95%)

`stabilized_approach.py:201-262` — `check_continuous_monitoring()`:
- Critical speed violations (> Vref+20 or < Vref-10)
- Critical VS (> 1500 fpm)
- Critical bank (> 15°)
- Только если radio_height < 500ft

`stabilized_approach.py:264-284` — `should_go_around()`:
- Unstabilized below stabilization_height - 100ft
- go_around_required flag

#### 2.2. Почему это НЕ заменяет новый guard

Текущий монитор вызывается **ПОСЛЕ** команд управления:

```
FinalPhaseState.handle():
  _control_aircraft()      # ← команды ушли на актуаторы
  _control_throttle()      # ← команды ушли на актуаторы
  _check_stabilization()   # ← монитор работает ПОСЛЕ команд
```

(`approach_phases.py:277-284`)

На кадре violation команды normal approach-control **уже отправлены** в `_control_aircraft()` и `_control_throttle()`. Монитор может только обнаружить проблему и вызвать go-around на **следующем** кадре — а за текущий кадр самолёт получил опасную команду.

#### 2.3. Где новый guard должен стоять в production path

```
_execute_approach():
  data = get_telemetry()
  approach_data = _calculate_approach_data(data)  # includes LOC fail-closed
  _handle_phase(data, approach_data)

_handle_phase():
  if approach_data is None: return  # existing LOC fail-closed

  wind_data = wind_correction.apply_wind_corrections(...)

  # >>> NEW: Deterministic guard (FINAL only, before any commands) <<<
  if self.phase == ApproachPhase.FINAL:
      guard_result = self.safety_guard.evaluate(telemetry, approach_data, wind_data)
      if guard_result.decision == Decision.GO_AROUND:
          self.execute_go_around()
          return

  phase_state.handle(telemetry, approach_data, wind_data)
```

Guard стоит **после** wind correction (у него больше данных) и **перед** `phase_state.handle()` (до отправки команд).

#### 2.4. Как исключить двойной go-around

`execute_go_around()` вызывает `stop_approach()` (`main.py:432`), который:
- `self.running = False` — цикл `while self.running` завершается
- `self.phase = ApproachPhase.IDLE`
- `self.phase_state = None`

После `stop_approach()`:
- `_handle_phase()` не вызовется (нет phase_state)
- Guard не вызовется (phase != FINAL)
- Нет возможности повторного go-around

---

### 3. Classification Table — правила guard

| # | Правило | Порог | Единицы | Classification | Режимы | При отсутствии поля | Reason code | Ложный go-around? |
|---|---------|-------|---------|---------------|--------|-------------------|-------------|-------------------|
| G1 | Critical sink rate | > 1500 | fpm (abs(vertical_speed)) | **Hard fail** → GO_AROUND | FINAL (ILS/LOC/VOR/NDB) | `vertical_speed is None` → GO_AROUND | `CRITICAL_SINK_RATE` | Нет: штатный VS в FINAL = 600-900 fpm снижения. 1500+ = явная аномалия |
| G2 | Critical bank | > 15 | ° (abs(bank)) | **Hard fail** → GO_AROUND | FINAL (ILS/LOC/VOR/NDB) | `bank is None` → GO_AROUND | `CRITICAL_BANK` | Нет: в FINAL крен должен быть < 5°. 15° = потеря стабильности |
| G3 | Gross underspeed | < Vref - 15 | kt (airspeed_indicated) | **Hard fail** → GO_AROUND | FINAL (ILS/LOC/VOR/NDB) | `airspeed_indicated is None` → GO_AROUND | `GROSS_UNDERSPEED` | Нет: Vref-15 = существенно ниже глиссадной. Stall risk |
| G4 | Gross overspeed | > Vref + 25 | kt (airspeed_indicated) | **Hard fail** → GO_AROUND | FINAL (ILS/LOC/VOR/NDB) | `airspeed_indicated is None` → GO_AROUND | `GROSS_OVERSPEED` | Нет: Vref+25 = существенно выше. Runway overrun risk |
| G5 | Invalid critical telemetry | radio_height IS None OR airspeed IS None OR altitude_agl IS None | — | **Hard fail** → GO_AROUND | FINAL (ILS/LOC/VOR/NDB) |本身就是检查 | `INVALID_TELEMETRY` | Нет: без данных невозможно безопасно продолжать |

#### Почему именно эти правила (не больше)

- **G1 (sink rate)** — прямая опасность CFIT. 1500 fpm в 500ft AGL = 20 секунд до земли
- **G2 (bank)** — 15° в FINAL = потеря контроля. ICAO standard
- **G3/G4 (speed)** — stall или overrun. Пороги Vref-15/Vref+25 chosen to avoid nuisance trips at normal speed variations (±10kt)
- **G5 (telemetry)** — fail-closed: без данных нет безопасности

#### Что НЕ в guard (почему)

- **Glideslope deviation** — уже в StabilizedApproachMonitor. Guard будет дублировать
- **Localizer deviation** — уже в StabilizedApproachMonitor. Дублирование
- **Flaps/gear** — конфигурация меняется по высоте. Guard не должен знать height thresholds
- **Wind shear** — уже в WindShearDetector (history-based). Guard — single-frame, не может оценить trends
- **LOC signal loss** — уже в `_calculate_approach_data()` (TASK-005)
- **ILS signal loss** — уже в ILSNavigation
- **DH guard** — уже в `FinalPhaseState.handle()` (approach_phases.py:291-298)

---

### 4. Production-Path Trace до актуаторов

```
Main loop (_execute_approach):
  data = telemetry.get_all_data()                    # SimConnect read
  approach_data = _calculate_approach_data(data)      # NAV calculation
  _handle_phase(data, approach_data)

_handle_phase:
  wind_data = wind_correction.apply_wind_corrections(telemetry, approach_data, config)

  [NEW] Guard evaluation (pure, no side effects):
    snapshot = SafetySnapshot.from_telemetry(telemetry, approach_data, wind_data, config)
    result = safety_guard.evaluate(snapshot)

  [NEW] If result.decision == GO_AROUND:
    system.execute_go_around()  →  stop_approach()  →  running=False, phase=IDLE
    return  (no commands sent this frame)

  [EXISTING] phase_state.handle(telemetry, approach_data, wind_data):
    _control_aircraft()  →  control.set_heading_hold(), control.set_vertical_speed()
    _control_throttle()  →  autothrottle, control.set_throttle()
    _check_stabilization()  →  may call execute_go_around()
```

**Ключевой момент:** На кадре violation guard вызывает `execute_go_around()` **до** `_control_aircraft()` и `_control_throttle()`. Команды normal approach-control **не уходят**.

---

### 5. Proposed API / Component Structure

#### A. `SafetySnapshot` (read-only, typed)

```python
@dataclass(frozen=True)
class SafetySnapshot:
    """Immutable snapshot for guard evaluation. No control/system/vJoy references."""
    altitude_agl: float          # футы AGL (telemetry.position.altitude_agl)
    radio_height: float          # футы radio altimeter (telemetry.position.radio_height, fallback altitude_agl)
    airspeed_indicated: float    # узлы IAS (telemetry.speed.airspeed_indicated)
    vertical_speed: float        # fpm (telemetry.speed.vertical_speed)
    bank: float                  # degrees (telemetry.attitude.bank)
    phase: str                   # "FINAL" (из phase enum)
    approach_type: str           # "ILS"/"LOC"/"VOR"/"NDB" (из config.station.type)
    vref: float                  # узлы (из approach_config.approach_speed)

    @classmethod
    def from_telemetry(cls, telemetry: dict, approach_data: dict,
                       wind_data: dict, config: 'ApproachConfig') -> 'SafetySnapshot':
        ...
```

**Источники полей:**
- `altitude_agl` → `telemetry['position']['altitude_agl']` (футы)
- `radio_height` → `telemetry['position'].get('radio_height', altitude_agl)` (футы)
- `airspeed_indicated` → `telemetry['speed']['airspeed_indicated']` (узлы)
- `vertical_speed` → `telemetry['speed']['vertical_speed']` (fpm)
- `bank` → `telemetry['attitude']['bank']` (градусы)
- `vref` → `config.approach_speed` (узлы)

**Чего НЕТ в snapshot:**
- Нет control, vJoy, autothrottle, system, self
- Нет callback, methods, side effects
- `frozen=True` — immutable

#### B. `GuardDecision` (enum)

```python
class GuardDecision(Enum):
    CONTINUE = "CONTINUE"
    GO_AROUND = "GO_AROUND"

@dataclass(frozen=True)
class GuardResult:
    decision: GuardDecision
    reason: str           # reason code (e.g., "CRITICAL_SINK_RATE")
    details: dict         # optional: threshold vs actual values for logging
```

#### C. `ApproachSafetyGuard` (deterministic, pure)

```python
class ApproachSafetyGuard:
    """Deterministic safety guard. Pure evaluation, no actuators."""

    def __init__(self, config: ApproachConfig):
        self._config = config
        self._go_around_executed = False  # idempotence flag

    def evaluate(self, snapshot: SafetySnapshot) -> GuardResult:
        """Evaluate snapshot against all rules. Returns CONTINUE or GO_AROUND."""
        if self._go_around_executed:
            return GuardResult(GuardDecision.CONTINUE, "already_go_around", {})

        # G5: Invalid telemetry (first — before accessing fields)
        # G1: Critical sink rate
        # G2: Critical bank
        # G3: Gross underspeed
        # G4: Gross overspeed

        return GuardResult(GuardDecision.CONTINUE, "all_checks_passed", {})

    def reset(self):
        """Reset idempotence flag for new approach."""
        self._go_around_executed = False
```

**Ключевые свойства:**
- Pure function: snapshot → decision. No state mutation during evaluation.
- No network, LLM, time-of-day, free text
- Idempotent: once GO_AROUND executed, subsequent calls return CONTINUE
- Deterministic: same input → same output always

#### D. `LLMSupervisor` boundary (document-only for TASK-006)

```python
class LLMSupervisorRecommendation(Enum):
    MONITOR = "MONITOR"
    ADVISE_GO_AROUND = "ADVISE_GO_AROUND"
    UNAVAILABLE = "UNAVAILABLE"

@dataclass(frozen=True)
class LLMAdvisory:
    recommendation: LLMSupervisorRecommendation
    confidence: float  # 0.0-1.0, informational only
    reasoning: str     # for logging, NOT for control decisions
```

**Контракт:**
- Вход: `SafetySnapshot` + limited event window
- Выход: `LLMAdvisory` (enum + confidence + reasoning)
- **Никогда не вызывает актуаторы**
- **Не участвует в решении текущего кадра**
- **ADVISE_GO_AROUND → логируется, но НЕ приводит к execute_go_around()**
- Отдельный integration point (будущий TASK) может вызвать go-around только если deterministic guard тоже решил GO_AROUND

**Рекомендация по LLM boundary в TASK-006: НЕ включать в код.** Причины:
1. Контракт документирован — достаточно для следующего TASK
2. Без модели/HTTP/subprocess это мёртвый код
3. Добавляет complexity без testing value
4. Чистый deterministic guard проще верифицировать

---

### 6. Test Plan

| # | Тест | Тип | Production path | Что проверяем |
|---|------|-----|----------------|---------------|
| T1 | FINAL + critical sink rate (2000 fpm) | Integration | `_handle_phase()` → guard → `execute_go_around()` | Go-around вызван, `_control_aircraft()` НЕ вызван |
| T2 | FINAL + normal telemetry (700 fpm, 120kt, 3° bank) | Integration | `_handle_phase()` → guard = CONTINUE → `phase_state.handle()` | Guard не мешает normal path |
| T3 | Guard в INITIAL — critical sink rate | Unit | Guard evaluate() | Guard = CONTINUE (не активен в INITIAL) |
| T4 | Guard в INTERMEDIATE — critical bank | Unit | Guard evaluate() | Guard = CONTINUE (не активен в INTERMEDIATE) |
| T5 | Guard в LANDING — critical speed | Unit | Guard evaluate() | Guard = CONTINUE (не активен в LANDING) |
| T6 | ILS + normal FINAL | Neighbour | `_handle_phase()` → guard → full FinalPhaseState | ILS normal path не сломан |
| T7 | LOC + normal FINAL | Neighbour | `_handle_phase()` → guard → full FinalPhaseState | LOC normal path не сломан |
| T8 | VOR + normal FINAL | Neighbour | `_handle_phase()` → guard → full FinalPhaseState | VOR normal path не сломан |
| T9 | NDB + normal FINAL | Neighbour | `_handle_phase()` → guard → full FinalPhaseState | NDB normal path не сломан |
| T10 | Missing radio_height | Unit | Guard evaluate() | GO_AROUND with reason INVALID_TELEMETRY |
| T11 | Missing airspeed | Unit | Guard evaluate() | GO_AROUND with reason INVALID_TELEMETRY |
| T12 | Missing altitude_agl | Unit | Guard evaluate() | GO_AROUND with reason INVALID_TELEMETRY |
| T13 | Idempotence: second call after go-around | Unit | Guard evaluate() twice | Second call = CONTINUE |
| T14 | LLM UNAVAILABLE doesn't change flow | Unit | Guard evaluate() with UNAVAILABLE advisory | Deterministic decision unchanged |
| T15 | LLM ADVISE_GO_AROUND doesn't trigger go-around | Unit | Guard evaluate() with ADVISE_GO_AROUND | No execute_go_around called |
| T16 | Reason code in log (caplog) | Unit | Guard evaluate() → GO_AROUND | Logger contains reason code via `caplog`/`assertLogs` |
| T17 | Red-without-fix: remove guard from _handle_phase | Integration | Critical violation test WITHOUT guard | Test FAILS (no go-around) |
| T18 | Red-without-fix: remove phase gate in guard | Unit | Guard returns CONTINUE always | Phase-gate test FAILS |

#### Anti-simulator checks

- **T1:** Вызывает реальный `_handle_phase()`, проверяет что `execute_go_around()` вызван через spy FakeControl
- **T2:** Вызывает реальный `_handle_phase()`, проверяет что `set_heading_hold()` вызван (normal path)
- **T16:** Проверяет logger через `caplog`, НЕ через литерал в тесте

#### Red-without-fix proof

- **T17:** Убираем guard integration из `_handle_phase()` → critical-violation test должен покраснеть
- **T18:** Убираем phase gate (guard проверяет все фазы) → test на отсутствие go-around в INITIAL должен покраснеть

---

### 7. Risks

| Риск | Severità | Mitigation |
|------|----------|------------|
| **Двойной go-around** (guard + existing monitor) | Medium | Guard вызывает `stop_approach()`, which sets `running=False` and `phase_state=None`. After first go-around, no further evaluation occurs. |
| **Конфликт с StabilizedApproachMonitor** | Low | Guard runs BEFORE monitor. Different timing (pre- vs post-commands). Different thresholds (hard limits vs stabilization criteria). No overlap in rules. |
| **Конфликт с WindShearDetector** | Low | WindShearDetector uses history (10+ samples). Guard is single-frame. Different detection windows — no conflict. |
| **Конфликт с LOC fail-closed (TASK-005)** | Low | LOC signal loss handled in `_calculate_approach_data()` → returns None → `_handle_phase()` returns early. Guard never sees invalid LOC data. |
| **Конфликт с flare (LANDING phase)** | None | Guard explicitly NOT active in LANDING. No interference with flare controller. |
| **False positive go-around at normal approach** | Medium | Thresholds chosen conservatively: 1500 fpm (normal 600-900), 15° bank (normal < 5°), Vref-15/Vref+25 (normal ±10kt). |
| **Missing telemetry causing guard bypass** | High | G5: missing critical telemetry → GO_AROUND (fail-closed). Guard fails safe. |

---

### 8. Open Questions (Owner Decisions)

1. **Vref thresholds — Vref-15/Vref+25 or tighter?** Current choice: 15kt below / 25kt above Vref. More conservative would be Vref-10/Vref+20. Tradeoff: fewer false positives vs earlier detection. Need owner decision.

2. **Bank threshold — 15° or 10°?** 15° is ICAO standard for go-around. 10° is more conservative. 15° chosen to avoid nuisance trips during gusty conditions. Need owner decision.

3. **Radio height source — radio_height or altitude_agl?** Recommendation: use `radio_height` (actual radar altimeter) when available, fallback to `altitude_agl`. Radio height is more accurate near ground. Need owner confirmation.

4. **Guard in INTERMEDIATE phase?** Currently FINAL only. INTERMEDIATE has simpler control (heading + descent). Risk is lower. Recommendation: FINAL only for TASK-006, can extend later. Need owner decision.

---

### 9. GO / NO-GO Recommendation

**GO** — minimal implementation order:

1. **`SafetySnapshot`** — frozen dataclass, `from_telemetry()` factory
2. **`GuardDecision` + `GuardResult`** — enums + dataclass
3. **`ApproachSafetyGuard`** — `evaluate()` with 5 rules (G1-G5), `reset()`, idempotence flag
4. **Integration in `_handle_phase()`** — guard call before `phase_state.handle()`, FINAL only
5. **Tests T1-T18** — full coverage including red-without-fix

**NOT in scope for TASK-006:**
- LLM supervisor boundary (documented only)
- Guard in INITIAL/INTERMEDIATE/LANDING
- Glideslope/localizer rules (already in StabilizedApproachMonitor)
- Wind shear rules (already in WindShearDetector)

**Estimated complexity:** ~150 lines production + ~300 lines tests. Single module `modules/safety_guard.py`.
