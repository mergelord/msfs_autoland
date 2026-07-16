# AUDIT-PRESIM (Claude) — независимый аудит @ e2cc5b5

**Дата:** 2026-07-13 · **Коммит:** `e2cc5b5a25f5e1d29d60f5b9304961ff12e425b2` (master, 221/0 tests) · **Статус:** параллельно с локальным аудитом MiMo (AUDIT-PRESIM)

**Метод:** чтение исходников с GitHub (raw view, whitespace-нормализованный). Каждое контрактное несоответствие подтверждено цитатами **с обеих сторон контракта** (producer + consumer). Точные номера строк и byte-exact цитаты — сверить по локальному отчёту MiMo.

**Покрытие (полное):** main.py, approach_phases, autopilot_takeover, safety_guard, control_ownership, command_gateway, base_controller, flare_controller, stabilized_approach, autothrottle, connection_monitor (осн. часть), control, ils_navigation, wind_correction, navigation (ключевые ф-ции), telemetry (ключевые ф-ции), aircraft_adapter (readback/AP-команды), virtual_joystick (ключевые ф-ции), synthetic_glidepath (авторитетная копия v5).

**Покрытие (частичное/нет):** dme_navigation, wind_shear_detector, turbulence_detector, engine_failure_detector (только пороги), rudder/aileron_compensation, telemetry_recorder, thresholds_config, wasm_interface, gui.py, log-analysis. Полагаюсь на отчёт MiMo по этим модулям.

---

# Вердикт: NO-GO

До исправления AUD-01…AUD-04 боевое тестирование в симе не рекомендуется. ILS/LOC-заходы функционально сломаны выше FINAL; go-around после передачи управления, вероятно, не исполняется физически.

---

# P1 — блокеры

## AUD-01 · ILS/LOC: контрактное несоответствие approach_data → KeyError-цикл в INITIAL/INTERMEDIATE

- `ils_navigation.calculate_ils_approach()` возвращает ключи: `ils_available, localizer, glideslope, dme_distance, required_altitude, altitude_deviation, required_vs, corrected_heading, on_localizer, on_glideslope, stabilized` — **нет** `distance_to_station`, `cross_track_error`, `on_course`.
- `calculate_loc_approach()` возвращает только `loc_available, localizer, corrected_heading, on_localizer, stabilized` — **нет** даже `required_altitude`.
- При этом `InitialPhaseState.handle` и `IntermediatePhaseState.handle` обращаются к `approach_data['distance_to_station']`, `['cross_track_error']`, `['required_altitude']` **напрямую** (без `.get`).
- Маршрутизация в `main._calculate_approach_data`: как только `use_ils and ils.get('nav1_has_localizer')` — данные идут из `calculate_ils_approach`; LOC — **всегда** из `calculate_loc_approach`.
- **Следствие:** захват localizer в INITIAL/INTERMEDIATE → KeyError каждый тик → 3 подряд ошибки → `stop_approach()` (см. AUD-04). Только VOR/NDB-ветка (`calculate_vor_approach`) отдаёт полный набор ключей.
- Почему тесты зелёные: replay/юнит-тесты, судя по всему, гоняют FINAL/LANDING (где обращения защищённые), а не INITIAL/INTERMEDIATE с ILS-данными.

## AUD-02 · ILS: дедлок INTERMEDIATE → FINAL

- Переход в FINAL в `IntermediatePhaseState` требует `autopilot_takeover.status.completed` (иначе «Waiting for takeover completion…»).
- Но для ILS `should_initiate_takeover()` разрешает инициацию **только** в фазах FINAL/LANDING (окно DH+50).
- **Следствие:** takeover в INTERMEDIATE не инициируется → completed никогда не True → фаза не переходит в FINAL → DH-guard, flare, safety guard (FINAL-only) никогда не активируются. Даже без AUD-01 ILS-заход не доходит до FINAL.

## AUD-03 · execute_go_around при выключенном AP master

- После успешного takeover система **выключает** AP самолёта (`disengage_autopilot`).
- `execute_go_around()` шлёт `set_throttle(1.0)`, `set_vertical_speed(1500)` (события `AP_VS_HOLD`/`AP_VS_VAR_SET_ENGLISH`), `set_flaps(2)` — но **не включает AP master обратно** и не переходит на vJoy-управление тангажом.
- При AP master OFF события VS hold не управляют самолётом; vJoy центрируется (`center_all_axes`), тяга 100%.
- **Следствие:** go-around ниже DH = полный газ + неуправляемый тангаж. Это худший сценарий именно там, где go-around критичен.
- Затрагивает **все** типы заходов после takeover (VOR/NDB/LOC/ILS).

## AUD-04 · Error budget → stop_approach вместо go-around

