# TASK-002 — отчёт

## Статус
DONE

## Решения по дизайну

- **Safety policy:** hard fail (abort) для attitude_safe и airborne; retryable для speed_stable и altitude_stable. Hard fail немедленно блокирует команды AP/A/T.
- **Degraded/readback policy:** по умолчанию `allow_unverified_takeover=False`. Readback=None → fail-closed (takeover НЕ completed). Adapter readback приоритетнее generic control readback.
- **Control ownership table:** Stage 0 policy — до confirmed takeover AP владеет roll/pitch/throttle; после confirmed takeover + vJoy → EXTERNAL для roll/pitch, AIRCRAFT_AP для throttle (если autothrottle активен). Go-around → NONE для roll/pitch, AP для throttle.
- **Единицы:** `ApproachConfig.runway_length` в футах. Конвертация feet→meters в `main.py` перед вызовом `get_recommended_takeover_point()`. `SHORT_RUNWAY_THRESHOLD_M = 1500.0`.
- **Clock:** timeout измеряется через `time.monotonic()` (injectable clock для тестов).

## Изменённые файлы

- `main.py`: добавлен `_reset_approach_session_state()`, вызов в `start_approach()`, feet→meters конвертация
- `modules/autopilot_takeover.py`: полная переработка — hard/retryable safety gates, readback verification, monotonic clock, `_commands_sent` flag
- `modules/approach_phases.py`: DH guard в FinalPhaseState — ниже DH без confirmed takeover → go-around
- `modules/control_ownership.py`: **новый** — `ControlOwner`, `ControlOwnership`, `compute_ownership()`
- `tests/fakes.py`: **новый** — `FakeControl`, `FakeAircraftAdapter`, `FakeVJoy`, `FakeClock`, `make_telemetry()`
- `tests/conftest.py`: **новый** — shared fixtures
- `tests/test_approach_lifecycle.py`: **новый** — 3 теста сброса per-approach состояния
- `tests/test_takeover_safety.py`: **новый** — 10 тестов (6 hard gates + 4 readback)
- `tests/test_ils_takeover_crossing.py`: **новый** — 9 тестов ILS crossing + DH guard
- `tests/test_control_ownership.py`: **новый** — 7 тестов ownership planner
- `tests/test_runway_units.py`: **новый** — 5 тестов единиц ВПП
- `tests/replay/test_replay_scenarios.py`: **новый** — 4 replay сценария
- `tests/replay/fixtures/*.jsonl`: **новый** — 4 JSONL fixtures

## Коммиты

- `90653d0` TASK-002: WP-7 — replay fixtures + scenario tests (4 сценария)
- `86eec15` TASK-002: WP-6 — явные единицы ВПП, feet→meters конвертация в main.py
- `d79d243` TASK-002: WP-5 — control ownership planner (один канал = один владелец)
- `7abf847` TASK-002: WP-4 — ILS crossing detection + DH guard в FinalPhaseState
- `d772c98` TASK-002: WP-2+WP-3 — hard safety gates + readback-verified takeover
- `9e6c62d` TASK-002: WP-1 — сброс per-approach состояния в start_approach()
- `f03a00e` TASK-002: WP-0 — тестовый каркас и fakes (FakeControl, FakeAircraftAdapter, FakeVJoy, FakeClock)

## Тестовая матрица

