# TASK-MIMO-FIX-PR10-MSFS2020-DATASET-D914A2E

## Контекст

**PR:** https://github.com/zhuk-mou-1/msfs_autoland/pull/10 (НЕ мержить текущий head)
**Текущий head:** `d914a2eda62a10f2c164f09c4cdb34758d35acea`
**Base:** `master` @ `5b15ae12422dc82fd99be2279459d042f3847963`

Ревью выявило дефекты извлечения. Исправить экстрактор, перегенерировать датасет, запушить в ЭТУ ЖЕ ветку PR #10. Мержим только исправленную версию.

## Жёсткие границы

- Изменения ТОЛЬКО под `TASKS/`. Запрещено трогать `modules/`, `tests/`, `main.py`, `config/`, CI/workflows, зависимости.
- Скрипт остаётся standalone, stdlib-only, READ-ONLY к файлам MSFS.
- Никакой ручной правки JSON — только перегенерация скриптом.
- Anti-fabrication: отсутствующее/неразбираемое значение = `null` + запись в `errors`. Ничего не дополнять по памяти/форумам/SDK-докам.

## Обязательные исправления (FIX-1…FIX-6)

### FIX-1 (критично): `flaps.positions` — реальные детенты, а не мусор

Сейчас: A320neo → `{sections: 2, positions: [4.0]}` — это НЕ расписание закрылков. Парсер хватает любой ключ с подстрокой `position` (например `number_of_flap_positions = 4`) и теряет реальные записи `flaps-position.N` (значение — CSV, первый компонент = угол в градусах).

Требуется:
- матчить ТОЛЬКО ключи вида `flaps-position.<N>` (регистронезависимо), не любую подстроку `position`;
- из каждого CSV-значения парсить первый числовой компонент = угол (deg);
- сохранять по секциям, не смешивая `[FLAPS.0]` и `[FLAPS.1]` в один set:
```json
"flaps": {"sections": [{"section": "FLAPS.0", "positions": [{"index": 0, "angle_deg": 0.0, "raw": "<исходная строка>"}]}]}
```
- если flight_model.cfg есть, а flaps-position.N нет — `positions: []` + запись в `errors`.

Проверка вменяемости: у Asobo A320neo должно быть НЕСКОЛЬКО позиций (0…full), у C152 — тоже больше одной. Один float на борт = провал критерия.

### FIX-2 (критично): `engine_count` — сейчас `null` у ВСЕХ бортов

Логика `max(N)` по секциям `[ENGINE.N]` не срабатывает. Требуется:
- считать количество секций, точно матчащих `^ENGINE\.(\d+)$` (регистронезависимо); count = число таких секций (индексация с 0: ENGINE.0 и ENGINE.1 → count 2, НЕ max=1);
- дополнительно извлечь `[GENERALENGINEDATA] engine.0..N` если секций нет, и ключ `Engine.N =` если встречается; если ничего нет — `null` + `errors`.

Проверка вменяемости: C208 → 1, A320neo → 2, generic-airliner-quadengines → 4.

### FIX-3 (критично): кавычки в строковых значениях cfg

Сейчас: `titles: ["\"Airbus A320 Neo Asobo\""]` — литеральные кавычки в данных. SimConnect отдаёт TITLE БЕЗ кавычек → точный whitelist-матч провалится.

Требуется: после разбора cfg снимать обрамляющие кавычки (и одинарные, и двойные) + trim у ВСЕХ строковых полей: `title`, `atc_type`, `atc_model`, `category`, `icao_type_designator`, `icao_manufacturer`, `icao_model`, `ui_manufacturer`, `ui_type`, `ui_variation`. Внутренние кавычки не трогать.

### FIX-4: ливреи отделить от самолётов

Пакеты с `manifest.content_type == "LIVERY"` (например `asobo-aircraft-a320-neo-livery-01`) сейчас раздувают счётчики (216/222/256) пустыми вариантами.

Требуется: у каждого пакета добавить поле `"is_livery": true/false` (по content_type). Ливреи ОСТАВИТЬ в датасете (их titles тоже встречаются в SimConnect TITLE), но в `meta` дать раздельные счётчики: `aircraft_packages`, `livery_packages`, `aircraft_variants`, `aircraft_titles`.

### FIX-5: `max_bank` — парсить, не терять raw

Сейчас: `"max_bank": "30,15"` / `"30, 0, 0, 0, 0, 0"` — сырая строка. Требуется: `"max_bank": {"raw": "30,15", "values": [30.0, 15.0]}` (первый компонент = основной лимит крена).

### FIX-6: незадекларированный `TASKS/TOOLS/analyze_dataset.py`

Файл не входил в deliverables задачи DATA-MSFS2020-01. Либо удалить из PR, либо оставить и ЯВНО задекларировать в отчёте как валидатор (тогда обновить его под новую схему flaps/engine_count/meta). Выбор зафиксировать в отчёте.

## Порядок работы

1. Исправить `TASKS/TOOLS/extract_msfs2020_default_aircraft.py` (FIX-1…FIX-5).
2. Перезапустить скрипт на локальной установке (R:\GAMES, msstore/OneStore) → перегенерировать `TASKS/DATA/msfs2020_default_aircraft_dataset.json`.
3. Обновить `TASKS/REVIEWS/DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1.md`: новая сводка (раздельно самолёты/ливреи), решение по FIX-6, примеры flaps для A320neo и C152 (доказательство FIX-1).
4. Прогнать все 399 тестов — без изменений.
5. `git diff --stat` против `5b15ae1` — только под `TASKS/`.
6. Push в ветку PR #10, в комментарий PR — краткий отчёт с фактическими цифрами.

## Acceptance criteria

- [ ] JSON валиден (`python -m json.tool`).
- [ ] A320neo: ≥3 позиций закрылков с углами; C152: ≥2. Ни одного борта с самолётным flight_model.cfg и одиночным бессмысленным float.
- [ ] `engine_count`: C208=1, A320neo=2, quadengines=4; `null` только с причиной в `errors`.
- [ ] Ни одного title/atc_type/category с обрамляющими кавычками.
- [ ] `meta` содержит раздельные счётчики aircraft/livery.
- [ ] Diff только под `TASKS/`; 399 тестов проходят; отчёт обновлён.
- [ ] Заявленный список файлов в отчёте == фактический diff PR (без сюрпризов).
