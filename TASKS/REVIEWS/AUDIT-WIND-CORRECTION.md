AUDIT-WIND-CORRECTION
Проведи независимый fact-based safety-аудит модуля коррекции ветра.
Среда
Workdir: C:\BAT\msfs_autoland
Repository: zhuk-mou-1/msfs_autoland
Commit: e6fafffba4d6047e87664730cbc888738cceae62
Основной файл: modules/wind_correction.py
Отчёт: TASKS\REVIEWS\BENCH-AUDIT-WIND-CORRECTION.md
Ограничения
Используй только локальные исходники и локальные Python-probes.
Интернет и deep research не использовать.
Не читать предыдущие отчёты об этом модуле.
Не изменять production-код и тесты.
Не создавать ветку, commit, patch или PR.
TASKS\ не коммитить.
Максимум пять подтверждённых находок. Пустой результат лучше выдуманного.
Проверяемый scope
Прочитай:
modules/wind_correction.py;
production-вызов в main.py;
потребителей wind_data в modules/approach_phases.py;
все тесты, где встречаются:
WindCorrection;
apply_wind_corrections;
corrected_heading;
corrected_vs;
headwind;
crosswind.
1. Точная структура кода
Для каждого условного блока в calculate_corrected_heading() выпиши структурированный псевдокод с сохранением вложенности.
Особенно укажи, к какому if относится каждый else.
Не делай вывод о поведении до проверки реальных отступов.
2. Компоненты ветра
Проверь авиационную конвенцию:
направление ветра означает, откуда он дует;
headwind > 0 — встречный;
crosswind > 0 — ветер справа согласно docstring.
Выполни probes для desired track:
0°;
90°;
180°;
270°.
Для каждого курса проверь:
ветер точно спереди;
сзади;
слева;
справа.
Выведи headwind, crosswind и ожидаемое физическое направление коррекции курса.
3. Corrected heading
Для TAS=120 kt, wind=20 kt выполни минимум четыре симметричных примера.
Для каждого покажи:
desired track;
wind direction;
computed crosswind;
фактический результат функции;
ожидаемый heading;
объяснение, должен ли самолёт направить нос влево или вправо.
Не используй только комментарии в коде как доказательство — проверь геометрию вектора ветра.
4. Drift/crab consistency
Сопоставь:
calculate_drift_angle;
calculate_crab_angle;
calculate_corrected_heading.
Установи:
согласованы ли их знаки между собой;
согласованы ли они с docstring;
согласованы ли они с физической компенсацией ветра.
Если методы внутренне согласованы, но используют неверную физическую конвенцию, укажи это отдельно.
5. Vertical speed
Проверь:
base_vs = calculate_descent_rate(ground_speed, angle)
vs_correction = calculate_pitch_correction(...)
corrected_vs = base_vs + vs_correction
​
Ответь:
какие параметры calculate_pitch_correction реально используются;
учитывает ли фактическая ground speed ветер уже сама;
не происходит ли повторный учёт headwind;
согласован ли знак correction с последующим:
set_vertical_speed(-int(vs))
​
Не предлагай физическую формулу без размерностного вывода.
6. Production usage и dead code
Для каждого публичного метода дай один статус:
production-used;
result-produced-but-not-consumed;
tests-only;
dead/unreferenced.
Отдельно проверь потребление полей:
drift_angle;
recommended_bank;
base_vs;
vs_correction;
corrected_vs.
Метод, который вызывается, нельзя называть dead, даже если его результат дальше не используется.
7. Валидация
Проверь:
TAS/GS ≤0;
отрицательную wind speed;
NaN/inf;
abs(crosswind) > TAS;
glideslope angle ≤0, около 90° и ≥90°.
Разделяй:
исключение;
огромное конечное значение;
silent corruption;
безопасный fallback.
Не утверждай наличие OverflowError, пока не воспроизведёшь его probe.
8. Тестовое покрытие
Проверь реальные assertions, а не имена тестов.
Укажи:
есть ли прямое создание WindCorrection;
есть ли real pipeline test;
какие тесты используют mocks;
есть ли nonzero-wind tests;
есть ли проверки обоих знаков crosswind.
Не указывай процент покрытия без запуска coverage.
Формат находки
Для каждой:
ID WCB-01, WCB-02, …
Severity P0/P1/P2/P3.
Статус ПОДТВЕРЖДЕНО / ПРЕДПОЛОЖЕНИЕ / ОПРОВЕРГНУТО.
Точные файл и строки.
Точная цитата.
Production call path.
Выполненный probe и его stdout.
Ожидаемый результат с обоснованием.
Последствие.
Минимальное направление исправления.
Regression test.
Самопроверка перед ответом
Проверь:
не перепутана ли вложенность if/else;
не назван ли вызываемый метод dead;
не заявлено ли исключение без воспроизведения;
не противоречит ли вывод собственной цитате;
не используется ли документация вместо production call path;
отделена ли ошибка реализации от спорной физической модели.
Итог
Дай:
findings;
отвергнутые тревоги;
таблицу использования методов и полей;
результаты probes;
матрицу тестов;
вердикт SAFE AS IS / SAFE WITH P2-P3 DEBT / FIX BEFORE SIM / NO-GO;
статус COMPLETED_NO_CHANGES.