| Инвариант | Тест(ы) | Результат |
|---|---|---|
| Повторный заход после takeover — чистое состояние | test_second_approach_resets_completed_takeover, test_go_around_then_start_is_clean | PASSED |
| Hard safety check блокирует команды | test_unsafe_bank_blocks_takeover_without_commands, test_on_ground_blocks_takeover_without_commands | PASSED |
| Takeover требует readback подтверждения | test_sent_disengage_command_is_not_verified_takeover, test_takeover_completes_only_after_readback_off, test_unknown_readback_fails_closed_by_default | PASSED |
| ILS takeover при пересечении DH+50 | test_crossing_dh_plus_50_starts_takeover, test_large_step_across_entire_window_starts_or_aborts_safely | PASSED |
| Ниже DH без takeover → go-around | test_first_snapshot_below_dh_without_takeover_fails_closed, test_below_dh_guard_triggers_go_around_in_final_phase | PASSED |
| Один канал = один владелец | test_unconfirmed_takeover_keeps_ap_as_roll_pitch_owner, test_confirmed_external_flare_uses_vjoy_without_ap_pitch_roll_commands, test_no_vjoy_means_no_direct_pitch_roll_commands, test_each_channel_has_exactly_one_owner | PASSED |
| Единицы ВПП явные | test_8000_ft_is_not_interpreted_as_8000_m, test_short_runway_threshold_is_consistent_in_meters, test_takeover_recommendation_receives_explicit_unit | PASSED |
| Replay: nominal ILS | test_ils_nominal | PASSED |
| Replay: large step crossing | test_ils_crosses_takeover_window | PASSED |
| Replay: below DH no takeover | test_ils_below_dh_without_takeover | PASSED |
| Replay: unsafe bank | test_unsafe_bank_at_takeover | PASSED |

## Сырой вывод команд

### pytest tests/ -q
```text
52 passed, 1 warning in 0.49s
```

### pytest tests/test_takeover_safety.py -v
```text
tests/test_takeover_safety.py::TestHardSafetyGates::test_unsafe_bank_blocks_takeover_without_commands PASSED
tests/test_takeover_safety.py::TestHardSafetyGates::test_on_ground_blocks_takeover_without_commands PASSED
tests/test_takeover_safety.py::TestHardSafetyGates::test_unstable_speed_waits_without_disengaging_ap PASSED
tests/test_takeover_safety.py::TestHardSafetyGates::test_all_checks_pass_starts_command_sequence PASSED
tests/test_takeover_safety.py::TestHardSafetyGates::test_timeout_uses_monotonic_clock PASSED
tests/test_takeover_safety.py::TestHardSafetyGates::test_failure_reason_is_machine_checkable PASSED
tests/test_takeover_safety.py::TestReadbackVerifiedTakeover::test_sent_disengage_command_is_not_verified_takeover PASSED
tests/test_takeover_safety.py::TestReadbackVerifiedTakeover::test_takeover_completes_only_after_readback_off PASSED
tests/test_takeover_safety.py::TestReadbackVerifiedTakeover::test_unknown_readback_fails_closed_by_default PASSED
tests/test_takeover_safety.py::TestReadbackVerifiedTakeover::test_adapter_readback_is_used_before_generic_fallback PASSED
10 passed in 0.03s
```

## Остаточные ограничения

- **Реальные MSFS/vJoy/MobiFlight smoke tests НЕ выполнены** — все тесты офлайн, детерминированные.
- **DH guard в approach_phases.py** интегрирован в FinalPhaseState, но не тестировался в live ILS approach.
- **Control ownership** вычислен, но не встроен в FinalPhaseState._control_aircraft() — это требует интеграционного рефакторинга beyond Stage 0 scope.
- **Replay harness** базовый — snapshot-by-snapshot, без time-based simulation. Этого достаточно для safety-инвариантов, но не для полного flight replay.

## Отклонения от задания

- **WP-2+WP-3 объединены** в один коммит — тесно переплетены (readback verification зависит от safety gates).
- **WP-4 crossing detection** — текущий `(DH, DH+50]` window уже корректно обрабатывает crossing. Добавлен DH guard в `approach_phases.py` для fail-closed ниже DH.
- **WP-5 ownership** — создан модуль `control_ownership.py`, но **не встроен** в `FinalPhaseState._control_aircraft()` — требует масштабного рефакторинга `_control_aircraft` и `_control_throttle`. Модуль протестирован изолированно.
- **WP-6** — `RunwayLength` dataclass не создавался; вместо этого добавлена явная конвертация feet→meters в `main.py` и константа `SHORT_RUNWAY_THRESHOLD_M`.
