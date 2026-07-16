TASK: FIXPACK-GO-e2cc5b5 — устранение блокеров аудита (минимум для GO)

BASE: master @ e2cc5b5a25f5e1d29d60f5b9304961ff12e425b2 (221/0)
BRANCH: fix/go-blockers
MODE: read/write, только перечисленные файлы

SCOPE (согласованный fix-pack v2, сверка Claude+MiMo):

F1 · Контракт approach_data (P0)
  modules/ils_navigation.py:
    - calculate_ils_approach(): добавить в return
      distance_to_station (геометрический расчёт через calculate_distance_to_threshold,
      НЕ dme_distance), cross_track_error (= -loc_dev['degrees']), on_course (= loc_dev['on_course'])
    - calculate_loc_approach(): те же три ключа + required_altitude
      (источник — synthetic glidepath: calculate_required_altitude(distance,
      glideslope_angle, runway_elevation))
    - В докстринге зафиксировать: cross_track_error для ILS/LOC в ГРАДУСАХ (у VOR — nm)
  modules/approach_phases.py (consumer, fail-closed дефолты):
    - distance = approach_data.get('distance_to_station', 999.0)  # НЕ 0 — гейт близости
    - required_alt = approach_data.get('required_altitude')       # None → гейт не проходить
    - cross_track = approach_data.get('cross_track_error', 0.0)
    - on_course = approach_data.get('on_course', False)

F2 · ILS deadlock INTERMEDIATE→FINAL (P0)
  modules/approach_phases.py, IntermediatePhaseState.handle:
    - approach-type-aware гейт: ILS → переход в FINAL по on_localizer + distance<8
      БЕЗ требования status.completed (takeover инициируется в FINAL, окно DH — не трогать);
      non-ILS → прежняя логика (completed takeover)
    - Способ определения типа захода взять из фактического кода (approach_config /
      approach_type) — проверить атрибут, не гадать

F3 · execute_go_around: re-engage AP (P0)
  main.py:
    - В SAFETY-scope ПЕРВОЙ командой: self.control.set_autopilot_master(True)
    - Реальная команда self.control.set_gear(False) (комментарий про positive climb
      убрать или реализовать проверку — не оставлять расхождение код/комментарий)

F4 · Error budget → go-around (P0)
  main.py, ветка consecutive_errors >= 3:
    - if self.autopilot_takeover.status.completed: self.execute_go_around()
      else: self.stop_approach()
    - Без дублирования stop_approach (go_around вызывает его сам)

F5 · Defensive telemetry в takeover (P0)
  modules/autopilot_takeover.py:
    - _save_initial_parameters(): критичные ключи (altitude, altitude_agl, airspeed)
      None → warning + return без сохранения (retry следующий тик)
    - _perform_safety_checks(): каждый отсутствующий канал → соответствующий
      check = False (fail-closed). НЕ подставлять 0.0. checks['airborne'] — одно
      присваивание, без дублей

F6 · G5 expansion (P1)
  modules/safety_guard.py: evaluate(..., has_vs=True, has_bank=True);
    G5 = not has_height or not has_airspeed or not has_vs or not has_bank
  main.py: передать has_vs/has_bank из фактических чтений speed/attitude

TESTS (обязательные, 15 шт. по согласованной таблице):
  tests/test_p0_p1_contract.py (расширить) — 4×F1
  tests/test_ils_phase_transition.py (new) — 3×F2
  tests/test_go_around.py (new) — 2×F3, 2×F4
  tests/test_takeover_defensive.py (new) — 2×F5
  tests/test_safety_guard_g5.py (new) — 2×F6

ACCEPTANCE:
  1. pytest tests/ = 236/0 (221 старых + 15 новых), полный вывод в отчёт
  2. Никаких изменений вне перечисленных файлов; поведение VOR/NDB не меняется
     (регрессия test_contract_vor_* зелёная)
  3. Отчёт: TASKS\REVIEWS\FIXPACK-GO-e2cc5b5.md — по каждому F: diff-фрагмент,
     тест(ы), результат
  4. Ветку fix/go-blockers запушить, master НЕ трогать до кросс-ревью
  5. TASKS\ не пушить

После пуша ветки я делаю независимое ревью диффа по API, затем merge.