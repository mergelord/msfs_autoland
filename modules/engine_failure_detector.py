"""
Детектор отказов двигателей для автоматического переключения
на асимметричное управление тягой
"""

import logging
import math
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _is_valid_number(value) -> bool:
    """Check if value is a finite numeric type (not bool)."""
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


@dataclass
class EngineState:
    """Состояние одного двигателя"""
    index: int  # Номер двигателя (1-4)
    running: bool  # Двигатель работает
    n1: float  # N1 (%) - скорость вентилятора/компрессора низкого давления
    n2: float  # N2 (%) - скорость турбины высокого давления
    egt: float  # EGT (°C) - температура выхлопных газов
    fuel_flow: float  # Расход топлива (фунты/час)
    oil_pressure: float  # Давление масла (PSI)
    throttle_position: float  # Положение РУД (0.0-1.0)

    # Флаги отказа
    failed: bool = False
    failure_reason: Optional[str] = None


@dataclass
class EngineFailureThresholds:
    """Пороговые значения для определения отказа двигателя"""
    min_n1_running: float = 20.0  # Минимальный N1 для работающего двигателя (%)
    min_n2_running: float = 30.0  # Минимальный N2 для работающего двигателя (%)
    max_egt: float = 900.0  # Максимальная EGT (°C)
    min_fuel_flow: float = 50.0  # Минимальный расход топлива (фунты/час)
    min_oil_pressure: float = 20.0  # Минимальное давление масла (PSI)

    # Время подтверждения отказа (секунды)
    failure_confirmation_time: float = 3.0


