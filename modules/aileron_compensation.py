"""
Компенсация крена элеронами при асимметричной тяге
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional
from modules.aircraft_geometry import AircraftGeometry

logger = logging.getLogger(__name__)


@dataclass
class AileronCompensationConfig:
    """Конфигурация компенсации крена"""
    # Коэффициенты
    direct_roll_factor: float = 0.01      # Прямой момент крена от тяги
    induced_roll_factor: float = 0.3      # Индуцированный крен от руля
    speed_factor: float = 0.8             # Коррекция на скорость
    reference_speed: float = 140.0        # Референсная скорость (узлы)

    # Ограничения
    max_aileron: float = 1.0
    min_aileron: float = -1.0
    max_aileron_rate: float = 0.15        # Скорость изменения

    # Мёртвая зона
    roll_deadzone: float = 0.02           # Игнорировать момент < 2%


class AileronCompensation:
    """Компенсация крена элеронами при асимметричной тяге"""

    def __init__(self, config: Optional[AileronCompensationConfig] = None,
                 aircraft_geometry: Optional[AircraftGeometry] = None):
        self.config = config or AileronCompensationConfig()
        self.aircraft_geometry = aircraft_geometry

        self.active = False
        self.current_aileron = 0.0
        self.total_compensations = 0

    def activate(self):
        """Активация компенсатора"""
        self.active = True
        logger.info("Aileron compensation activated")

    def deactivate(self):
        """Деактивация компенсатора"""
        self.active = False
        self.current_aileron = 0.0
        logger.info("Aileron compensation deactivated")

    def set_aircraft_geometry(self, geometry: AircraftGeometry):
        """Установить геометрию самолёта"""
        self.aircraft_geometry = geometry
        logger.info(f"Aircraft geometry set: {geometry.number_of_engines} engines")

    def calculate_direct_roll_moment(self, engine_throttles: Dict[int, float]) -> float:
        """
        Расчёт прямого момента крена от асимметричной тяги

        Момент = Σ(Thrust_i × vertical_arm_i)
        """
        if not self.aircraft_geometry:
            return 0.0

        total_moment = 0.0

        for engine_idx, throttle in engine_throttles.items():
            pos = self.aircraft_geometry.get_engine_position(engine_idx)

            # Момент = тяга × вертикальное плечо
            # Положительный vertical_arm (двигатель выше ЦТ) + тяга справа = крен вправо
            moment = throttle * pos.vertical_arm * (1 if pos.lateral_arm > 0 else -1)
            total_moment += moment

        logger.debug(f"Direct roll moment: {total_moment:.3f}")
        return total_moment

    def calculate_induced_roll_moment(self, rudder_deflection: float) -> float:
        """
        Расчёт индуцированного момента крена от руля направления

        Руль создаёт боковую силу выше ЦТ → момент крена
        """
        if not self.aircraft_geometry:
            return 0.0

        # Индуцированный момент пропорционален отклонению руля и высоте киля
        induced_moment = rudder_deflection * self.aircraft_geometry.vertical_stabilizer_height * 0.01

        logger.debug(f"Induced roll moment from rudder: {induced_moment:.3f}")
        return induced_moment

    def calculate_aileron_input(self,
                                engine_throttles: Dict[int, float],
                                rudder_deflection: float,
                                current_speed: float,
                                current_aileron: float = 0.0) -> float:
        """
        Расчёт требуемого отклонения элеронов

        Args:
            engine_throttles: Тяга каждого двигателя
            rudder_deflection: Текущее отклонение руля (-1.0 до +1.0)
            current_speed: Текущая скорость (узлы)
            current_aileron: Текущее положение элеронов

        Returns:
            Требуемое положение элеронов (-1.0 до +1.0)
        """
        if not self.active or not self.aircraft_geometry:
            return 0.0

        # 1. Прямой момент крена от асимметричной тяги
        direct_moment = self.calculate_direct_roll_moment(engine_throttles)

        # 2. Индуцированный момент крена от руля
        induced_moment = self.calculate_induced_roll_moment(rudder_deflection)

        # 3. Общий момент крена
        total_moment = direct_moment + induced_moment

        # 4. Проверка мёртвой зоны
        if abs(total_moment) < self.config.roll_deadzone:
            return 0.0

        # 5. Базовая компенсация элеронами
        base_aileron = -total_moment * self.config.direct_roll_factor

        # 6. Коррекция на скорость
        if current_speed > 0:
            speed_ratio = self.config.reference_speed / current_speed
            speed_correction = 1.0 + (speed_ratio - 1.0) * self.config.speed_factor
            speed_correction = max(0.5, min(2.0, speed_correction))
        else:
            speed_correction = 1.0

        compensated_aileron = base_aileron * speed_correction

        # 7. Учёт эффективности элеронов
        compensated_aileron /= self.aircraft_geometry.aileron_effectiveness

        # 8. Ограничение скорости изменения
        aileron_change = compensated_aileron - current_aileron
        if abs(aileron_change) > self.config.max_aileron_rate:
            aileron_change = self.config.max_aileron_rate * (1 if aileron_change > 0 else -1)
            compensated_aileron = current_aileron + aileron_change

        # 9. Ограничение диапазона
        compensated_aileron = max(self.config.min_aileron,
                                 min(self.config.max_aileron, compensated_aileron))

        logger.info(f"Aileron compensation: direct={direct_moment:.3f}, "
                   f"induced={induced_moment:.3f}, aileron={compensated_aileron:+.2f}")

        return compensated_aileron

    def apply_compensation(self,
                          engine_throttles: Dict[int, float],
                          rudder_deflection: float,
                          current_speed: float,
                          control) -> bool:
        """Применить компенсацию элеронов"""
        if not self.active:
            return False

        new_aileron = self.calculate_aileron_input(
            engine_throttles,
            rudder_deflection,
            current_speed,
            self.current_aileron
        )

        if hasattr(control, 'set_aileron'):
            control.set_aileron(new_aileron)
            self.current_aileron = new_aileron
            self.total_compensations += 1
            return True
        else:
            logger.warning("Control does not support set_aileron method")
            return False

    def get_status(self) -> Dict:
        """Получить статус компенсатора"""
        return {
            'active': self.active,
            'current_aileron': self.current_aileron,
            'total_compensations': self.total_compensations,
            'has_geometry': self.aircraft_geometry is not None
        }
