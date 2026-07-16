TASK: SETUP-DEPGRAPH-ENV
Контекст: подготовка окружения к задаче DEPGRAPH-3971ba1 (граф зависимостей modules/). По твоему PROBE RESULT: ast и networkx 3.6.1 уже на месте — их не трогать. Доустановить недостающее для рендера PNG/SVG.
Шаги (PowerShell):
Graphviz binary (dot):
winget install --id Graphviz.Graphviz -e
​
Если winget недоступен — choco install graphviz или скачать инсталлятор с graphviz.org. После установки перезапустить PowerShell и проверить, что dot попал в PATH; если нет — добавить C:\Program Files\Graphviz\bin в PATH вручную.
Python-пакет graphviz:
pip install graphviz
​
Проверка (все 4 команды, вывод вставить в отчёт):
python --version
python -c "import ast, networkx; print('networkx', networkx.__version__)"
python -c "import graphviz; print('graphviz-py', graphviz.__version__)"
dot -V
​
Смоук-тест рендера — создать и выполнить одноразовый скрипт:
python -c "import graphviz; g = graphviz.Digraph(); g.edge('a','b'); g.render('smoke_test', format='png', cleanup=True); print('render OK')"
​
Файл smoke_test.png после проверки удалить.
Ограничения:
Никаких изменений в репозитории C:\BAT\msfs_autoland — задача только про окружение.
Ничего не коммитить, не апгрейдить networkx и другие уже установленные пакеты.
Формат ответа: ENV_READY + вывод всех проверочных команд из шага 3 и результат смоук-теста. Если что-то не встало — ENV_BLOCKED + текст ошибки дословно.