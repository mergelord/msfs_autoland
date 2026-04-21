"""
Компенсатор асимметричной тяги через руль направления
для самолётов с 2+ двигателями при отказе одного или нескольких двигателей
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class RudderCompensationConfig:
    """Конфигурация компенсации рулём направления"""
    # Коэффициенты компенсации
    thrust_asymmetry_factor: float = 0.015  # Руль на 1% асимметрии тяги
    speed_factor: float = 0.8  # Коррекция на скорость (меньше скорость = больше руль)
    reference_speed: float = 140.0  # Референсная скорость (узлы)

    # Ограничения
    max_rudder: float = 1.0  # Максимальное отклонение руля (100%)
    min_rudder: float = -1.0  # Минимальное отклонение руля (-100%)

    # Мёртвая зона
    asymmetry_deadzone: float = 0.05  # Игнорировать асимметрию < 5%

    # Динамика
    max_rudder_rate: float = 0.2  # Максимальная скорость изменения руля (за цикл)


class RudderCompensation:
    """
    Автоматическая компенсация асимметричной тяги рулём направления

    Физика:
    - Асимметричная тяга создаёт момент рыскания (yaw moment)
    - Руль направления создаёт противоположный момент
    - Компенсация зависит от: разницы тяги, расстояния двигателей от ЦТ, скорости
    """

    def __init__(self, config: Optional[RudderCompensationConfig] = None):
        self.config = config or RudderCompensationConfig()

        # Состояние
        self.active = False
        self.current_rudder = 0.0  # Текущее положение руля (-1.0 до +1.0)
        self.total_compensations = 0

        # Геометрия самолёта (будет обновляться)
        self.engine_arm: float = 10.0  # Расстояние двигателя от ЦТ (футы)
        self.number_of_engines: int = 2

    def activate(self):
        """Активация компенсатора"""
        self.active = True
        logger.info("Rudder compensation activated")

    def deactivate(self):
        """Деактивация компенсатора"""
        self.active = False
        self.current_rudder = 0.0
        logger.info("Rudder compensation deactivated")

    def reset(self):
        """Сброс состояния"""
        self.current_rudder = 0.0
        self.active = False
        logger.info("Rudder compensation reset")

    def set_aircraft_geometry(self, engine_arm: float, number_of_engines: int):
        """
        Установить геометрию самолёта

        Args:
            engine_arm: Расстояние двигателя от центра тяжести (футы)
            number_of_engines: Количество двигателей
        """
        self.engine_arm = engine_arm
        self.number_of_engines = number_of_engines
        logger.info(f"Aircraft geometry set: engine_arm={engine_arm}ft, engines={number_of_engines}")

    def calculate_thrust_asymmetry(self, engine_throttles: Dict[int, float]) -> float:
        """
        Расчёт асимметрии тяги

        Args:
            engine_throttles: Словарь {engine_index: throttle_percent}

        Returns:
            Асимметрия тяги (-1.0 до +1.0)
            Положительное значение = больше тяги справа (нужен левый руль)
            Отрицательное значение = больше тяги слева (нужен правый руль)
        """
        if not engine_throttles or len(engine_throttles) < 2:
            return 0.0

        # Для 2-двигательного самолёта
        if self.number_of_engines == 2:
            left_thrust = engine_throttles.get(1, 0.0)
            right_thrust = engine_throttles.get(2, 0.0)

            # Асимметрия = правый - левый
            asymmetry = right_thrust - left_thrust

            logger.debug(f"Thrust asymmetry (2-eng): L={left_thrust:.2f}, R={right_thrust:.2f}, "
                        f"asymmetry={asymmetry:+.2f}")

            return asymmetry

        # Для 4-двигательного самолёта
        elif self.number_of_engines == 4:
            # Двигатели: 1=левый внешний, 2=левый внутренний, 3=правый внутренний, 4=правый внешний
            left_outer = engine_throttles.get(1, 0.0)
            left_inner = engine_throttles.get(2, 0.0)
            right_inner = engine_throttles.get(3, 0.0)
            right_outer = engine_throttles.get(4, 0.0)

            # Взвешенная асимметрия (внешние двигатели имеют больший момент)
            left_total = left_outer * 1.5 + left_inner * 1.0
            right_total = right_outer * 1.5 + right_inner * 1.0

            asymmetry = (right_total - left_total) / 2.5  # Нормализация

            logger.debug(f"Thrust asymmetry (4-eng): L_out={left_outer:.2f}, L_in={left_inner:.2f}, "
                        f"R_in={right_inner:.2f}, R_out={right_outer:.2f}, asymmetry={asymmetry:+.2f}")

            return asymmetry

        # Для 3-двигательного (центральный + 2 боковых)
        elif self.number_of_engines == 3:
            left = engine_throttles.get(1, 0.0)
            center = engine_throttles.get(2, 0.0)  # Не создаёт момент
            right = engine_throttles.get(3, 0.0)

            asymmetry = right - left

            logger.debug(f"Thrust asymmetry (3-eng): L={left:.2f}, C={center:.2f}, R={right:.2f}, "
                        f"asymmetry={asymmetry:+.2f}")

            return asymmetry

        return 0.0

    def calculate_speed_correction(self, current_speed: float) -> float:
        """
        Коррекция на скорость

        При меньшей скорости требуется больше руля для той же компенсации

        Args:
            current_speed: Текущая скорость (узлы)

        Returns:
            Коэффициент коррекции (>1.0 при низкой скорости)
        """
        if current_speed <= 0:
            return 1.0

        # Обратная зависимость от скорости
        speed_ratio = self.config.reference_speed / current_speed

        # Применяем speed_factor для сглаживания
        correction = 1.0 + (speed_ratio - 1.0) * self.config.speed_factor

        # Ограничение (не более 2x коррекции)
        correction = max(0.5, min(2.0, correction))

        return correction

    def calculate_rudder_input(self,
                               engine_throttles: Dict[int, float],
                               current_speed: float,
                               current_rudder: float = 0.0) -> float:
        """
        Расчёт требуемого отклонения руля для компенсации асимметрии

        Args:
            engine_throttles: Тяга каждого двигателя {engine_index: throttle}
            current_speed: Текущая скорость (узлы)
            current_rudder: Текущее положение руля (-1.0 до +1.0)

        Returns:
            Требуемое положение руля (-1.0 до +1.0)
            Положительное = левый руль (компенсация правой тяги)
            Отрицательное = правый руль (компенсация левой тяги)
        """
        if not self.active:
            return 0.0

        # 1. Расчёт асимметрии тяги
        thrust_asymmetry = self.calculate_thrust_asymmetry(engine_throttles)

        # 2. Проверка мёртвой зоны
        if abs(thrust_asymmetry) < self.config.asymmetry_deadzone:
            logger.debug("Thrust asymmetry within deadzone, no rudder compensation needed")
            return 0.0

        # 3. Базовая компенсация руля
        # Положительная асимметрия (больше тяги справа) → положительный руль (влево)
        base_rudder = thrust_asymmetry * self.config.thrust_asymmetry_factor

        # 4. Коррекция на скорость
        speed_correction = self.calculate_speed_correction(current_speed)
        compensated_rudder = base_rudder * speed_correction

        # 5. Ограничение скорости изменения (плавность)
        rudder_change = compensated_rudder - current_rudder
        if abs(rudder_change) > self.config.max_rudder_rate:
            rudder_change = self.config.max_rudder_rate * (1 if rudder_change > 0 else -1)
            compensated_rudder = current_rudder + rudder_change

        # 6. Ограничение диапазона
        compensated_rudder = max(self.config.min_rudder, min(self.config.max_rudder, compensated_rudder))

        logger.info(f"Rudder compensation: asymmetry={thrust_asymmetry:+.2f}, "
                   f"speed={current_speed:.0f}kt, correction={speed_correction:.2f}, "
                   f"rudder={compensated_rudder:+.2f}")

        return compensated_rudder

    def apply_compensation(self,
                          engine_throttles: Dict[int, float],
                          current_speed: float,
                          control) -> bool:
        """
        Применить компенсацию руля

        Args:
            engine_throttles: Тяга каждого двигателя
            current_speed: Текущая скорость
            control: Экземпляр MSFSControl

        Returns:
            True если компенсация применена
        """
        if not self.active:
            return False

        # Расчёт требуемого руля
        new_rudder = self.calculate_rudder_input(
            engine_throttles,
            current_speed,
            self.current_rudder
        )

        # Применение через control
        if hasattr(control, 'set_rudder'):
            control.set_rudder(new_rudder)
            self.current_rudder = new_rudder
            self.total_compensations += 1
            return True
        else:
            logger.warning("Control does not support set_rudder method")
            return False

    def get_status(self) -> Dict:
        """Получить статус компенсатора"""
        return {
            'active': self.active,
            'current_rudder': self.current_rudder,
            'total_compensations': self.total_compensations,
            'engine_arm': self.engine_arm,
            'number_of_engines': self.number_of_engines
        }
