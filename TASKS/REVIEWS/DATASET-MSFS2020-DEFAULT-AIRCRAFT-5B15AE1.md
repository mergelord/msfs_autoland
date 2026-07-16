# DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1

## Мета

```
Sim: MSFS 2020
Channel: msstore (OneStore)
InstalledPackagesPath: R:\GAMES
Trusted baseline: 5b15ae12422dc82fd99be2279459d042f3847963
Extracted: 2026-07-16
Script: TASKS/TOOLS/extract_msfs2020_default_aircraft.py
```

## Сводка

| Метрика | Значение |
|---|---|
| Всего пакетов | 216 |
| Читаемых | 212 |
| Нечитаемых (зашифрованы) | 4 |
| Вариантов (simobjects) | 222 |
| Уникальных titles | 256 |

## Нечитаемые пакеты

| Пакет | Причина |
|---|---|
| asobo-aircraft-pitts-s1-reno | Encrypted (.fsarchive) |
| microsoft-aircraft-a310-300 | Encrypted (.fsarchive) |
| microsoft-aircraft-a320neo | Encrypted (.fsarchive) |
| microsoft-aircraft-volocity | Encrypted (.fsarchive) |

Это Deluxe/Premium контент — не ошибка задачи.

## Топ-аномалии

### Борта без AP
- asobo-aircraft-c152
- asobo-aircraft-cabri-g2
- asobo-aircraft-cap10c
- asobo-aircraft-dg1001-e (глайдер)
- asobo-aircraft-dr400
- asobo-aircraft-e330
- asobo-aircraft-flightdesignct
- asobo-aircraft-icon
- asobo-aircraft-ls8 (глайдер)
- asobo-aircraft-pitts
- asobo-aircraft-vl3
- microsoft-aircraft-jn4
- microsoft-aircraft-wright-flyer

### Борта с autothrottle
- asobo-aircraft-a320-neo
- asobo-aircraft-fa18e
- asobo-aircraft-generic-airliner-quadengines
- asobo-aircraft-generic-airliner-twinengines
- microsoft-aircraft-bell407

### Борта с большим числом LVars (>20)
- asobo-aircraft-dg1001-e: 26 LVars
- asobo-aircraft-fa18e: 28 LVars
- microsoft-aircraft-dhc2: 28 LVars
- microsoft-aircraft-hughes-h4-hercules: 21 LVars

## Acceptance criteria

- [x] JSON валиден (`python -m json.tool` проходит)
- [x] Покрыты ВСЕ каталоги `asobo-aircraft-*` и `microsoft-aircraft-*` (216 packages, каждый либо readable с данными, либо unreadable с причиной)
- [x] Каждое значение имеет `source_paths`
- [x] Отсутствующие поля = `null`
- [x] `git diff --stat` PR содержит ТОЛЬКО добавления под `TASKS/`
- [x] 399 тестов проходят без изменений
- [x] Отчёт в `TASKS/REVIEWS/DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1.md`

## Deliverables

1. `TASKS/TOOLS/extract_msfs2020_default_aircraft.py` — одноразовый скрипт
2. `TASKS/DATA/msfs2020_default_aircraft_dataset.json` — датасет
3. `TASKS/REVIEWS/DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1.md` — этот отчёт
