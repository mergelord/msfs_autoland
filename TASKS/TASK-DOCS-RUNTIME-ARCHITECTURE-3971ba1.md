# TASK: DOCS-RUNTIME-ARCHITECTURE-3971ba1

## 0. Цель

Создать и опубликовать отдельную документационную ветку:

```text
docs/runtime-architecture-3971ba1
```

В ветке разместить канонический архитектурный snapshot проекта `msfs_autoland` на baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

Snapshot должен включать принятые DEPGRAPH- и RUNTIME-ARCHITECTURE-артефакты, методологию evidence levels, ограничения, инструкции для внешнего аудитора и CI-проверки:

1. целостности архитектурной документации;
2. актуальности snapshot относительно production-кода;
3. обязательного regeneration или architecture-diff после production-изменений.

Это **docs/CI task**, не bugfix.

---

## 1. Repository и baseline

- Repository: `zhuk-mou-1/msfs_autoland`
- Default branch: `master`
- Required baseline:

```text
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

- Local checkout:

```text
C:\BAT\msfs_autoland
```

- Canonical runtime package:

```text
RUNTIME-ARCHITECTURE-3971ba1-v5.1.zip
```

- Existing canonical DEPGRAPH artifacts:

```text
research/depgraph/
```

Перед началом:

```powershell
git fetch origin
git rev-parse HEAD
git rev-parse origin/master
git status --short
```

Если `origin/master` не указывает на baseline, остановиться:

```text
BLOCKED_BASELINE_MOVED
```

Не удалять существующие untracked `TASKS/`, `research/` или ZIP-файлы.

---

## 2. Создание ветки

Создать ветку строго от baseline:

```powershell
git switch master
git reset --hard origin/master
git switch -c docs/runtime-architecture-3971ba1 3971ba12113d8994665b1c9a172f2dca6c9e3855
```

Если ветка уже существует локально или на origin:

- не перезаписывать её автоматически;
- проверить parent/history;
- остановиться с `BLOCKED_BRANCH_EXISTS`, если содержимое не является продолжением этой задачи.

Production-файлы не изменять:

```text
main.py
gui.py
modules/**
tests/**
config/**
```

Разрешённые tracked paths:

```text
docs/architecture/**
.github/workflows/architecture-docs.yml
```

---

## 3. Целевая структура

Создать:

```text
docs/
└── architecture/
    ├── README.md
    ├── CURRENT.md
    ├── CURRENT.json
    ├── EXTERNAL-AUDIT-BRIEF.md
    ├── check_snapshot_freshness.py
    ├── methodology/
    │   ├── EVIDENCE-LEVELS.md
    │   ├── VERIFICATION.md
    │   └── KNOWN-LIMITATIONS.md
    ├── diffs/
    │   └── README.md
    └── snapshots/
        └── 3971ba1/
            ├── README.md
            ├── snapshot-metadata.json
            ├── DEPGRAPH-REPORT.md
            ├── depgraph.json
            ├── depgraph.mmd
            ├── depgraph.png
            ├── RUNTIME-ARCHITECTURE-REPORT.md
            ├── runtime-architecture.json
            ├── module-inventory.csv
            ├── data-dictionary.csv
            ├── actuator-sinks.csv
            ├── command-paths.csv
            ├── phase-transitions.csv
            ├── frame-command-order.csv
            ├── fail-safe-matrix.csv
            ├── go-around-call-sites.csv
            ├── self-system-accesses.csv
            ├── execution-flow.mmd
            ├── execution-flow.dot
            ├── execution-flow.png
            ├── phase-state-machine.mmd
            ├── phase-state-machine.dot
            ├── phase-state-machine.png
            ├── data-flow.mmd
            ├── data-flow.dot
            ├── data-flow.png
            ├── command-flow.mmd
            ├── command-flow.dot
            ├── command-flow.png
            ├── safety-flow.mmd
            ├── safety-flow.dot
            ├── safety-flow.png
            ├── harness/
            │   ├── README.md
            │   ├── results.json
            │   └── command-traces/
            ├── evidence/
            │   ├── depgraph.json
            │   └── source-line-index.json
            ├── verify_runtime_architecture.py
            ├── verifier-stdout.txt
            └── artifact-manifest.json
```

Если canonical v5.1 содержит дополнительные scripts, необходимые verifier/reproducibility, допускается сохранить их внутри snapshot. Не добавлять сам ZIP в git.

---

## 4. Импорт canonical v5.1

1. Распаковать `RUNTIME-ARCHITECTURE-3971ba1-v5.1.zip` во временный каталог.
2. Проверить:

```text
ZIP entries: 52
backslash names: 0
standalone verifier: PASS / exit 0
schema_version: 2.0
nodes: 49
edges: 89
data_items: 36
actuator_sinks: 72
scenarios: 11
state_transition edges: 7
DEPGRAPH reconciliation: 49/49
manifest mismatches: 0
```

3. Скопировать содержимое в:

```text
docs/architecture/snapshots/3971ba1/
```

4. Дополнить snapshot отдельными верхнеуровневыми DEPGRAPH-файлами из `research/depgraph/`, если их нет в v5.1:

```text
DEPGRAPH-REPORT.md
depgraph.json
depgraph.mmd
depgraph.png
```

5. Не копировать:

- ZIP v1–v5.1;
- промежуточные ошибочные отчёты;
- addendum-task files;
- `__pycache__`;
- `.pyc`;
- временные render-файлы;
- локальные task/review notes.

6. Просканировать документацию на локальные/чувствительные данные:

```text
C:\BAT\
user email
API keys
tokens
absolute local paths
```

Если требуется санитизация canonical-файла:

- изменить только документационный текст;
- пересоздать manifest;
- повторно запустить verifier;
- зафиксировать изменение в snapshot README.

---

## 5. Snapshot README

`docs/architecture/snapshots/3971ba1/README.md` должен явно содержать:

```text
Baseline commit:
3971ba12113d8994665b1c9a172f2dca6c9e3855

Production scope:
47 Python files in modules/ + main.py + gui.py = 49 files

Snapshot status:
CANONICAL

Runtime confirmation:
RUNTIME_CONFIRMED = 0
```

Обязательно указать:

- snapshot описывает только baseline `3971ba1`;
- он не считается автоматически актуальным для следующих commit;
- `STATIC_CONFIRMED` не равно реальному исполнению в MSFS;
- `HARNESS_CONFIRMED` не равно `RUNTIME_CONFIRMED`;
- реальные SimConnect/WASM/vJoy/timing свойства требуют MSFS;
- diagrams являются визуализацией machine-readable registry;
- источники истины: baseline source + JSON/CSV evidence + verifier;
- canonical package прошёл независимую проверку;
- архитектурные выводы не являются сертификатом безопасности.

Добавить команды проверки:

```bash
cd docs/architecture/snapshots/3971ba1
python verify_runtime_architecture.py
```

Ожидаемый результат:

```text
RESULT: PASS
exit code 0
```

---

## 6. Architecture root docs

### 6.1 `docs/architecture/README.md`

Объяснить:

- назначение каталога;
- snapshot-based подход;
- difference между import graph и runtime architecture;
- как открыть Mermaid/PNG;
- как проверить snapshot;
- как добавить новый snapshot;
- как создать architecture-diff;
- почему нельзя молча обновлять старый snapshot после изменения production-кода.

### 6.2 `CURRENT.md`

Человекочитаемый указатель:

```text
Current canonical snapshot: snapshots/3971ba1/
Baseline: 3971ba12113d8994665b1c9a172f2dca6c9e3855
Status relative to current production tree: CURRENT
```

Добавить правило:

```text
Если production digest отличается:
STATUS = STALE
Требуется новый snapshot или architecture-diff.
```

### 6.3 `CURRENT.json`

Минимальная schema:

```json
{
  "schema_version": "1.0",
  "snapshot": "docs/architecture/snapshots/3971ba1",
  "baseline_commit": "3971ba12113d8994665b1c9a172f2dca6c9e3855",
  "production_digest_algorithm": "sha256-path-null-content-v1",
  "production_digest": "<computed>",
  "status": "CURRENT"
}
```

Production digest вычислять по отсортированному списку:

```text
main.py
gui.py
modules/**/*.py
```

Digest должен зависеть от path + file content, но не от docs commit SHA. Тогда документационные commits не делают snapshot STALE.

---

## 7. Methodology docs

### 7.1 `EVIDENCE-LEVELS.md`

Документировать:

```text
STATIC_CONFIRMED
TEST_CONFIRMED
HARNESS_CONFIRMED
RUNTIME_CONFIRMED
INFERRED
UNREACHED
DEAD
```

Для каждого уровня:

- точное определение;
- допустимые доказательства;
- что уровень НЕ доказывает;
- пример.

### 7.2 `VERIFICATION.md`

Описать:

- проверку manifest;
- standalone verifier;
- evidence bundle;
- DEPGRAPH reconciliation;
- scenario/trace validation;
- JSON/CSV/diagram consistency;
- freshness checker;
- CI jobs;
- локальные команды воспроизведения.

### 7.3 `KNOWN-LIMITATIONS.md`

Минимум:

- SimConnect timing;
- telemetry jitter/age;
- WASM/LVAR accuracy;
- vJoy hardware behavior;
- real aircraft dynamics;
- no real MSFS runtime confirmation;
- mock/harness boundaries;
- snapshot baseline limitation;
- авиационные sign/unit/geometry выводы требуют отдельной физической проверки.

---

## 8. External audit brief

Создать `docs/architecture/EXTERNAL-AUDIT-BRIEF.md`.

Аудит проводить в два прохода.

### PASS A — blind code-first audit

Аудитору предоставить repository и baseline, но не показывать архитектурные выводы до фиксации первого отчёта.

Попросить независимо восстановить:

- lifecycle;
- state machine;
- telemetry/data flow;
- command path;
- ownership;
- actuator sinks;
- safety/fail-safe;
- go-around/takeover;
- dead/unreachable paths;
- readiness verdict.

### PASS B — architecture cross-check

После завершения PASS A открыть:

```text
docs/architecture/snapshots/3971ba1/
```

Попросить определить:

- совпадения;
- противоречия;
- пропуски;
- ошибочные evidence levels;
- неверные file:line;
- недоказанные выводы;
- архитектурные риски;
- рекомендации.

### Обязательные аудит-домены

- code correctness;
- architecture/modularity;
- `self.system.*` coupling;
- state management;
- telemetry freshness;
- error handling/fail-silent behavior;
- CommandGateway/ownership;
- go-around atomicity;
- test/harness realism;
- aviation units/signs/geometry;
- operational readiness.

### Deliverables внешнего аудитора

```text
EXTERNAL-CODE-AUDIT.md
EXTERNAL-ARCHITECTURE-AUDIT.md
ARCHITECTURE-CROSSCHECK.md
SAFETY-READINESS.md
RECOMMENDED-ROADMAP.md
FINDINGS.json
```

Каждая finding:

```text
id
severity
confidence
file:line
architecture edge
runtime reachability
existing test
required test
recommendation
fix risk
```

Отдельные readiness verdicts:

```text
Unit/CI readiness
Offline integration readiness
Controlled MSFS test readiness
Autonomous scenario readiness
Operational safety readiness
```

---

## 9. Architecture diff protocol

Создать `docs/architecture/diffs/README.md`.

Будущий architecture-diff хранить как:

```text
docs/architecture/diffs/<from>-to-<production-digest-prefix>/
├── architecture-diff.json
├── ARCHITECTURE-DIFF.md
└── affected-tests.md
```

`architecture-diff.json`:

```json
{
  "schema_version": "1.0",
  "from_snapshot": "3971ba1",
  "from_production_digest": "...",
  "to_production_digest": "...",
  "changed_production_files": [],
  "changed_nodes": [],
  "added_edges": [],
  "removed_edges": [],
  "changed_safety_paths": [],
  "required_regression_tests": [],
  "review_status": "PENDING"
}
```

CI может считать production tree документированным через diff только если:

- `from_production_digest` совпадает с `CURRENT.json`;
- `to_production_digest` совпадает с фактическим production digest;
- `changed_production_files` точно совпадает с git diff production scope;
- `review_status` не пустой;
- обязательные поля присутствуют.

Не разрешать bypass через пустой diff-файл.

---

## 10. Freshness checker

Создать:

```text
docs/architecture/check_snapshot_freshness.py
```

Требования:

1. Python stdlib only.
2. Работает на Windows/Linux.
3. Читает `CURRENT.json`.
4. Вычисляет deterministic production digest по:

```text
main.py
gui.py
modules/**/*.py
```

5. Сравнивает с current snapshot digest.
6. Статусы:

```text
CURRENT
CURRENT_WITH_ARCHITECTURE_DIFF
STALE
ERROR
```

7. Если digest совпал:

```text
ARCHITECTURE STATUS: CURRENT
exit 0
```

8. Если digest отличается и валидного architecture-diff нет:

```text
ARCHITECTURE STATUS: STALE
Current production tree differs from baseline snapshot.
Required: regenerate snapshot or add a validated architecture-diff.
exit 1
```

9. Если найден валидный diff, чей `to_production_digest` совпадает:

```text
ARCHITECTURE STATUS: CURRENT_WITH_ARCHITECTURE_DIFF
exit 0
```

10. Писать summary в stdout и, если задан `GITHUB_STEP_SUMMARY`, добавлять Markdown summary туда.
11. Не изменять документы автоматически.
12. Поддержать параметры:

```text
--repo-root
--current-file
--diff-root
--json-output
```

13. `--json-output` должен выдавать machine-readable status.

---

## 11. CI workflow

Создать:

```text
.github/workflows/architecture-docs.yml
```

Название:

```text
Architecture Documentation
```

Triggers:

```yaml
on:
  pull_request:
    paths:
      - 'docs/architecture/**'
      - 'main.py'
      - 'gui.py'
      - 'modules/**/*.py'
      - '.github/workflows/architecture-docs.yml'
  push:
    branches: [master]
    paths:
      - 'docs/architecture/**'
      - 'main.py'
      - 'gui.py'
      - 'modules/**/*.py'
      - '.github/workflows/architecture-docs.yml'
  workflow_dispatch:
