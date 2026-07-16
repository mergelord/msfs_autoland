TASK: PROBE-RUNTIME-ARCHITECTURE-3971ba1
Цель
Определить, способен ли ты построить для проекта msfs_autoland достоверную блок-схему:
порядка исполнения и lifecycle;
потоков данных;
переходов фаз захода;
формирования и передачи управляющих команд;
safety/fail-safe, go-around и manual takeover.
Это только capability probe. Полную схему сейчас не строить.
Baseline
Repository: zhuk-mou-1/msfs_autoland
Branch: master
Commit: 3971ba12113d8994665b1c9a172f2dca6c9e3855
Рабочий каталог: C:\BAT\msfs_autoland
Существующий DEPGRAPH уже построен и принят.
В репозитории ничего не изменять.
Не создавать commit.
Не исправлять найденные баги.
Что потребуется в полной задаче
Будущая работа должна будет построить следующие артефакты:
execution-flow.mmd/png
запуск GUI;
создание AutoLandSystem;
инициализация компонентов;
подключение к MSFS;
загрузка конфигурации;
основной цикл;
shutdown.
phase-state-machine.mmd/png
все фазы захода;
условия переходов;
go-around, abort и takeover;
источник каждого условия.
data-flow.mmd/png
SimConnect/WASM → telemetry;
нормализация и валидация;
navigation/ILS/FMS;
phase logic;
corrections;
safety;
управляющая команда.
command-flow.mmd/png
источник решения;
CommandGateway;
ControlOwnership;
safety clamps;
control / virtual_joystick / WASM / SimConnect;
конфликтующие записи в одном кадре;
feedback.
safety-flow.mmd/png
stale/missing telemetry;
потеря соединения;
потеря ILS;
нестабилизированный заход;
wind shear/turbulence;
engine failure;
исключения;
go-around;
manual takeover.
runtime-architecture.json
узлы и рёбра;
тип ребра: call, read, write, state_transition, command, fallback;
source_file, source_line, target_file, target_line;
условие;
уровень подтверждения.
RUNTIME-ARCHITECTURE-REPORT.md
выводы;
скрытые зависимости через self.system.*;
неподключённые подсистемы;
конфликтующие команды;
непроверенные и недостижимые пути;
блокеры полётных испытаний.
Требования к достоверности
Каждое значимое ребро должно иметь доказательство:
source_file:line → target_file:line
​
Уровень доказательства должен быть обозначен отдельно:
STATIC_CONFIRMED;
TEST_CONFIRMED;
RUNTIME_CONFIRMED;
INFERRED;
UNREACHED;
DEAD.
Не считать импорт доказательством фактического вызова или подключения подсистемы.
Особенно проследить скрытые зависимости через:
self.system.*;
callbacks;
GUI signals;
shared mutable state;
lazy initialization;
direct writes в SimConnect/WASM/virtual joystick.
Capability probe
Не выполняя полную задачу, сделай только следующее.
1. Environment check
Сообщи, доступны ли:
Python AST;
networkx;
Graphviz dot;
Mermaid renderer, если есть;
запуск pytest;
чтение всего repository tree;
поиск по исходникам;
возможность написать локальный tracing/test harness без изменения production-кода.
2. Мини-доказательство статической трассировки
На реальном коде commit 3971ba1 найди и покажи с файлами и строками:
где создаётся AutoLandSystem;
где запускается основной update/control loop;
один полный путь от чтения telemetry до отправки управляющей команды;
один переход между фазами захода;
один путь manual takeover или go-around;
одно взаимодействие через self.system.*, которое не видно в import graph.
Не нужно исследовать все ветки.
3. Проверка возможности динамической верификации
Ответь отдельно:
можно ли запустить значимые сценарии без MSFS;
какие зависимости придётся mock/stub;
можно ли перехватить все вызовы Control/SimConnect/WASM/virtual joystick;
можно ли определить порядок записей команд внутри одного кадра;
что невозможно подтвердить без работающего MSFS.
4. Оценка объёма
Дай реалистичную оценку:
количество файлов, которые потребуется просмотреть;
ожидаемое число узлов и рёбер;
ориентировочное время;
рекомендуемое разбиение на этапы;
риск переполнения контекста;
какие части лучше выполнять отдельными проходами.
Строгий формат ответа
Начни ровно с одного статуса:
PROBE_RESULT: CAPABLE
​
или
PROBE_RESULT: PARTIALLY_CAPABLE
​
или
PROBE_RESULT: NOT_CAPABLE
​
Затем разделы:
ENVIRONMENT
STATIC_TRACE_SAMPLE
DYNAMIC_VALIDATION
LIMITATIONS
EXECUTION_PLAN
ESTIMATE
FINAL_JUSTIFICATION
​
Критерий CAPABLE
Ставь CAPABLE только если ты можешь:
проанализировать весь production-код;
проследить вызовы и данные, а не только импорты;
дать file:line evidence;
различать статически найденный и runtime-подтверждённый путь;
построить все пять схем и JSON-реестр;
обнаружить прямые и скрытые отправки управляющих команд;
честно отметить то, что нельзя подтвердить без MSFS.
Если можешь построить только статические схемы, но не динамическую верификацию, ставь PARTIALLY_CAPABLE.
Запреты
Не строить сейчас полные схемы.
Не менять production-код.
Не делать commit.
Не исправлять баги.
Не пересказывать Mermaid в чат.
Не заявлять о runtime-подтверждении без фактического запуска соответствующего пути.