class EngineFailureDetector:
    """Детектор отказов двигателей"""

    def __init__(self, thresholds: Optional[EngineFailureThresholds] = None,
                 *, clock: Optional[Callable[[], float]] = None):
        self.thresholds = thresholds or EngineFailureThresholds()
        self._clock = clock or time.monotonic

        # Состояние двигателей
        self.engines: Dict[int, EngineState] = {}
        self.number_of_engines: int = 0

        # История отказов для подтверждения
        self.failure_history: Dict[int, List[float]] = {}  # engine_index -> [timestamps]

        # Статистика
        self.total_failures_detected: int = 0
        self.active_failures: List[int] = []  # Индексы отказавших двигателей

        # Rate-limited warning tracking for invalid telemetry
        self._warned_fields: set[Tuple[int, str]] = set()

    def initialize(self, number_of_engines: int):
        """
        Инициализация детектора для конкретного самолёта

        Args:
            number_of_engines: Количество двигателей (1-4)
        """
        self.number_of_engines = number_of_engines
        self.engines = {}
        self.failure_history = {}
        self.active_failures = []

        for i in range(1, number_of_engines + 1):
            self.engines[i] = EngineState(
                index=i,
                running=True,
                n1=0.0,
                n2=0.0,
                egt=0.0,
                fuel_flow=0.0,
                oil_pressure=0.0,
                throttle_position=0.0
            )
            self.failure_history[i] = []

        logger.info(f"Engine failure detector initialized for {number_of_engines} engines")

    def update_engine_data(self, telemetry: Dict):
        """
        Обновление данных двигателей из телеметрии

        Args:
            telemetry: Телеметрия от SimConnect
        """
        if not self.engines:
            # Автоинициализация если не была вызвана initialize()
            num_engines = telemetry.get('aircraft_info', {}).get('number_of_engines', 2)
            self.initialize(num_engines)

        # Обновление данных каждого двигателя
        for engine_idx in self.engines.keys():
            self._update_single_engine(engine_idx, telemetry)

    def _update_single_engine(self, engine_idx: int, telemetry: Dict):
        """
        Обновление данных одного двигателя

        Args:
            engine_idx: Индекс двигателя (1-4)
            telemetry: Телеметрия от SimConnect
        """
        engine = self.engines[engine_idx]

        # Чтение данных из телеметрии
        engine_data = telemetry.get('engines', {}).get(f'engine_{engine_idx}', {})

        # H2: Validate all required numeric fields and running flag
        numeric_fields = {
            'n1': engine_data.get('n1', 0.0),
            'n2': engine_data.get('n2', 0.0),
            'egt': engine_data.get('egt', 0.0),
            'fuel_flow': engine_data.get('fuel_flow', 0.0),
            'oil_pressure': engine_data.get('oil_pressure', 0.0),
            'throttle': engine_data.get('throttle', 0.0),
        }
        running_raw = engine_data.get('running', True)

        # Validate running must be a real bool
        if not isinstance(running_raw, bool):
            warn_key = (engine_idx, 'running')
            if warn_key not in self._warned_fields:
                self._warned_fields.add(warn_key)
                logger.warning(
                    f"Engine {engine_idx}: invalid telemetry field "
                    f"'running'={running_raw!r} — preserving previous state"
                )
            return

        # Validate all numeric fields
        for field, value in numeric_fields.items():
            if not _is_valid_number(value):
                warn_key = (engine_idx, field)
                if warn_key not in self._warned_fields:
                    self._warned_fields.add(warn_key)
                    logger.warning(
                        f"Engine {engine_idx}: invalid telemetry field "
                        f"'{field}'={value!r} — preserving previous state"
                    )
                return

        # All fields valid — apply and check failure
        engine.running = running_raw
        engine.n1 = numeric_fields['n1']
        engine.n2 = numeric_fields['n2']
        engine.egt = numeric_fields['egt']
        engine.fuel_flow = numeric_fields['fuel_flow']
        engine.oil_pressure = numeric_fields['oil_pressure']
        engine.throttle_position = numeric_fields['throttle']

        # Проверка на отказ
        self._check_engine_failure(engine)

    def _check_engine_failure(self, engine: EngineState):
        """
        Проверка двигателя на отказ

        Args:
            engine: Состояние двигателя
        """
        failure_detected = False
        failure_reason = None

        # Проверка 1: Двигатель не работает
        if not engine.running:
            failure_detected = True
            failure_reason = "Engine not running"

        # Проверка 2: N1 слишком низкий при открытом РУД
        elif engine.throttle_position > 0.3 and engine.n1 < self.thresholds.min_n1_running:
            failure_detected = True
            failure_reason = f"Low N1: {engine.n1:.1f}% (threshold: {self.thresholds.min_n1_running}%)"

        # Проверка 3: N2 слишком низкий
        elif engine.n2 < self.thresholds.min_n2_running and engine.throttle_position > 0.3:
            failure_detected = True
            failure_reason = f"Low N2: {engine.n2:.1f}% (threshold: {self.thresholds.min_n2_running}%)"

        # Проверка 4: Перегрев
        elif engine.egt > self.thresholds.max_egt:
            failure_detected = True
            failure_reason = f"Overheat: {engine.egt:.0f}°C (max: {self.thresholds.max_egt}°C)"

        # Проверка 5: Нет расхода топлива при открытом РУД
        elif engine.throttle_position > 0.3 and engine.fuel_flow < self.thresholds.min_fuel_flow:
            failure_detected = True
            failure_reason = f"No fuel flow: {engine.fuel_flow:.0f} lbs/hr"

        # Проверка 6: Низкое давление масла
        elif engine.oil_pressure < self.thresholds.min_oil_pressure and engine.running:
            failure_detected = True
            failure_reason = f"Low oil pressure: {engine.oil_pressure:.1f} PSI"

        # Подтверждение отказа (защита от ложных срабатываний)
        current_time = self._clock()

        if failure_detected:
            # Добавляем в историю
            self.failure_history[engine.index].append(current_time)

            # Удаляем старые записи (старше confirmation_time)
            self.failure_history[engine.index] = [
                t for t in self.failure_history[engine.index]
                if current_time - t < self.thresholds.failure_confirmation_time
            ]

            # Если отказ подтверждён несколькими проверками подряд
            if len(self.failure_history[engine.index]) >= 3:
                if not engine.failed:
                    # Новый отказ
                    engine.failed = True
                    engine.failure_reason = failure_reason
                    self.active_failures.append(engine.index)
                    self.total_failures_detected += 1

                    logger.critical(f"ENGINE {engine.index} FAILURE DETECTED: {failure_reason}")
                    logger.critical(f"N1={engine.n1:.1f}%, N2={engine.n2:.1f}%, "
                                  f"EGT={engine.egt:.0f}°C, Fuel={engine.fuel_flow:.0f}lbs/hr, "
                                  f"Oil={engine.oil_pressure:.1f}PSI, Throttle={engine.throttle_position*100:.0f}%")
        else:
            # Отказа нет - очищаем историю
            self.failure_history[engine.index] = []

            # Если двигатель восстановился
            if engine.failed:
                logger.warning(f"Engine {engine.index} recovered from failure")
                engine.failed = False
                engine.failure_reason = None
                if engine.index in self.active_failures:
                    self.active_failures.remove(engine.index)

    def has_engine_failure(self) -> bool:
        """
        Проверка наличия отказов двигателей

        Returns:
            True если есть хотя бы один отказавший двигатель
        """
        return len(self.active_failures) > 0

    def get_failed_engines(self) -> List[int]:
        """
        Получить список отказавших двигателей

        Returns:
            Список индексов отказавших двигателей
        """
        return self.active_failures.copy()

    def get_working_engines(self) -> List[int]:
        """
        Получить список работающих двигателей

        Returns:
            Список индексов работающих двигателей
        """
        return [idx for idx in self.engines.keys() if idx not in self.active_failures]

    def get_engine_state(self, engine_idx: int) -> Optional[EngineState]:
        """
        Получить состояние конкретного двигателя

        Args:
            engine_idx: Индекс двигателя (1-4)

        Returns:
            Состояние двигателя или None
        """
        return self.engines.get(engine_idx)

    def get_all_engines_state(self) -> Dict[int, EngineState]:
        """
        Получить состояние всех двигателей

        Returns:
            Словарь {engine_index: EngineState}
        """
        return self.engines.copy()

    def calculate_asymmetric_thrust_correction(self) -> Dict[str, float]:
        """
        Расчёт коррекции для асимметричной тяги

        Returns:
            Словарь с коррекциями для каждого двигателя
        """
        if not self.has_engine_failure():
            # Нет отказов - все двигатели одинаково
            return {f'engine_{i}': 1.0 for i in self.engines.keys()}

        working_engines = self.get_working_engines()
        failed_engines = self.get_failed_engines()

        corrections = {}

        # Отказавшие двигатели - 0% тяги
        for engine_idx in failed_engines:
            corrections[f'engine_{engine_idx}'] = 0.0

        # H5: All engines failed — no working engine for compensation
        if not working_engines:
            logger.critical(
                "ALL ENGINES FAILED — no working engine for asymmetric compensation"
            )
            return corrections

        # Работающие двигатели - компенсация
        # Увеличиваем тягу на работающих двигателях пропорционально
        compensation_factor = self.number_of_engines / len(working_engines)

        for engine_idx in working_engines:
            corrections[f'engine_{engine_idx}'] = min(1.0, compensation_factor)

        logger.info(f"Asymmetric thrust correction: {corrections}")

        return corrections

    def get_status(self) -> Dict:
        """Получить статус детектора"""
        return {
            'number_of_engines': self.number_of_engines,
            'active_failures': self.active_failures,
            'total_failures_detected': self.total_failures_detected,
            'has_failure': self.has_engine_failure(),
            'working_engines': self.get_working_engines(),
            'engines': {
                idx: {
                    'running': eng.running,
                    'failed': eng.failed,
                    'failure_reason': eng.failure_reason,
                    'n1': eng.n1,
                    'n2': eng.n2,
                    'egt': eng.egt
                }
                for idx, eng in self.engines.items()
            }
        }
