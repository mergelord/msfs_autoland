# Отчёт: Подключение GitHub Actions CI

**Дата:** 2026-07-13
**Repo:** https://github.com/zhuk-mou-1/msfs_autoland
**Коммит:** `9a15e2e` (master)

---

## 1. Что сделано

Создан GitHub Actions workflow для автоматического прогона тестов при каждом push/PR в master.

### Файлы

| Файл | Изменение | Коммит |
|------|-----------|--------|
| `.github/workflows/ci.yml` | NEW — workflow | `19dbf0a` |
| `tests/conftest.py` | Mock SimConnect + pyvjoy | `19dbf0a`, `8d4bbef` |
| `tests/test_architecture.py` | Хардкод пути → relative | `9a15e2e` |

---

## 2. Workflow: `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          pip install pyvjoy gtts pygame || true
      - name: Run tests
        run: pytest tests/ -q --tb=short
```

**Триггеры:** push в master, PR в master.
**Матрица:** Python 3.12 + 3.13 на ubuntu-latest.
**Зависимости:** pytest (обязательно), pyvjoy/gtts pygame (опционально, `|| true`).

---

## 3. Проблема: модули с нативными зависимостями

Проект имеет две нативные зависимости, недоступные в Linux CI:

1. **SimConnect** — Windows SDK для MSFS. Модуль `modules/control.py` импортирует `from SimConnect import AircraftEvents` на уровне модуля. Без SimConnect — `ModuleNotFoundError` при любом импорте проектных модулей.

2. **pyvjoy** — Windows-драйвер vJoy. Модуль `modules/virtual_joystick.py` импортирует `import pyvjoy` на уровне модуля. На Linux pyvjoy устанавливается, но при импорте вызывает `sys.exit()` из-за отсутствия `vJoyInterface.dll`.

### Решение: early mock в `tests/conftest.py`

```python
# Mock SimConnect and pyvjoy before any project module imports them at module level.
for _mod in ('SimConnect', 'pyvjoy', 'pyvjoy._sdk'):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
```

**Почему `conftest.py`:** pytest загружает conftest.py ДО сбора тестов. `sys.modules` mock гарантированно применяется до любого `import modules.*`. Это единственный безопасный точка входа — нельзя положиться на порядок импорта в тестах.

**Почему `MagicMock()`:** SimConnect и pyvjoy используются в production через `AircraftEvents`/`VirtualJoystick`. В тестах все вызовы идут через `tests/fakes.py` (FakeControl, FakeVJoy), которые не зависят от нативных модулей. MagicMock достаточно для прохождения импорта.

**Почему не `try/except ImportError`:** SimConnect импортируется на уровне модуля в `control.py` (`from SimConnect import AircraftEvents`). Если mock не применён до первого import — исключение уже выброшено. `sys.modules` mock — единственный способ перехватить это.

---

## 4. Проблема: хардкод пути в `test_architecture.py`

Файл `tests/test_architecture.py` содержал:

```python
class ArchitectureAnalyzer:
    def __init__(self, project_root: str = "C:/BAT/msfs_autoland"):
```

На CI (ubuntu) этот путь не существует → `FileNotFoundError`.

**Решение:**

```python
def __init__(self, project_root: str = None):
    if project_root is None:
        project_root = str(Path(__file__).resolve().parent.parent)
    self.project_root = Path(project_root)
```

`Path(__file__).resolve().parent.parent` вычисляет корень проекта относительно расположения теста — работает на любой OS.

---

## 5. История CI запусков

| Run ID | Время | Результат | Коммит | Описание |
|--------|-------|-----------|--------|----------|
| 29248732060 | 12:08 | **failure** | `19dbf0a` | pyvjoy `sys.exit()` + hardcoded path |
| 29248844308 | 12:10 | **failure** | `8d4bbef` | hardcoded path (pyvjoy исправлен) |
| 29248969029 | 12:12 | **success** | `9a15e2e` | все исправлено |

**Итеративный процесс:** 3 коммита, 3 прогона, каждый устранял конкретную ошибку.

---

## 6. Тесты в CI vs локально

| Метрика | Локально (Windows) | CI (Ubuntu) |
|---------|-------------------|-------------|
| Тестов | 251 | 251 |
| Пройдено | 251 | 251 |
| Провалено | 0 | 0 |
| Python | 3.14.5 | 3.12, 3.13 |
| SimConnect | реальный | mocked |
| pyvjoy | реальный | mocked |

**Разница:** локально SimConnect и pyvjoy реальные, в CI — замки. Все 251 тест используют `tests/fakes.py` (FakeControl, FakeVJoy, FakeAircraftAdapter) и не обращаются к нативным модулям напрямую. Тесты, требующие SimConnect (интеграционные с реальным контроллером), в suite отсутствуют — это осознанный выбор (unit/integration test approach).

---

## 7. Что НЕ покрывается CI

1. **SimConnect интеграция** — реальное чтение/запись SimVars. Требует Windows + MSFS SDK.
2. **pyvjoy интеграция** — реальная передача управления через vJoy. Требует Windows + vJoy driver.
3. **GUI** — `gui.py` использует tkinter. Не тестируется в CI.
4. **Replay fixtures** — 4 replay теста с JSONL-фиксустурами. Фикстуры в git, тесты проходят.

---

## 8. Рекомендации

1. **Python 3.14:** когда GitHub Actions поддержит 3.14 — добавить в матрицу. Сейчас 3.12/3.13.
2. **Windows CI:** если потребуется тестировать SimConnect/pyvjoy — добавить `runs-on: windows-latest` job с установкой SimConnect SDK. Но это значительно дороже (Windows runner стоит ~2x Linux).
3. **Coverage:** добавить `pytest-cov` для отслеживания покрытия. Сейчас не настроено.
4. **Pre-commit hooks:** можно добавить `pre-commit` с `ruff`/`black` для автоматического форматирования перед коммитом.