- `execute_approach`: после 3 подряд исключений — `stop_approach()` (просто останавливает цикл и запись), **не** go-around, **не** возврат AP самолёту.
- После takeover это оставляет самолёт вообще без управляющего контура на малой высоте.
- В связке с AUD-01 (KeyError-цикл) достигается за ~3.5 с.
- Рекомендация: ниже FINAL/после takeover деградация должна быть fail-closed: go-around (с учётом фикса AUD-03) или re-engage AP самолёта.

---

# P2 — серьёзные

## AUD-05 · Safety guard слеп по VS/крену при потере каналов

- `SafetySnapshot.from_telemetry` дефолтит `vs`/`bank` в 0.0; main передаёт guard'у только `has_altitude/has_radio_height/has_airspeed`.
- G5 (missing data) покрывает высоту/скорость, но **не** VS/bank → при потере этих каналов G1 (sink rate) и G2 (bank) молча отключаются (fail-open).

## AUD-06 · Финальная проверка стабилизации не работает при DH < 200 ft

- `_check_final_stabilization`: go-around только если `not is_stabilized and radio_height > 200`.
- Для CAT II (DH=100) проверка на DH фактически пропускается. Если это осознанный «committed below 200» — задокументировать; иначе поправить порог.

## AUD-07 · FINAL/INITIAL/INTERMEDIATE: незащищённые обращения к телеметрии

- `telemetry.get_position()/get_speed()/...` при ошибке чтения возвращают `{}`; отдельные `aq.get()` могут вернуть `None`.
- `LandingPhaseState` читает защищённо (`.get` + явная проверка None), а FINAL/INITIAL/INTERMEDIATE — `telemetry['position']['altitude_agl']` напрямую → KeyError/TypeError → расход error budget (AUD-04).
- `_get_telemetry_with_monitoring` тоже: `position['altitude_agl']` напрямую, и `update_metrics(..., success=True)` безусловно (метрики не видят фактических сбоев чтения).

## AUD-08 · connection_monitor.update_flight_phase с None

- `altitude_agl < 1500` при `altitude_agl=None` → TypeError (main передаёт значения из телеметрии без проверки) → снова error budget.

---

# P3 — заметки

1. **AUD-09:** `flare_controller.update()` дефолтит `radio_height=0` (сам по себе fail-open), но фактический вызов из LANDING защищён проверками — латентно.
2. **AUD-10:** `navigation.calculate_landing_distance`: деление `headwind / ground_speed` → ZeroDivisionError при GS=0 (вызывается в FINAL-логировании).
3. **AUD-11:** autothrottle `dt` по `time.time()` (wall clock, не monotonic) — скачки при коррекции системного времени.
4. **AUD-12:** G1 guard: `abs(vs) > 1500` срабатывает и на набор высоты — консервативно, но имя «sink rate» вводит в заблуждение.
5. **AUD-13:** guard G3/G4 используют `config.approach_speed`, который после `_calculate_approach_speeds` = **VAPP** (не VREF): пороги смещены на ветровую надбавку.
6. **AUD-14:** `_maintain_glideslope`: деление на `flare_params['throttle']` (None при неактивном flare) — сейчас недостижимо (has_engine_failure=False в этой ветке), но хрупко.
7. **AUD-15:** CommandGateway: ContextVar по умолчанию AIRCRAFT_AP — код без `source_scope` проходит как AP. Приемлемо, но требует дисциплины.

---

# Что чисто

- **Readback-контур** (WP-3/FIX-1): `MSFSControl.get_autopilot_engaged/get_autothrottle_engaged` реализованы через `_aq`, adapter корректно отдаёт None → fallback; `_verify_readback` fail-closed (нет readback → takeover failed → go-around).
- **Autothrottle:** missing airspeed → hold current (не 0!), anti-windup, rate limit, clamps — образцово.
- **stabilized_approach:** FIX-P1-4 на месте, защищённые чтения, missing airspeed → skip (осознанный компромисс, частично прикрыт G5).
- **connection_monitor:** FIX-P1-3 (LANDING перед APPROACH) на месте.
- **control.py:** клампы входов (`_bounded_number`), валидация — хорошо.
- **wind_correction, ils_navigation (математика), virtual_joystick (P-контроллеры с лимитами)** — замечаний по существу нет.
- **execute_go_around** корректно использует SAFETY-scope гейтвея (сам механизм; проблема AUD-03 — в отсутствии re-engage AP).

---

# Сверка с MiMo

- Совпавшие находки → скорее всего реальные; расхождения разбирать по одной с byte-exact проверкой (урок P1-2).
- Особо прошу MiMo подтвердить локально: точные строки AUD-01 (обращения в Initial/IntermediatePhaseState), AUD-02 (гейт перехода + окно ILS в `should_initiate_takeover`), AUD-03 (тело `execute_go_around`), AUD-04 (ветка `consecutive_errors`).
- Мои line numbers приблизительные (raw view); семантика перепроверена перекрёстно по обеим сторонам каждого контракта.
