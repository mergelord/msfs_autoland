TASK: CI-LINT-SETUP
Цель: добавить в .github/workflows/ci.yml статический анализ (ruff, mypy, radon, bandit) без риска для существующего прогона тестов.
Ветка: ci/lint-static-analysis (от текущего master = 9a15e2e)
Важное ограничение
НЕ трогать существующий job test в ci.yml — он рабочий (251/0 на 3.12/3.13). Все изменения — через добавление новых, отдельных jobs в тот же файл.
Новые jobs должны быть параллельны test, не зависеть от него (needs не указывать), чтобы не увеличивать время до готовности основного сигнала.
Что добавить
1. Job lint-ruff — БЛОКИРУЮЩИЙ
runs-on: ubuntu-latest, один Python (3.12 достаточно, без матрицы)
pip install ruff
ruff check . — если есть ошибки, job должен зафейлиться (это нормальное поведение, без || true)
Добавить pyproject.toml (или ruff.toml) с базовым набором правил: E, F, B (bugbear — mutable defaults и т.п.), UP. Исключить tests/replay/fixtures/*.jsonl и любые сгенерированные файлы из линтинга (это не .py, но на всякий случай проверь exclude).
Если ruff check . находит существующие нарушения в текущем коде — не переписывай логику модулей, чтобы не трогать поведение. Точечно поправь только безопасные вещи (unused imports, форматирование) или добавь # noqa: <код> с кратким комментарием для случаев, где правило ложноположительно/не применимо. Если нарушений много (>20) — остановись и дай мне список с классификацией (safe-to-fix / needs-discussion) вместо массовой правки.
2. Job type-check-mypy — НЕ блокирующий
continue-on-error: true на уровне job или шага, чтобы красный mypy не валил весь workflow.
pip install mypy
Настроить mypy.ini (или секцию в pyproject.toml) с ignore_missing_imports = True для SimConnect, pyvjoy, gtts, pygame (эти модули недоступны в CI, как и в тестах).
Область проверки — только 3 safety-critical модуля для начала: modules/approach_phases.py, modules/autopilot_takeover.py, modules/safety_guard.py. Команда: mypy modules/approach_phases.py modules/autopilot_takeover.py modules/safety_guard.py. Остальной код пока не проверяем — избегаем шума на нетипизированной legacy-базе.
Не добавляй аннотации типов в сами модули в рамках этой таски — это отдельная задача. Сейчас цель — просто включить сигнал.
3. Job radon-complexity — НЕ блокирующий, информационный
pip install radon
radon cc modules/ main.py -s -a (cyclomatic complexity) и radon mi modules/ main.py -s (maintainability index)
Просто вывести в лог job (stdout), без порогов/фейлов. Не нужен continue-on-error, если сама команда не возвращает ненулевой код при обычной работе — проверь, но в целом radon не фейлится по умолчанию без флага --min/--max с строгим порогом.
4. Job bandit-security — НЕ блокирующий, информационный
pip install bandit
bandit -r modules/ main.py -ll (-ll = только MEDIUM+ severity, чтобы не шуметь по мелочи)
continue-on-error: true
Приёмка
Существующий job test не изменён, всё ещё 251/0 на 3.12 и 3.13.
4 новых job видны в Actions на PR/push, каждый успешно ЗАПУСКАЕТСЯ (для non-blocking — не важно красный или зелёный результат самого анализа, важно что job механически работает и не крашится на инфраструктурном уровне).
lint-ruff — либо зелёный, либо (если есть находки) даёшь мне список находок с классификацией вместо самостоятельной правки логики.
Отчёт: TASKS\REVIEWS\CI-LINT-SETUP-REPORT.md — что добавлено, что нашли ruff/mypy/radon/bandit при первом прогоне (даже если non-blocking — интересны находки), финальные run ID со статусами.
Не пушить TASKS\.
Формат сдачи — как обычно: ветка → отчёт в чат → я делаю независимое ревью по GitHub API → мы согласовываем merge.