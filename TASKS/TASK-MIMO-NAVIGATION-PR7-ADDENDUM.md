# TASK-MIMO-NAVIGATION-PR7-ADDENDUM

## Статус ревью

`REQUEST_CHANGES`

PR: https://github.com/zhuk-mou-1/msfs_autoland/pull/7

Проверенный commit: `c4c8537eadcf72c0d2c86f23e2850d38769d556d`

Base: `3d24855d32f857cb22b6f36e2e9defc815340302`

Работать на той же ветке `fix/navigation-core`. PR не мержить.

## Блокер 1 — NAV-F1 всё ещё использует unsigned scalar distance

Текущая реализация объявлена как signed along-track, но фактически делает:

```python
distance_to_threshold = calculate_distance(current, threshold)
is_before_intercept = distance_to_threshold >= intercept_to_threshold
ideal_altitude = (
    intercept_altitude
    if is_before_intercept
    else distance_to_threshold * feet_per_nm
)
```

`calculate_distance()` возвращает неотрицательную Haversine-дистанцию. Это не signed along-track projection.

### Почему это блокирует merge

1. После пролёта порога scalar distance снова растёт.
2. Когда distance после порога становится больше `intercept_to_threshold`, код ошибочно классифицирует самолёт как находящийся до intercept и возвращает полную intercept altitude.
3. Cross-track offset входит в scalar distance и завышает профиль.
4. `vertical_deviation_dots` по-прежнему использует `distance_to_intercept`, которое после прохождения intercept растёт и не является расстоянием до порога вдоль final axis.
5. Тест `test_navf1_after_threshold_clamped_non_negative` проверяет только `>= 0`; значение `2000 ft` после порога тоже проходит этот тест, хотя является явной ошибкой.
6. Cross-track тест допускает отношение `0.5 < ratio < 2.0`, то есть разрешает почти двукратное искажение safety-critical профиля.

### Требуемое исправление

Рассчитать signed along-track coordinate относительно порога вдоль оси final approach course/runway heading.

Допустимый вариант — local tangent-plane projection:

- перевести delta latitude/longitude относительно threshold в NM;
- longitude масштабировать через `cos(reference_lat)` с существующей pole-защитой;
- спроецировать вектор threshold→aircraft на outbound runway axis либо эквивалентно на inbound final axis с документированным знаком;
- получить signed along-track distance: положительное значение на стороне захода до порога, `0` на пороге, отрицательное после порога;
- clamp profile distance в `[0, intercept_to_threshold_nm]`;
- `ideal_altitude = clamped_along_track_nm * feet_per_nm`;
- до intercept получается intercept altitude, после порога — строго `0.0`;
- vertical deviation считать относительно того же profile/along-track geometry, не `distance_to_intercept`.

Не использовать scalar Haversine distance как замену signed projection.

### Обязательные усиленные тесты

1. После порога на 0.1, 1 и 5 NM: `ideal_altitude_agl == 0` (с разумным числовым допуском), а не только `>= 0`.
2. До intercept на 0.1, 1 и 5 NM: высота удерживается на intercept altitude.
3. Одинаковый along-track progress с cross-track offsets 0, 0.5 и 2 NM: профильная высота совпадает в узком допуске, например `pytest.approx(..., rel=1e-3, abs=1.0)`.
4. Точки после порога не классифицируются как before-intercept независимо от удаления от порога.
5. Near-threshold vertical deviation использует distance/profile до threshold и остаётся finite.
6. Downstream `SyntheticGlidepath.compute_target_vs()` не получает ложный профиль после порога/при cross-track offset.

Показать red-without-addendum для как минимум теста после порога и строгого cross-track теста.

## Блокер 2 — NAV-F4 инвертировал знак course error

Helper реализован как:

```python
def angle_difference(angle1, angle2):
    diff = angle2 - angle1
```

Текущий вызов:

```python
angle_difference(current_heading, expected_course)
```

возвращает `expected - current`, тогда как прежний контракт выражения был `current - expected`, только без shortest-angle normalization.

Из-за этого:

- current=359, expected=0 сейчас даёт `+1`, требуется `-1`;
- current=1, expected=0 сейчас даёт `-1`, требуется `+1`;
- current=0, expected=359 сейчас даёт `-1`, требуется `+1`.

`course_ok` работает из-за `abs()`, но знак в observability/violations изменён на противоположный и не соответствует выданной спецификации.

### Требуемое исправление

Использовать:

```python
course_error = self.angle_difference(expected_course, current_heading)
```

Исправить тесты на ожидаемые знаки. Не менять helper глобально.

## Блокер 3 — NAV-F3 реализовал неполную валидацию

Текущий код валидирует только angle и distances. В задаче были обязательны finite-проверки:

- `runway_threshold_lat`;
- `runway_threshold_lon`;
- `runway_heading`;
- `runway_elevation`;
- `glideslope_angle`;
- обе distances.

Сейчас NaN/inf в координатах, heading или elevation может попасть в возвращаемые объекты и нарушает критерий finite outputs.

### Требуемое исправление

1. Добавить finite-validation всех перечисленных числовых входов до геометрических вычислений.
2. Валидировать физические диапазоны координат: latitude `[-90, 90]`, longitude в документированном допустимом диапазоне.
3. Нормализовать finite heading либо отклонять значение вне выбранного контракта; зафиксировать контракт тестом.
4. Добавить разумный верхний предел glideslope angle. Использовать диапазон, согласованный с существующей документацией модуля; экстремальные/физически бессмысленные углы не должны проходить молча.
5. Добавить parametrized tests для NaN/+inf/-inf по координатам, heading и elevation.

## Что уже принято

- Base/parent правильные.
- Scope ровно 2 файла — правильный.
- NAV-F2 исправляет основной outbound/inbound дефект; текущий подход можно оставить.
- Удаление мёртвого выражения NAV-F3 — правильное.
- NAV-F4 устранил false `course_ok=False` на wrap boundary, но требует коррекции знака.
- 324 tests и успешные test/mypy/bandit/radon checks подтверждают отсутствие широкой тестовой регрессии.
- Полный `lint-ruff` остаётся красным с двумя pre-existing annotations; targeted ruff изменённых файлов заявлен зелёным.

## Проверки после addendum

- `pytest tests/ -q`
- targeted tests NAV-F1/F3/F4
- `ruff check modules/navigation.py tests/test_navigation.py`
- `python -m py_compile modules/navigation.py`
- `git diff --check`

## Формат ответа

Вернуть:

- новый commit SHA и parent (`c4c8537...`);
- точный diff только addendum;
- результаты усиленных probes;
- red-without-addendum evidence;
- полный pytest;
- targeted ruff и py_compile;
- подтверждение, что PR #7 не смёржен.
