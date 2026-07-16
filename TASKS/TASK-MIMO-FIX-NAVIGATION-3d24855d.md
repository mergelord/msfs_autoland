# TASK-MIMO-FIX-NAVIGATION-3d24855d

## Цель

Исправить оставшиеся подтверждённые дефекты `modules/navigation.py` после уже смёрженных PR #5 и PR #6. Задача относится к safety-critical навигационной геометрии VOR/NDB и синтетической глиссады.

Это отдельная волна. Не смешивать её с P2-эшелоном и Pass B.

## Репозиторий и база

- Репозиторий: `zhuk-mou-1/msfs_autoland`
- Рабочий каталог: `C:\BAT\msfs_autoland`
- Обязательный base SHA: `3d24855d32f857cb22b6f36e2e9defc815340302`
- Ветка: `fix/navigation-core`
- Целевая ветка PR: `master`

Перед началом:

1. `git fetch origin`
2. Подтвердить, что `origin/master` точно указывает на base SHA выше.
3. Подтвердить чистое tracked-дерево. Локальная папка `TASKS/` может оставаться untracked и не должна попасть в коммит.
4. Запустить базовый `pytest tests/ -q` и записать фактический baseline. Не подменять его ожидаемым числом из старых отчётов.
5. Если `origin/master` уже ушёл с указанного SHA или baseline красный не только из-за известного CI `lint-ruff`, остановиться со статусом `STOPPED_ON_GATE`.

## Важная рекалибровка старого аудита

Не реализовывать старые пункты механически. На текущем base уже закрыты:

- старый NAV-02: `calculate_landing_distance(ground_speed=0)` — исправлено PR #5 и покрыто тестом;
- Finding 3 Wave 1: защита деления на `cos(latitude)` в `calculate_glideslope_intercept_point()` и `calculate_runway_beacons()` — исправлено PR #6.

Эти участки не переписывать, кроме минимальной совместимой адаптации, если она объективно нужна для фиксов ниже. Старые тесты не удалять и не ослаблять.

---

# Обязательные исправления

## NAV-F1 — неверная геометрия `should_start_descent()`

### Подтверждённый дефект

Текущий код вычисляет профиль через скалярное `distance_to_intercept`. После прохождения точки перехвата расстояние до неё снова растёт. В результате `ideal_altitude` может увеличиваться по мере приближения к порогу, статус может стать `LOW`, а downstream `SyntheticGlidepath.compute_target_vs()` способен вернуть `0.0` и остановить снижение.

Простая замена на `intercept_distance - distance_to_intercept` недостаточна: скалярная дистанция не различает положение до/после intercept и ошибается при cross-track offset.

### Требуемое поведение

1. Профиль после перехвата рассчитывать по положению относительно порога ВПП, а не по расстоянию до точки intercept.
2. Использовать signed along-track геометрию вдоль оси финального курса либо эквивалентный математически доказанный метод.
3. В `calculate_glideslope_intercept_point()` разрешено добавить в возвращаемый словарь неизменяемые геометрические данные, необходимые downstream: координаты порога и курс ВПП. Существующие ключи и их смысл сохранить.
4. До intercept идеальная высота должна оставаться на уровне `intercept_altitude_agl` и не инициировать ложное снижение только из-за бокового смещения.
5. Между intercept и порогом `ideal_altitude_agl` должна монотонно уменьшаться к нулю по мере продвижения к порогу.
6. После порога результат должен быть ограничен физически осмысленным диапазоном; отрицательную требуемую AGL-высоту не возвращать.
7. Cross-track offset не должен превращаться в ошибочное движение профиля назад/вверх.
8. Сохранить контракт ключей результата `should_start_descent()` и совместимость с `SyntheticGlidepath`.
9. Все вычисляемые публичные числовые значения должны быть finite. Для неfinite/некорректной геометрии выбрать явный fail-closed контракт, залогировать причину и покрыть тестом.

### Обязательные тесты

Минимум:

