# TASK-MIMO-MERGE-PR7-C2BC9E5

## Решение ревью

`APPROVE_CODE — MERGE_AFTER_METADATA_UPDATE`

PR: https://github.com/zhuk-mou-1/msfs_autoland/pull/7

Approved head: `c2bc9e5e11b2b1a23d086047cfb583f1c38f4594`

Required base: `3d24855d32f857cb22b6f36e2e9defc815340302`

Никаких изменений production-кода в этой задаче не делать. Если head PR изменился — остановиться и вернуть новый SHA для повторной проверки.

## 1. Обновить PR body

Текущее описание устарело: указывает 324 теста, 23 новых теста, только два изменённых файла и безусловный hold до intercept.

Обновить итоговое описание так, чтобы оно отражало финальный PR:

- NAV-F1: signed along-track phase/profile от intercept до threshold;
- `ON_PROFILE` между intercept и threshold продолжает снижение;
- `PAST_THRESHOLD` запрещает дальнейшее снижение;
- до intercept сохраняется исключение `HIGH` при превышении intercept altitude более чем на 300 ft;
- `SyntheticGlidepath` использует `descent_info['ideal_altitude_agl']` как единый источник профиля;
- NAV-F2 inbound bearing;
- NAV-F3 dead-code removal, finite/range/ordering validation, longitude `[-180, 180]`, heading `% 360`;
- NAV-F4 signed `angle_difference`;
- изменённые production-файлы: `modules/navigation.py`, `modules/synthetic_glidepath.py`;
- тесты: `346 passed`, 1 warning;
- актуальное число добавленных navigation tests определить по diff, не оставлять старое `23` без проверки;
- CI debt: `lint-ruff` и `check-architecture-freshness` pre-existing на base `3d24855d`; остальные checks успешны.

## 2. Необязательное улучшение теста

Не блокирует merge: отдельного downstream-теста именно для `HIGH before intercept` нет. Unit-test ветки HIGH и downstream SyntheticGlidepath tests покрывают составные части. Не добавлять новый commit в merge-only задаче; занести этот интеграционный test-gap в следующий test-maintenance/P2 пакет.

## 3. Предmerge-проверка

Непосредственно перед merge подтвердить:

- PR #7 открыт, не draft;
- head точно `c2bc9e5e11b2b1a23d086047cfb583f1c38f4594`;
- base точно `3d24855d32f857cb22b6f36e2e9defc815340302`;
- mergeable = true;
- test (3.12) = success;
- test (3.13) = success;
- type-check-mypy = success;
- bandit-security = success;
- radon-complexity = success;
- validate-architecture-snapshot = success;
- lint-ruff = failure, подтверждённый pre-existing на base;
- check-architecture-freshness = failure, подтверждённый pre-existing на base.

## 4. Merge

Смержить PR #7 штатным merge способом без force-push/rebase и без дополнительных code commits.

После merge вернуть:

- merge commit SHA;
- два parent SHA merge commit;
- подтверждение, что первый parent — прежний master `3d24855d...`, второй parent — approved head `c2bc9e5...`;
- новый `origin/master` SHA;
- состояние PR: merged/closed;
- итоговое описание PR;
- ссылку на PR.

## 5. Post-merge verification

Независимо проверить:

- `origin/master` указывает на merge commit;
- approved head входит в историю master;
- изменены только ожидаемые три файла относительно base:
  - `modules/navigation.py`;
  - `modules/synthetic_glidepath.py`;
  - `tests/test_navigation.py`;
- на merge commit запущены push-checks; вернуть их полный список и статусы;
- известные pre-existing failures не выдавать за регрессию PR #7.

## Запреты

- не обновлять architecture snapshot в PR #7;
- не исправлять global lint debt в PR #7;
- не менять код после approved head;
- не начинать P2/Pass B до подтверждения merge и post-merge verification.
