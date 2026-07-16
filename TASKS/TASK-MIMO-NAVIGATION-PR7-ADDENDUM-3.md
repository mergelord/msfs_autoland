# TASK-MIMO-NAVIGATION-PR7-ADDENDUM-3

## Статус ревью

`REQUEST_CHANGES`

PR: https://github.com/zhuk-mou-1/msfs_autoland/pull/7

Проверенный head: `ac8f6cc1a379a0ce81cd7d002e6ddc61d50a6f9b`

Parent подтверждён: `0774c8b25015b4c561af0f864cc42c2350598a93`

Работать на той же ветке `fix/navigation-core`. PR не мержить.

## Что принято окончательно

- NAV-F1 signed along-track geometry в `Navigation.should_start_descent()` корректна.
- Phase decision между intercept и threshold теперь использует along-track и возвращает `should_descend=True` для `ON_PROFILE`.
- После threshold возвращаются `PAST_THRESHOLD` и `should_descend=False`.
- NAV-F2 принят.
- NAV-F3 longitude/heading contract реализован.
- NAV-F4 принят.
- `check-architecture-freshness` независимо подтверждён как pre-existing: на base SHA `3d24855d32f857cb22b6f36e2e9defc815340302` этот же check имеет `conclusion: failure`. Не обновлять snapshot в этом PR.

## Блокер 1 — production consumer повторно вычисляет профиль по scalar Haversine distance

`Navigation.should_start_descent()` теперь возвращает правильный along-track профиль в `descent_info['ideal_altitude_agl']`.

Но `SyntheticGlidepath.compute_target_vs()` после этого игнорирует его и повторно вычисляет целевую высоту через:

```python
distance_nm = self._nav.calculate_distance_to_threshold(latitude, longitude, self._config)
ideal_alt_msl = self._nav.calculate_required_altitude(
    distance_nm,
    self._config.glideslope_angle,
    self._config.runway_elevation,
)
```

`calculate_distance_to_threshold()` — scalar Haversine distance. Поэтому в реальном вертикальном guidance остаются две ошибки:

1. Cross-track offset увеличивает distance и завышает целевую высоту, хотя along-track progress тот же.
2. Профиль в `SyntheticGlidepath` отличается от уже исправленного профиля `Navigation`, то есть существуют два источника истины.

Gate `should_descend` исправлен, но величина target VS всё ещё вычисляется по старой геометрии.

### Требуемое исправление

В `SyntheticGlidepath.compute_target_vs()` использовать результат уже рассчитанного профиля:

```python
ideal_alt_msl = (
    descent_info['ideal_altitude_agl']
    + float(self._config.runway_elevation)
)
```

Не вычислять второй профиль через scalar `calculate_distance_to_threshold()`.

Сохранить:

- MSL/AGL conversion;
- MDA hard floor и hysteresis;
- sign convention target VS: positive = descend;
- wind-corrected base VS pipeline.

Разрешённый дополнительный production-файл: `modules/synthetic_glidepath.py` — он был предусмотрен исходным scope именно для такого случая.

### Обязательные тесты

1. На одинаковом along-track progress при cross-track offsets 0, 0.5 и 2 NM `SyntheticGlidepath.compute_target_vs()` даёт одинаковый результат в узком числовом допуске при одинаковых altitude/wind inputs.
2. On-profile между intercept и threshold с ненулевым `wind_correction_vs`, например `500.0`, возвращает ожидаемую положительную descent-команду, а не только проверку `>= 0`.
3. Тест должен быть красным на `ac8f6cc...` без addendum-3.
4. MDA floor regression: у/ниже MDA результат остаётся `0.0`.
5. Past-threshold regression: результат не требует дальнейшего снижения.

## Блокер 2 — потеряна существующая ветка HIGH до intercept

Текущий код:

```python
if is_before_intercept:
    should_descend = False
    status = 'OK'
```

безусловно запрещает снижение до intercept. До правки исходная логика позволяла раннее снижение, если самолёт более чем на 300 ft выше требуемой intercept altitude (`altitude_error > 300`, status `HIGH`). В addendum-2 было явно указано сохранить это исключение.

Это полезное safety-поведение: самолёт, пришедший высоко до точки intercept, должен иметь возможность снизиться до высоты перехвата, а не удерживать чрезмерную высоту до самой точки.

### Требуемое исправление

В фазе `is_before_intercept`:

- если `altitude_error > 300`: `should_descend=True`, `status='HIGH'`, reason о снижении до intercept altitude;
- иначе: `should_descend=False`, status `OK`/совместимый статус удержания;
- не начинать снижение только из-за cross-track offset.

### Обязательные тесты

1. До intercept на intercept altitude: `should_descend=False`.
2. До intercept на `intercept_altitude + 301 ft`: `status=HIGH`, `should_descend=True`.
3. До intercept ниже/на профиле не получает ложную команду снижения.
4. Downstream SyntheticGlidepath для HIGH-before-intercept не блокируется gate-ом и выдаёт физически согласованную команду, если MDA не мешает.

## Тест, который нужно усилить

Текущий `test_navf1_on_profile_downstream_positive_vs` утверждает `vs >= 0`, хотя название обещает positive VS. Ноль проходит тест и не доказывает отсутствие прежнего hold.

После перехода на единый profile source:

- передать ненулевой `wind_correction_vs`;
- ожидать `vs > 0` и по возможности точное значение через `pytest.approx`;
- не использовать assertion `>= 0` для доказательства продолжения снижения.

## CI

Freshness и lint считаются pre-existing только в рамках этого PR:

- base `3d24855d`: `check-architecture-freshness = failure`;
- base `3d24855d`: `lint-ruff = failure`;
- остальные проверки нового head должны быть зелёными.

Не исправлять эти два долга в navigation PR.

## Финальные проверки

- `pytest tests/ -q`;
- targeted Navigation + SyntheticGlidepath tests;
- `ruff check modules/navigation.py modules/synthetic_glidepath.py tests/test_navigation.py` и новый/изменённый synthetic test file;
- `python -m py_compile modules/navigation.py modules/synthetic_glidepath.py`;
- `git diff --check`;
- GitHub checks на новом head.

## Обновление PR body

Перед финальной приёмкой обновить устаревшие значения в описании PR:

- актуальное число тестов;
- актуальное число новых тестов;
- упомянуть три addendum-коммита/итерации либо дать итоговое summary без старых чисел `324` и `23`.

## Формат ответа

Вернуть:

- новый commit SHA и parent `ac8f6cc...`;
- точный addendum-3 diff;
- red-without-addendum-3 evidence для cross-track downstream и HIGH-before-intercept;
- числовые probes;
- полный pytest/ruff/py_compile;
- полный список checks;
- подтверждение, что PR #7 не смёржен.
