# Задача: Аудит регрессии `main.py` — изменения Wave 1 (commit 59d5118)

## Контекст
`main.py` — точка интеграции, через которую проходит несколько фиксов Wave 1. Часть изменений в этом файле уже независимо аудирована отдельными задачами:
- Конвертация веса/длины ВПП в `_calculate_approach_speeds` (строки ~488-498, FIX-05/FIX-08) — аудирована в `TASK-ALISA-AUDIT-autothrottle`. По итогам подтверждена реальная межмодульная регрессия единиц измерения (kg vs lbs между `main.py` и `modules/autothrottle.py` через `modules/approach_phases.py._get_aircraft_weight`).
- Замена `is not None` на `_is_finite_number(...)` при построении `has_altitude/has_radio_height/has_airspeed/has_vs/has_bank` для `safety_guard.evaluate()` (строки ~734-740) — аудирована в `TASK-ALISA-AUDIT-safety_guard`. Подтверждена как корректный фикс, с отдельно найденным косметическим несоответствием (другой блок логирования "GUARD SNAPSHOT" в этом же файле по-прежнему использует `is not None`, а не `_is_finite_number` — чисто логирование, не влияет на решение guard).

**Эта задача НЕ должна повторять уже проделанную работу по этим двум блокам.** Примите их выводы как данные (можно кратко сверить, что код в текущем `main.py` на commit `59d5118779ec18017b138a09b172f5c321ec1dbe` не отличается от того, что видели в прошлых аудитах — но не переаудировать логику заново). Сфокусируйтесь на остальном диффе `main.py` и на целостности файла в целом.

Полный diff `main.py` из PR #5 (подтверждён через GitHub API):
```diff
@@ -36,7 +36,7 @@
 from modules.synthetic_glidepath import SyntheticGlidepath
 from modules.wind_correction import WindCorrection
 from modules.wind_shear_detector import WindShearDetector
-from modules.safety_guard import ApproachSafetyGuard, SafetySnapshot, GuardDecision
+from modules.safety_guard import ApproachSafetyGuard, SafetySnapshot, GuardDecision, _is_finite_number
 from modules.telemetry_recorder import TelemetryRecorder
@@ -448,9 +448,9 @@ def execute_go_around(self):
         self.control.set_flaps(2)
         logger.info("Go-around: Flaps to takeoff position")
 
-        # F3: real gear UP command (was a comment before)
-        self.control.set_gear(False)
-        logger.info("Go-around: Gear UP")
+        # F3: real gear UP command
+        self.control.set_gear(False)
+        logger.info("Go-around: Gear UP")
 
         # 5. Если vJoy доступен, центрируем управление
         if self.use_vjoy:
@@ -475,6 +475,7 @@ def _calculate_approach_speeds(self, config: ApproachConfig):
         # Получение телеметрии
         telemetry = self.telemetry.get_all_data()
         weather = telemetry.get('weather', {})
+        weight_data = telemetry.get('weight', {})
         aircraft = telemetry.get('aircraft', {})
         ... (уже аудировано отдельной задачей — см. выше)
@@ -724,11 +734,11 @@ def _handle_phase(self, telemetry: dict, approach_data: dict):
         ... (уже аудировано отдельной задачей — см. выше)
```

## Область аудита
**В скоупе:**
1. Новый импорт `_is_finite_number` в шапке файла — проверить ВСЕ места использования этой функции по всему `main.py`, а не только уже аудированный блок `_handle_phase`. В частности: есть ли другой блок логирования ("GUARD SNAPSHOT", уже выявлен как F1 в прошлом аудите — использует `is not None`, не `_is_finite_number`) или иные места, которые ДОЛЖНЫ бы использовать `_is_finite_number` для консистентности, но не используют? Составить полный список.
2. Комментарий `# F3: real gear UP command (was a comment before)` → `# F3: real gear UP command` в `execute_go_around` — подтвердить документально, что это ИСКЛЮЧИТЕЛЬНО изменение текста комментария, без изменения кода/логики/поведения `execute_go_around`.
3. Строка `weight_data = telemetry.get('weight', {})` — новая переменная, добавленная в `_calculate_approach_speeds`. Она в скоупе только в части: используется ли она где-либо ЕЩЁ в файле (не только в уже аудированном участке конвертации веса)? Убедиться, что нет второго независимого использования `weight_data`, которое осталось незамеченным в прошлом аудите.
4. Общая целостность файла: пройти по всему `main.py` (не только изменённым строкам) и проверить, есть ли другие места, ссылающиеся на переменные/поля, изменённые в Wave 1 (`total_weight`, `aircraft_weight_kg`, `runway_length`, `has_altitude`/`has_radio_height`/`has_airspeed`/`has_vs`/`has_bank`, `_is_finite_number`), которые могли быть упущены при точечных аудитах autothrottle/safety_guard.

**Вне скоупа:** повторный аудит логики конвертации веса/длины ВПП (строки ~488-498) и построения `has_*` флагов для `safety_guard.evaluate()` (строки ~734-740) — эти находки уже приняты из прошлых отчётов, не пересматривать заново.

## Вопросы для аудита (схема regression-sentinel, как в прошлых аудитах)
- **Q1**: Комментарий-фикс (F3) закрыт по сути — действительно нет скрытого изменения поведения под видом переформулировки комментария?
- **Q2**: Нет ли новых регрессий вне уже аудированных блоков — например, конфликт имён из-за нового импорта `_is_finite_number`, неиспользуемая или неправильно использованная `weight_data` где-то ещё, или другие ранее непримеченные изменения в диффе.
- **Q3**: Есть ли тестовое покрытие для оставшихся изменений `main.py` (импорт, комментарий, новая переменная `weight_data` вне уже покрытого пути)?
- **Q4**: Рассогласование кода/тестов/CI по всему файлу `main.py` в текущей версии commit `59d5118`.

## Важное требование
Любые гипотезы о межмодульном влиянии — только через точную трассировку по реальному коду (см. прецедент autothrottle, где трассировка подтвердила настоящую регрессию единиц измерения). Не переоткрывайте и не пересматривайте уже подтверждённые находки из прошлых аудитов (вес/длина ВПП, has_* flags) — используйте их как принятый контекст.

## Формат отчёта
Тот же формат: таблица находок, вердикты по Q1-Q4, итоговая сводная таблица, рекомендации. Если весь оставшийся (неаудированный ранее) дифф `main.py` тривиален и не порождает находок — это нормальный валидный результат ("чисто"), не нужно искусственно находить проблемы.
