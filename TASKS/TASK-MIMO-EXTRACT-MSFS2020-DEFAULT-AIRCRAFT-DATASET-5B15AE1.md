# TASK-MIMO: Извлечение датасета дефолтных бортов из локальной установки MSFS 2020

**Task ID:** `DATA-MSFS2020-01`
**Repo:** `zhuk-mou-1/msfs_autoland`
**Trusted baseline:** `5b15ae12422dc82fd99be2279459d042f3847963` (origin/master)
**Branch:** `data/msfs2020-default-aircraft-dataset` → PR в `master`
**Тип задачи:** READ-ONLY извлечение данных с локальной машины. НЕ фикс, НЕ фича.

---

## Overriding criterion (действует поверх всего)

- Никаких изменений production-кода. Запрещено трогать `modules/`, `main.py`, `tests/`, `config/`.
- Никакой новой логики в приложении. Экстрактор — одноразовый standalone-скрипт, НЕ импортируется ниоткуда из проекта.
- Только чтение файлов установки MSFS 2020. Ничего в папках симулятора не изменять, не перемещать, не удалять.
- Если факт извлечь нельзя — писать `null` + причину. Ничего не придумывать и не «восстанавливать по памяти».

## Зачем (контекст)

Аудит показал: `MSFSControl` пишет 29 стандартных SimConnect Key Events, но проект нигде не проверяет, что конкретный борт их реально исполняет. Детект самолёта — эвристика по строке `TITLE`. Чтобы заземлить телеметрию и команды на реальную поверхность самолёта, нужен фактический датасет по всем дефолтным бортам MSFS 2020: точные `title`, тип/число двигателей, конфигурация автопилота/автотраста, ступени закрылков, используемые LVars.

Отдельно критично: в `control.py` найден дефект — `FLAPS_SET` шлётся со значениями 0–3, а спецификация требует шкалу 0–16383. Для корректного фикса нужны фактические `[FLAPS.N]`-конфигурации бортов из `flight_model.cfg`.

---

## Шаг 0. Локализация установки

1. Найти `UserCfg.opt`:
   - MS Store: `%LOCALAPPDATA%\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe\LocalCache\UserCfg.opt`
   - Steam: `%APPDATA%\Microsoft Flight Simulator\UserCfg.opt`