```

Использовать текущую стабильную Python-версию CI проекта либо Python 3.13.

### Job 1: `validate-architecture-snapshot`

Шаги:

```bash
python docs/architecture/snapshots/3971ba1/verify_runtime_architecture.py
```

Ожидается PASS/exit 0.

Job проверяет изменения архитектурной документации и не зависит от MSFS.

### Job 2: `check-architecture-freshness`

Шаг:

```bash
python docs/architecture/check_snapshot_freshness.py \
  --repo-root . \
  --current-file docs/architecture/CURRENT.json \
  --diff-root docs/architecture/diffs \
  --json-output
```

Поведение:

```text
Production digest == snapshot digest
→ CURRENT → PASS

Production digest changed + valid architecture-diff
→ CURRENT_WITH_ARCHITECTURE_DIFF → PASS

Production digest changed + no valid diff/new snapshot
→ STALE → FAIL
```

### Security/robustness

- Не выполнять произвольный код из PR кроме tracked stdlib scripts.
- Не использовать `pull_request_target`.
- Не выдавать write permissions.
- Добавить минимальные permissions:

```yaml
permissions:
  contents: read
```

- Не использовать внешние Actions, кроме официальных `actions/checkout` и `actions/setup-python` с pinned major versions.

---

## 12. Локальные тесты CI/freshness

До commit выполнить:

```powershell
python docs/architecture/snapshots/3971ba1/verify_runtime_architecture.py
python docs/architecture/check_snapshot_freshness.py --repo-root . --current-file docs/architecture/CURRENT.json --diff-root docs/architecture/diffs --json-output
python -m py_compile docs/architecture/check_snapshot_freshness.py
python -m py_compile docs/architecture/snapshots/3971ba1/verify_runtime_architecture.py
git diff --check
```

Ожидается:

```text
snapshot verifier: PASS
freshness: CURRENT
py_compile: PASS
git diff --check: PASS
```

### Negative freshness self-test

Во временной копии или с параметром fixture/test mode:

- изменить один production byte;
- убедиться, что checker возвращает `STALE` и exit 1;
- вернуть файл без изменения working tree.

### Valid diff self-test

Во временном каталоге:

- создать fixture architecture-diff с правильными from/to digest;
- checker должен вернуть `CURRENT_WITH_ARCHITECTURE_DIFF`;
- invalid/empty diff должен вернуть `STALE` или `ERROR`.

Не изменять production-файлы в реальной ветке.

---

## 13. Документационный индекс и navigation

`docs/architecture/README.md` должен ссылаться относительными ссылками на:

- current snapshot;
- DEPGRAPH report;
- runtime report;
- пять diagrams;
- machine-readable JSON;
- evidence levels;
- limitations;
- verification guide;
- external audit brief;
- architecture-diff protocol.

Все ссылки проверить локально: target существует, case совпадает.

---

## 14. Git discipline

Перед staging:

```powershell
git status --short
git diff --name-only
```

Staging только явно:

```powershell
git add docs/architecture .github/workflows/architecture-docs.yml
```

Запрещено:

```text
git add .
git add -A
```

Проверить staged scope:

```powershell
git diff --cached --name-only
```

Допустимы только:

```text
docs/architecture/**
.github/workflows/architecture-docs.yml
```

Проверить отсутствие production diff:

```powershell
git diff --exit-code 3971ba12113d8994665b1c9a172f2dca6c9e3855 -- main.py gui.py modules tests config
```

Должен быть exit 0.

---

## 15. Commit, push, PR

Создать один docs-only commit:

```text
docs: add verified runtime architecture snapshot 3971ba1
```

Перед push повторить:

```powershell
git diff HEAD^ --name-only
git status --short
git log -1 --oneline
```

Push:

```powershell
git push -u origin docs/runtime-architecture-3971ba1
```

Не merge в master.

Если `gh` доступен и авторизован — открыть PR:

```text
Title: docs: add verified runtime architecture snapshot 3971ba1
Base: master
Head: docs/runtime-architecture-3971ba1
```

PR body:

- baseline;
- docs-only scope;
- verifier PASS;
- freshness CURRENT;
- CI behavior;
- unresolved MSFS-only limitations;
- external audit plan;
- explicit `NO PRODUCTION CODE CHANGES`.

Если PR создать нельзя — не блокировать push; вернуть compare URL/instructions.

---

## 16. Acceptance criteria

Задача принимается только если:

- ветка создана от `3971ba1`;
- canonical v5.1 unpacked в snapshot;
- DEPGRAPH top-level artifacts присутствуют;
- root README/CURRENT/methodology/limitations/audit brief созданы;
- snapshot metadata и production digest созданы;
- standalone verifier PASS;
- freshness checker CURRENT;
- negative stale test PASS;
- valid architecture-diff fixture test PASS;
- CI workflow содержит два jobs;
- CI workflow не использует `pull_request_target`;
- permissions `contents: read`;
- production diff = 0;
- commit docs-only;
- branch pushed;
- PR открыт либо возвращён compare URL;
- master не изменён;
- ZIP и промежуточные task-файлы не закоммичены.

---

## 17. Формат финального ответа

Начать ровно:

```text
COMPLETED_AND_PUSHED
```

или:

```text
COMPLETED_NOT_PUSHED
```

или:

```text
BLOCKED
```

Разделы:

```text
BASELINE
BRANCH
COMMIT
TRACKED_SCOPE
SNAPSHOT_COUNTS
DEPGRAPH
VERIFIER
PRODUCTION_DIGEST
FRESHNESS_CHECK
NEGATIVE_STALE_TEST
ARCHITECTURE_DIFF_TEST
CI_WORKFLOW
PRODUCTION_DIFF
PUSH
PR
GIT_STATUS
```

В `TRACKED_SCOPE` дать counts и paths, без вставки содержимого MMD/JSON/CSV.

В `CI_WORKFLOW` указать оба job names и trigger paths.

В `GIT_STATUS` отдельно показать оставшиеся untracked `TASKS/`, `research/`, ZIP — они не должны попасть в commit.

---

## 18. Stop conditions

Остановиться без commit/push, если:

- origin/master не baseline;
- canonical v5.1 verifier не проходит;
- DEPGRAPH 49/49 не сходится;
- production digest нельзя воспроизвести;
- freshness checker не ловит modified production file;
- invalid/empty architecture-diff ошибочно пропускает stale state;
- CI YAML невалиден;
- staged scope содержит production/test/config files;
- local sensitive paths не удалось безопасно удалить;
- branch conflict/unknown history.

Финальный принцип:

> Snapshot остаётся неизменяемым историческим доказательством baseline `3971ba1`. После изменения production-кода обновляется CURRENT через новый snapshot или проверенный architecture-diff; старый snapshot не переписывается.
