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

## Сводка (обновлено после FIX-1..6)

| Метрика | Значение |
|---|---|
| Всего пакетов | 216 |
| Aircraft packages | 48 |
| Livery packages | 164 |
| Readable | 212 |
| Нечитаемых (зашифрованы) | 4 |
| Aircraft variants | 58 |
| Aircraft titles | 123 |

## Нечитаемые пакеты

| Пакет | Причина |
|---|---|
| asobo-aircraft-pitts-s1-reno | Encrypted (.fsarchive) |
| microsoft-aircraft-a310-300 | Encrypted (.fsarchive) |
| microsoft-aircraft-a320neo | Encrypted (.fsarchive) |
| microsoft-aircraft-volocity | Encrypted (.fsarchive) |

## Примеры flaps (FIX-1)

**A320neo** (2 sections):
- FLAPS.0 (trailing edge): 5 positions — angles: 0, 10, 15, 20, 35 deg
- FLAPS.1 (leading edge): 5 positions — angles: 0, 18, 22, 22, 27 deg

**C152** (1 section):
- FLAPS.0: 4 positions — angles: 0, 10, 20, 30 deg

**C172SP** (1 section):
- FLAPS.0: 4 positions — angles: 0, 10, 20, 30 deg

## Engine count (FIX-2)

| Авиа | engine_count |
|---|---|
| C208B Grand Caravan | 1 |
| A320neo | 2 |
| Generic Twin Engines | 2 |
| Generic Quad Engines | 4 |

## FIX-6 решение

`TASKS/TOOLS/analyze_dataset.py` — оставлен как валидатор, обновлён под новую схему (aircraft/livery разделение, flaps sections, structured max_bank).

## Acceptance criteria

- [x] JSON валиден
- [x] A320neo: 10 позиций закрылков (5+5) с углами; C152: 4 позиции
- [x] engine_count: C208=1, A320neo=2, quadengines=4
- [x] Ни одного title/atc_type/category с обрамляющими кавычками
- [x] meta содержит раздельные счётчики aircraft/livery
- [x] Diff только под TASKS/; 399 тестов проходят; отчёт обновлён
- [x] Заявленный список файлов == фактический diff PR