- точка до intercept: профиль удерживает intercept altitude;
- точно в intercept;
- 75%, 50%, 25% пути от intercept к порогу: монотонное уменьшение ideal altitude;
- около порога: ideal altitude близка к 0, а не к высоте intercept;
- после порога: нет отрицательной высоты и NaN/inf;
- тот же along-track progress с небольшим cross-track offset даёт близкую высоту профиля;
- regression-тест реального дефекта: после прохождения intercept `status`/`should_descend` не блокирует корректное продолжение снижения как `LOW` из-за расстояния до старой точки;
- downstream-тест через реальный `SyntheticGlidepath.compute_target_vs()` либо ближайший реальный production path: корректный профиль после intercept не возвращает ложный `0.0` только из-за NAV-F1.

Для ключевого regression-теста показать red-without-fix на base SHA.

## NAV-F2 — смешение outbound radial и inbound final course в VOR/NDB

### Подтверждённый дефект

`calculate_vor_approach()` вычисляет:

- `bearing_to_station` — inbound bearing от самолёта к станции;
- `current_radial = bearing_to_station + 180` — outbound radial от станции;
- затем сравнивает `current_radial` с `config.final_approach_course`, который используется как inbound курс захода.

Самолёт, находящийся точно на inbound final course, может получить ошибку около 180°, ложный `on_course=False` и неверный intercept heading. `calculate_ndb_approach()` делегирует сюда же, поэтому дефект затрагивает оба типа захода.

### Требуемое поведение

1. Явно разделить outbound radial (для observability/совместимости) и inbound course error (для управления).
2. Сохранить возвращаемый ключ `current_radial` с его прежней outbound-семантикой.
3. `cross_track_error`, `on_course` и `recommended_heading` должны строиться из согласованной inbound-величины и `final_approach_course`.
4. Угловая ошибка должна быть signed и нормализована в `[-180, +180]` через единый helper `angle_difference()`.
5. Не менять публичный формат результата без необходимости.
6. Подтвердить знаки левее/правее числовыми probes, а не только mock-asserts.

### Обязательные тесты

- точное совпадение inbound bearing и final course: ошибка около 0°, `on_course=True`;
- противоположный outbound radial не создаёт ложные 180°;
- wrap 359°/0° в обе стороны;
- симметричные отклонения слева/справа дают противоположные знаки и корректные intercept headings;
- NDB-путь наследует исправленное поведение;
- red-without-fix для сценария «точно на inbound course, но старый код возвращает около 180°».

## NAV-F3 — перезаписываемое и потенциально аварийное вычисление высоты приводов

### Подтверждённый дефект

В `calculate_runway_beacons()` первый сложный расчёт `outer_altitude_agl` немедленно перезаписывается простой физически понятной формулой. Несмотря на перезапись, выражение выполняется и при некорректном `glideslope_angle`/нулевой дистанции способно делить на ноль либо распространять NaN/inf.

### Требуемое поведение

1. Удалить первое перезаписываемое выражение полностью.
2. Оставить один источник истины: `distance_nm * tan(angle) * 6076.12` после валидации.
3. Валидировать как минимум:
   - finite latitude/longitude/heading/elevation;
   - finite и строго положительный реалистичный `glideslope_angle`;
   - finite и неотрицательные `outer_distance_nm`/`inner_distance_nm`;
   - осмысленный порядок приводов (`outer_distance_nm >= inner_distance_nm`).
4. Для конфигурационной ошибки использовать явный единообразный контракт. Предпочтение: `ValueError` до создания объектов с NaN/inf. Перед выбором проверить production callers; если существующий жизненный цикл требует другого контракта, описать это в отчёте и реализовать эквивалентный fail-closed вариант.
5. Нормальное поведение и PR #6 pole guard сохранить.

### Обязательные тесты

- штатные 3°/5 NM/1 NM дают ожидаемые finite высоты;
- `glideslope_angle`: 0, отрицательное, NaN, +inf;
- distances: отрицательное, NaN, +inf;
- outer < inner;
- нулевая допустимая distance, если после анализа она сознательно разрешена, не вызывает деление на ноль;
- near-pole regression-тест PR #6 остаётся зелёным.

## NAV-F4 — wrap-баг `check_beacon_passage()`

### Подтверждённый дефект

Текущий `course_error = normalize_angle(current_heading - expected_course)` возвращает диапазон `[0, 360)`. Например, фактическое отклонение `-1°` превращается в `359°`, из-за чего `course_ok=False`.

Подсистема приводов сейчас выглядит не подключённой к production loop; это не отменяет дефект helper-а, но в этой задаче запрещено отдельно подключать её к runtime.

### Требуемое поведение

