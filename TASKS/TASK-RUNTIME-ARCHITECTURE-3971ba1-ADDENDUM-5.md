# TASK: RUNTIME-ARCHITECTURE-3971ba1 — ADDENDUM 5 (MICRO)

## Статус v5

```text
ACCEPTED_WITH_TWO_MINOR_CORRECTIONS
```

Основные артефакты, JSON schema 2.0, harness 11/11, DEPGRAPH reconciliation, manifest и standalone verifier приняты. Production-код, диаграммы, CSV, JSON и harness заново не перестраивать, кроме двух точечных исправлений ниже.

Baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

---

## 1. Исправить описание abort transitions в отчёте

Машинные данные корректны:

```text
INTERMEDIATE → IDLE
FINAL → IDLE
```

Но `RUNTIME-ARCHITECTURE-REPORT.md` ошибочно говорит:

```text
Abort transitions: 2 (both from FINAL → IDLE)
```

### Требуется

Заменить на:

```text
Abort transitions: 2
- INTERMEDIATE → IDLE — takeover failure in IntermediatePhaseState
- FINAL → IDLE — SafetyGuard / weather / stabilization / DH / takeover failure in FinalPhaseState / error budget
```

Точно развести call sites:

- `approach_phases.py:244` — Intermediate takeover failure;
- `approach_phases.py:373` — Final/ILS takeover failure;
- остальные FINAL triggers оставить в FINAL→IDLE.

Проверить, что report, CSV и JSON одинаково атрибутируют phase каждого call site.

---

## 2. Исправить `verifier-stdout.txt`

Независимый свежий запуск из ZIP подтверждён:

```text
RESULT: PASS
EXIT=0
```

Но упакованный `verifier-stdout.txt` заканчивается старым результатом:

```text
RESULT: FAIL (1 errors)
- hash mismatches = 1
```

Причина — verifier stdout записывался в файл, который одновременно входил в проверяемый manifest; во время redirect файл был изменён и self-check закономерно увидел mismatch.

### Требуется

Устранить циклическую зависимость одним из способов:

#### Рекомендуемый вариант

- `artifact-manifest.json` не включает:
  - сам `artifact-manifest.json`;
  - `verifier-stdout.txt`.
- Verifier явно разрешает эти два служебных файла вне manifest.
- Сначала проверить все manifest entries.
- Затем запустить verifier и сохранить stdout.
- В ZIP включить итоговый `verifier-stdout.txt` с:

```text
RESULT: PASS
EXIT=0
```

Также исправить две вводящие в заблуждение PASS-подписи verifier:

```text
JSON scenarios != harness scenarios
trace set != scenario set
```

на:

```text
JSON scenarios == harness scenarios
trace set == scenario set
```

Логика equality уже работает; требуется исправить только текст сообщений.

---

## 3. Финальная упаковка

Создать без изменения core artifacts:

```text
RUNTIME-ARCHITECTURE-3971ba1-v5.1.zip
```

Проверки:

```text
fresh extraction verifier       PASS / exit 0
saved verifier stdout           PASS / exit 0
abort transitions in report     INTERMEDIATE→IDLE + FINAL→IDLE
CSV/JSON transition count       7
ZIP backslash names             0
manifest mismatches              0
production diff                 clean
```

---

## Формат ответа

```text
STATUS: COMPLETED_MINOR_CORRECTIONS
REPORT_ABORT_TRANSITIONS
VERIFIER_STDOUT_TAIL
FRESH_EXTRACTION_EXIT
MANIFEST
ZIP_PATH
GIT_PROOF
```

Приложить `RUNTIME-ARCHITECTURE-3971ba1-v5.1.zip`. Не вставлять большие артефакты в чат.

---

## Критерий

> Это редакционно-упаковочный addendum. Не менять принятые алгоритмические выводы, diagrams, harness semantics или production-код.
