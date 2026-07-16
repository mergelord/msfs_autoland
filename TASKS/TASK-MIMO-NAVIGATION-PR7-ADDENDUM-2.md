# TASK-MIMO-NAVIGATION-PR7-ADDENDUM-2

## Статус ревью

`REQUEST_CHANGES`

PR: https://github.com/zhuk-mou-1/msfs_autoland/pull/7

Проверенный head: `0774c8b25015b4c561af0f864cc42c2350598a93`

Parent подтверждён: `c4c8537eadcf72c0d2c86f23e2850d38769d556d`

Работать на той же ветке `fix/navigation-core`. PR не мержить.

## Что принято

- Signed local tangent-plane projection теперь действительно реализована.
- Профиль clamp `[0, intercept_to_threshold]` корректно даёт 0 после порога и intercept altitude до intercept.
- Строгие cross-track и after-threshold тесты добавлены.
- NAV-F4 sign исправлен правильно: `angle_difference(expected, current)`.
- NAV-F3 получил finite checks и верхнюю границу glideslope.
- Scope остаётся ровно 2 файла.
- Tests 3.12/3.13, bandit, radon и validate-architecture-snapshot зелёные.

## Блокер 1 — NAV-F1: on-profile самолёт после intercept всё ещё получает `should_descend=False`

Геометрия высоты исправлена, но decision logic ниже всё ещё привязана к scalar `distance_to_intercept`:

```python
elif abs(altitude_error) <= 200:
    should_descend = (distance_to_intercept <= tolerance_nm)
    status = "ON_PROFILE"
```

После прохождения intercept `distance_to_intercept` растёт. Поэтому самолёт, находящийся точно на правильном профиле между intercept и threshold, получает:

- `status = ON_PROFILE`;
- `should_descend = False` после выхода дальше чем на `tolerance_nm` от intercept;
- downstream `SyntheticGlidepath.compute_target_vs()` может вернуть `0.0` и прекратить команду снижения.

Текущий downstream-тест использует самолёт значительно выше профиля, поэтому попадает в ветку `HIGH`, где `should_descend=True`, и не покрывает дефект on-profile.

### Требуемое исправление

Decision logic должна использовать along-track phase:

- `along_track_nm > intercept_to_threshold + tolerance`: до intercept;
- около intercept: `INTERCEPT`, `should_descend=True`;
- `0 < along_track_nm < intercept_to_threshold`: после intercept, до threshold;
- `along_track_nm <= 0`: порог/после порога, не продолжать синтетическое снижение.

Для самолёта между intercept и threshold:

- `ON_PROFILE` → `should_descend=True`;
- умеренно `HIGH` → `should_descend=True`;
- `LOW` → оставить fail-safe поведение без команды дальнейшего снижения;
- после threshold → `should_descend=False`.

Не использовать растущее `distance_to_intercept` как gate продолжения снижения. Его можно сохранить только для observability/reason.

### Обязательные тесты

1. На 75%, 50%, 25% пути intercept→threshold, при `current_altitude_agl == ideal_altitude_agl`: `status == ON_PROFILE`, `should_descend is True`.
2. Тот же сценарий через реальный `SyntheticGlidepath.compute_target_vs()` должен давать положительную команду descent, а не `0.0`.
3. До intercept on-profile/на intercept altitude: не начинать снижение раньше заданного gate, кроме существующей ветки HIGH.
4. После threshold: `should_descend=False`, target VS не требует дальнейшего снижения.
5. Red-without-addendum-2 для on-profile точки на 50% пути.

## Блокер 2 — NAV-F3: контракт longitude и heading не завершён

В addendum требовалось:

- диапазон longitude;
- нормализация finite heading либо отклонение вне выбранного диапазона;
- тесты на выбранный контракт.

Текущий код проверяет longitude и heading только на finite. Поэтому, например, longitude `1000°` и heading `100000°` проходят молча.

### Требуемое исправление

Выбрать и документировать единый контракт:

- latitude: `[-90, 90]`;
- longitude: предпочтительно `[-180, 180]` с `ValueError`, либо явная нормализация с тестами;
- heading: предпочтительно нормализация finite значения через `% 360`, либо диапазон `[0, 360)` с `ValueError`.

Добавить boundary tests: longitude `-180`, `180`, за пределами; heading `0`, `359.999`, `360`, отрицательный и большой положительный.

## Блокер 3 — новый красный CI `check-architecture-freshness`

На head `0774c8b` GitHub показывает 8 checks, из них минимум два красных:

- `lint-ruff` — известный pre-existing failure;
- `check-architecture-freshness` — отдельный failure, который нельзя автоматически считать pre-existing.

`validate-architecture-snapshot` при этом зелёный.

### Требуемое действие

1. Получить точный stdout/log `check-architecture-freshness` локально или через GitHub CLI.
2. Установить, вызван ли failure изменением `modules/navigation.py` и какой именно freshness contract нарушен.
3. Не обновлять architecture snapshot вслепую и не добавлять docs в PR без объяснения.
4. Если check требует обновления только metadata/hash из-за легитимной production-правки — сообщить точный необходимый diff до его внесения либо выполнить минимальное обновление, если repository policy однозначно этого требует.
5. Если failure pre-existing, доказать сравнением того же check на base SHA `3d24855d...`.

Без классификации нового красного check merge не разрешён.

## Проверки после исправления

- полный `pytest tests/ -q`;
- targeted NAV-F1 on-profile tests;
- targeted NAV-F3 boundary tests;
- `ruff check modules/navigation.py tests/test_navigation.py`;
- `python -m py_compile modules/navigation.py`;
- `git diff --check`;
- полный список GitHub checks на новом head.

## Формат ответа

Вернуть:

- новый commit SHA и parent `0774c8b...`;
- diff addendum-2;
- red-without-addendum-2 evidence;
- on-profile probes на 75/50/25%;
- longitude/heading boundary probes;
- полный pytest/ruff/py_compile;
- точную диагностику `check-architecture-freshness`;
- подтверждение, что PR #7 не смёржен.
