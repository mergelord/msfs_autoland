TASK: AUDIT-NAVIGATION-MIMO
Проведи независимый fact-based code review и safety-аудит навигационной математики проекта msfs_autoland.
Среда
Рабочий каталог: C:\BAT\msfs_autoland
Репозиторий: zhuk-mou-1/msfs_autoland
Проверяемый commit: e6fafffba4d6047e87664730cbc888738cceae62
Основной файл: modules/navigation.py
Отчёт: TASKS\REVIEWS\AUDIT-NAVIGATION-e6fafff.md
TASKS\ — локальная папка, не коммитить.
Жёсткие ограничения
Не изменять production-код и тесты.
Не создавать ветку, коммит, PR или patch.
Работать против точного указанного commit.
Перед началом подтвердить:
текущий HEAD;
чистоту tracked-дерева;
наличие только допустимого untracked TASKS\.
Если рабочий checkout не на нужном commit, используй отдельный detached worktree.
Не используй отчёты Алисы и предыдущие выводы как источник фактов.
Каждое утверждение подтверждай реальным кодом, вызовом или тестом.
Связанный scope
Для проверки контрактов и production-достижимости прочитай:
modules/types.py;
modules/approach_phases.py;
modules/synthetic_glidepath.py;
modules/autopilot_takeover.py;
modules/ils_navigation.py;
main.py;
релевантные тесты, включая:
tests/test_loc_approach.py;
tests/test_runway_units.py;
tests/test_synthetic_glidepath.py;
tests/test_p0_p1_contract.py;
VOR/NDB replay-тесты и fixtures.
Обязательно прочитай navigation.py полностью, включая код после calculate_runway_beacons().
1. Геодезическая математика
Проверь:
calculate_distance;
calculate_bearing;
normalize_angle;
angle_difference.
Граничные случаи:
одинаковые координаты;
переход долготы через ±180°;
полюса;
antipodal и почти antipodal точки;
координаты вне допустимого диапазона;
отрицательные/большие углы;
NaN/inf.
Отдельно проверь, может ли floating-point rounding вывести аргумент asin(sqrt(a)) за допустимый диапазон.
2. VOR/NDB guidance
Проверь:
calculate_vor_approach;
calculate_ndb_approach;
calculate_intercept_heading.
Нужно установить:
правильность радиала;
порядок аргументов и знак cross_track_error;
направление коррекции вправо/влево;
корректность final_approach_course;
используется ли nav_data;
оправдано ли полное делегирование NDB в VOR-алгоритм;
поведение до, над и после пролёта станции;
скачки радиала около станции;
реальный production call path.
Для каждого подозрения на ошибку знака дай числовой воспроизводимый пример.
3. Вертикальный профиль
Проверь:
calculate_descent_rate;
calculate_required_altitude;
calculate_glideslope_distance;
calculate_glideslope_intercept_point;
should_start_descent;
get_glideslope_info.
Особое внимание:
знак vertical speed;
knots, ft/min, ft/NM;
AGL против MSL;
нулевой, отрицательный, почти нулевой и ≥90° угол;
отрицательная высота/дистанция;
деление на ноль;
расчёт ideal_altitude;
расстояние до intercept point против расстояния до порога;
согласованность с synthetic_glidepath.py;
вычисления, которые сразу перезаписываются и не влияют на результат.
4. Координаты glideslope intercept point
Проверь используемое приближение координат:
точность на обычных и высоких широтах;
cos(latitude) → 0 около полюсов;
переход долготы через ±180°;
знак reverse heading;
согласованность полученной точки с calculate_distance;
приемлемость ошибки на реальных дистанциях захода.
Отделяй допустимое приближение от safety-дефекта.
5. Посадочная дистанция
Проверь calculate_landing_distance:
ground_speed=0;
отрицательные и очень малые скорости;
headwind и tailwind;
экстремальный ветер;
неизвестный runway_condition;
нулевой/отрицательный вес;
NaN/inf;
физический и размерностный смысл формулы;
production-вызов и фактические аргументы.
Не смешивай этот анализ с ранее известным вопросом kg/lbs в другом модуле: фиксируй только самостоятельный дефект контракта navigation.py.
6. Проверка длины ВПП
Проверь check_runway_length:
единицы required_distance и runway_length;
контракт ApproachConfig.runway_length;
runway length ≤0;
safety margin ≤0;
согласованность is_sufficient и статуса;
достижимость OK, WARNING, CRITICAL;
margin_percent;
NaN/inf.
7. Runway beacons
Проверь полный beacon-контур:
outer/inner coordinates;
расстояния;
ожидаемые высоты;
частоты;
AGL/MSL;
курс, скорость и допуски;
passed;
timestamp;
повторные вызовы;
reset/state lifecycle;
production call paths.
8. Валидация и отказоустойчивость
Для всех публичных методов проверь:
отсутствующие ключи;
неверные типы;
NaN/inf;
KeyError, ValueError, ZeroDivisionError;
fail-safe, fail-closed или silent corruption;
реакцию основного цикла на исключение;
возможность перехода в error-budget/go-around после takeover.
Не предлагай blanket try/except; укажи правильную точку валидации.
9. Мёртвый код и реальные вызовы
Для каждого публичного метода классифицируй:
production-used;
tests-only;
dead/unreferenced.
Отдельно найди:
неиспользуемые аргументы;
перезаписываемые вычисления;
дублирование с ils_navigation.py;
дублирование с synthetic_glidepath.py.
10. Тестовое покрытие
Проверяй фактические assertions, а не названия файлов.
Оцени покрытие:
distance/bearing;
wrap углов;
знак intercept heading;
VOR/NDB production paths;
пролёт станции;
glideslope edge cases;
ground_speed=0;
runway units/status;
beacon logic;
NaN/inf;
высокие широты.
При необходимости запусти существующие тесты и отдельные read-only Python probes. Не добавляй тесты в репозиторий.
Формат каждой находки
Для каждой находки:
ID NAV-01, NAV-02, …
Severity: P0/P1/P2/P3.
Статус: ПОДТВЕРЖДЕНО / ПРЕДПОЛОЖЕНИЕ / НЕ ДОКАЗАНО.
Точные файл и строки.
Точная цитата кода.
Production call path.
Числовой воспроизводимый пример.
Фактическое последствие.
Минимальное направление исправления.
Необходимый regression test.
Обязательные разделы отчёта
Проверенный commit и состояние checkout.
Архитектурное резюме.
Подтверждённые находки по severity.
Предположения отдельно.
Рассмотренные и отвергнутые тревоги.
Таблица production-used / tests-only / dead.
Матрица тестового покрытия.
Команды и результаты probes/tests.
Итоговый вердикт:
SAFE AS IS;
SAFE WITH P2-P3 DEBT;
FIX BEFORE SIM;
NO-GO.
Критерий качества
Не нужно обязательно находить дефекты. Пустой результат лучше недоказанной находки. Перед финализацией проверь, что:
каждая цитата существует;
номер строки соответствует указанному commit;
вывод не противоречит цитате;
production path действительно достижим;
предположение не выдано за подтверждённый дефект.
Финальный статус задачи: COMPLETED_NO_CHANGES либо STOPPED_ON_GATE.