1. Рассчитывать signed shortest-angle error через `angle_difference()` в диапазоне `[-180, +180]`.
2. Сохранить смысл знака в логах/нарушениях.
3. Не менять прочие правила altitude/speed/status и не подключать beacon subsystem к `main.py`.

### Обязательные тесты

- current=359°, expected=0° → error около -1°, course_ok=True при tolerance 3–5°;
- current=1°, expected=0° → +1°;
- current=0°, expected=359° → +1°;
- отклонение за пределами tolerance остаётся нарушением;
- остальные altitude/speed violations не меняются.

---

# Необязательная чистка только при нулевом риске

Старый NAV-06 отмечал дублирование wind helpers. Не проводить рефакторинг ветровой математики в этой задаче. Допускается только удалить очевидно недостижимое/перезаписываемое выражение NAV-F3. Любое объединение с `WindCorrection` — отдельная будущая задача.

# Разрешённый scope

Production:

- `modules/navigation.py`
- минимально `modules/synthetic_glidepath.py` только если без этого невозможно сохранить корректный контракт NAV-F1; сначала попытаться обойтись без изменения production consumer-а.

Tests:

- `tests/test_navigation.py`
- существующий или новый целевой тестовый файл для `SyntheticGlidepath`.

Не трогать:

- `main.py`;
- `modules/wind_correction.py`;
- `modules/approach_phases.py`;
- `modules/safety_guard.py`;
- CI/config/docs/architecture snapshot;
- старые тесты PR #5/#6, кроме строго необходимого расширения без ослабления assertions.

Если необходим выход за scope — остановиться и запросить решение, не расширять diff самостоятельно.

# Требования к качеству

1. Для каждого NAV-F1..F4 — отдельный regression-тест, который красный без соответствующего production-фикса.
2. Не писать тесты, повторяющие формулу реализации без проверки наблюдаемого поведения.
3. Не использовать только `MagicMock` для геометрических дефектов: нужны реальные числовые coordinates/probes.
4. Все углы и единицы документировать в коде/тестах: inbound/outbound, degrees, NM, ft AGL.
5. Не ослаблять существующие assertions и не удалять тесты.
6. `pytest tests/ -q` должен пройти полностью.
7. Запустить `ruff check` только на изменённых Python-файлах. Известное pre-existing падение полного `lint-ruff` на текущем master не маскировать и не исправлять широким форматированием в этой ветке.
8. Запустить `python -m py_compile` на изменённых production-файлах.
9. Один содержательный коммит поверх точного base SHA; без merge master внутрь feature-ветки.

# Обязательный self-review перед push

Проверить:

- `git diff --check`;
- `git status --short`;
- `git diff --stat <base>...HEAD`;
- полный список изменённых файлов;
- отсутствие `TASKS/`, generated reports, caches и architecture snapshot в коммите;
- отсутствие новых публичных breaking changes;
- finite outputs и wrap boundaries;
- red-without-fix evidence для четырёх дефектов.

# Git/PR

1. Создать ветку `fix/navigation-core` от точного base SHA.
2. После зелёных тестов сделать один коммит.
3. Push ветки и открыть PR в `master`.
4. Не мерджить PR самостоятельно. Ждать независимого diff-review.

Рекомендуемый заголовок PR:

`fix(navigation): correct glidepath and inbound-course geometry`

# Формат отчёта

Сохранить локально, не коммитить:

`TASKS/REVIEWS/FIX-NAVIGATION-3d24855d.md`

В ответе вернуть:

- `STATUS: COMPLETED_AND_PUSHED | COMPLETED_NOT_PUSHED | STOPPED_ON_GATE | APPLY_FAILED`
- base SHA, branch, commit SHA, parent SHA;
- URL PR;
- точный список изменённых файлов;
- таблицу NAV-F1..F4: root cause → fix → regression test;
- числовые probes для NAV-F1, NAV-F2 и NAV-F4;
- red-without-fix evidence;
- полный результат `pytest tests/ -q`;
- результаты targeted ruff и `py_compile`;
- `git diff --check`;
- известные остаточные риски;
- подтверждение: PR не смёржен.

## Критерий приёмки

Задача принимается только после независимой проверки diff-а и тестов. Заявление `all tests passed` без точного SHA, parent, состава diff и red-without-fix не считается достаточным.