2. Прочитать из него `InstalledPackagesPath`.
3. Корень официальных пакетов: `<InstalledPackagesPath>\Official\OneStore\` (MS Store) или `<InstalledPackagesPath>\Official\Steam\`.
4. Зафиксировать в отчёте: канал установки (Store/Steam), полный путь, версию симулятора (из `fs-base/manifest.json` или лаунчера).

## Шаг 1. Отбор пакетов

Включить все каталоги пакетов, имя которых начинается с:

- `asobo-aircraft-*`
- `microsoft-aircraft-*` (сюда входит дефолтный iniBuilds A310: `microsoft-aircraft-a310-300`)

Не включать: ливреи-пакеты без SimObjects/Airplanes, AI-трафик, сторонние marketplace-аддоны.

Для каждого пакета зафиксировать статус читаемости: если файлы зашифрованы (`.fsarchive`, Deluxe/Premium-контент) — записать `"readable": false` с причиной и продолжить. Это НЕ ошибка задачи.

## Шаг 2. Извлечение (per package)

Написать одноразовый скрипт `TASKS/TOOLS/extract_msfs2020_default_aircraft.py` (Python 3, только stdlib: `configparser`/ручной парсер cfg, `json`, `re`, `pathlib`). Cfg-файлы MSFS содержат комментарии `;` и дубли ключей — парсер должен это переживать, а не падать.

### 2.1 `manifest.json`
- `creator`, `title`, `package_version`, `minimum_game_version`, `content_type`

### 2.2 `layout.json`
- только перечень путей, matching: `aircraft.cfg`, `engines.cfg`, `systems.cfg`, `flight_model.cfg`, `cockpit.cfg`, `model/*.xml`, `panel/*`, `html_ui/*` (наличие кастомного JS)

### 2.3 `SimObjects/Airplanes/<variant>/aircraft.cfg`
- `[GENERAL]`: `atc_type`, `atc_model`, `category`, `icao_type_designator`, `icao_manufacturer`, `icao_model`
- Все секции `[FLTSIM.N]`: полный список строк `title=` (это whitelist для SimConnect `TITLE` — самое важное поле датасета), `ui_manufacturer`, `ui_type`, `ui_variation`

### 2.4 `engines.cfg`
- `[GENERALENGINEDATA]`: `engine_type` (0–5), число секций `[ENGINE.N]` → фактическое количество двигателей

### 2.5 `systems.cfg`
- Секция `[AUTOPILOT]` целиком, минимум: `autopilot_available`, `flight_director_available`, `autothrottle_available`, `max_bank`, `use_no_default_autopilot` (если есть), лимиты VS/ALT если заданы

### 2.6 `flight_model.cfg`
- Все секции `[FLAPS.N]`: число позиций закрылков (`flaps-position.N`), значения позиций. Нужно для фикса `FLAPS_SET`.

### 2.7 `cockpit.cfg`
- наличие файла + секция `[RADIOS]`/`[INSTRUMENTS]` если присутствуют (кратко)

### 2.8 `model/*.xml` (+ `panel/`, `html_ui/` если есть)
- Regex-скан по токенам `\(L:[^),\s]+`, `\(H:[^),\s]+`, `\(B:[^),\s]+`
- Итог: списки уникальных LVars/HVars/BVars + счётчики. Файлы >20 МБ можно сканировать потоково.
- Флаг `custom_logic`: true, если найдены нестандартные LVars или свой JS в `html_ui/`

## Шаг 3. Выходные артефакты (deliverables)

1. `TASKS/TOOLS/extract_msfs2020_default_aircraft.py` — одноразовый скрипт (для воспроизводимости)
2. `TASKS/DATA/msfs2020_default_aircraft_dataset.json` — датасет, схема:

```json
{
  "meta": {
    "sim": "MSFS 2020",
    "channel": "steam|msstore",
    "installed_packages_path": "...",
    "game_version": "...",
    "extracted_at": "ISO-8601",
    "script": "TASKS/TOOLS/extract_msfs2020_default_aircraft.py"
  },
  "packages": [
    {
      "package": "asobo-aircraft-c172sp-as1000",
      "readable": true,
      "manifest": { "creator": "...", "package_version": "...", "minimum_game_version": "..." },
      "variants": [
        {
          "simobject": "...",
          "titles": ["..."],
          "atc_type": "...", "atc_model": "...", "category": "...",
          "icao_type_designator": "...",
          "ui_manufacturer": "...", "ui_type": "...",
          "engine_type": 0, "engine_count": 1,
          "autopilot": { "available": true, "autothrottle_available": false, "max_bank": 25.0 },
          "flaps": { "sections": 1, "positions": [0, 10, 20, 30] },
          "lvars": ["..."], "hvars": ["..."], "bvars": ["..."],
          "custom_logic": false,
          "source_paths": { "aircraft_cfg": "...", "engines_cfg": "...", "systems_cfg": "...", "flight_model_cfg": "..." }
        }
      ],
      "errors": []
    }
  ]
}
```

3. `TASKS/REVIEWS/DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1.md` — отчёт:
   - сводная таблица: пакет × число вариантов × число titles × engine_type/count × AP available × A/T available × flaps positions × unique LVars × custom_logic
   - список нечитаемых/пропущенных пакетов с причинами
   - top-аномалии (борта без AP, борта с autothrottle, борта с большим числом LVars)
   - точная команда запуска скрипта и окружение

## Шаг 4. Acceptance criteria

- [ ] JSON валиден (`python -m json.tool` проходит)
- [ ] Покрыты ВСЕ каталоги `asobo-aircraft-*` и `microsoft-aircraft-*` из Official (каждый либо в `packages` с данными, либо с `readable:false` и причиной)
- [ ] Каждое значение имеет `source_paths` (трассируемость до файла-источника)
- [ ] Нечего не выдумано: отсутствующие поля = `null` + запись в `errors`
- [ ] `git diff --stat` PR содержит ТОЛЬКО добавления под `TASKS/` (0 изменений в `modules/`, `tests/`, `main.py`, `config/`)
- [ ] Все 399 тестов проходят без изменений (`pytest -q`) — как доказательство, что production-код не тронут
- [ ] Отчёт в `TASKS/REVIEWS/DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1.md`

## Явно ЗАПРЕЩЕНО

- Менять что-либо в `modules/`, `tests/`, `main.py`, `config/`
- Подключать скрипт к приложению (импорты, вызовы, CI)
- Добавлять зависимости (только stdlib)
- Скачивать что-либо из интернета
- «Дополнять» датасет данными не из файлов установки (из памяти, из форумов, из SDK-доков)

## Формат ответного отчёта MiMo

В PR-описании и в отчёте указать: base SHA, ветку, канал установки MSFS, полное число найденных пакетов / прочитанных / нечитаемых, итоговое число вариантов и уникальных titles.
