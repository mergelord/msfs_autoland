"""
Геометрия самолёта для расчёта моментов при асимметричной тяге
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class EnginePosition:
    """
    Положение двигателя относительно центра тяжести (ЦТ)

    Система координат (стандартная авиационная):
    - X-axis: продольная ось (нос → хвост, положительно вперёд)
    - Y-axis: поперечная ось (левое крыло → правое крыло, положительно вправо)
    - Z-axis: вертикальная ось (вниз → вверх, положительно вверх)
    """
    lateral_arm: float      # Расстояние по Y-axis (футы), + вправо, - влево
    vertical_arm: float     # Расстояние по Z-axis (футы), + вверх, - вниз
    longitudinal_arm: float # Расстояние по X-axis (футы), + вперёд, - назад

    def __post_init__(self):
        """Валидация значений"""
        if abs(self.lateral_arm) > 100:
            raise ValueError(f"lateral_arm слишком большой: {self.lateral_arm} футов")
        if abs(self.vertical_arm) > 50:
            raise ValueError(f"vertical_arm слишком большой: {self.vertical_arm} футов")
        if abs(self.longitudinal_arm) > 100:
            raise ValueError(f"longitudinal_arm слишком большой: {self.longitudinal_arm} футов")


@dataclass
class AircraftGeometry:
    """
    Геометрия самолёта для расчёта моментов

    Используется для точного расчёта:
    - Момента рыскания (yaw) от асимметричной тяги
    - Момента крена (roll) от асимметричной тяги
    - Момента тангажа (pitch) от асимметричной тяги
    - Индуцированного крена от руля направления
    """
    number_of_engines: int
    engine_positions: Dict[int, EnginePosition]

    # Высота вертикального стабилизатора над ЦТ (для индуцированного крена)
    vertical_stabilizer_height: float  # футы

    # Эффективность управляющих поверхностей (для расчёта требуемых отклонений)
    aileron_effectiveness: float = 1.0   # Относительная эффективность элеронов
    rudder_effectiveness: float = 1.0    # Относительная эффективность руля

    # Аэродинамические характеристики
    dihedral_angle: float = 3.0          # Угол поперечного V крыла (градусы)

    def __post_init__(self):
        """Валидация геометрии"""
        if self.number_of_engines < 1 or self.number_of_engines > 4:
            raise ValueError(f"Поддерживается 1-4 двигателя, получено: {self.number_of_engines}")

        if len(self.engine_positions) != self.number_of_engines:
            raise ValueError(f"Количество позиций двигателей ({len(self.engine_positions)}) "
                           f"не совпадает с number_of_engines ({self.number_of_engines})")

        if self.vertical_stabilizer_height <= 0:
            raise ValueError(f"vertical_stabilizer_height должна быть > 0: {self.vertical_stabilizer_height}")

    def get_engine_position(self, engine_index: int) -> EnginePosition:
        """Получить позицию конкретного двигателя"""
        if engine_index not in self.engine_positions:
            raise ValueError(f"Двигатель {engine_index} не найден в геометрии")
        return self.engine_positions[engine_index]

    def calculate_yaw_moment_arm(self, engine_index: int) -> float:
        """
        Расчёт плеча момента рыскания для двигателя

        Returns:
            Плечо момента (футы), положительное значение
        """
        pos = self.get_engine_position(engine_index)
        return abs(pos.lateral_arm)

    def calculate_roll_moment_arm(self, engine_index: int) -> float:
        """
        Расчёт плеча момента крена для двигателя

        Returns:
            Плечо момента (футы), положительное значение
        """
        pos = self.get_engine_position(engine_index)
        return abs(pos.vertical_arm)

    def calculate_pitch_moment_arm(self, engine_index: int) -> float:
        """
        Расчёт плеча момента тангажа для двигателя

        Returns:
            Плечо момента (футы), положительное значение
        """
        pos = self.get_engine_position(engine_index)
        return abs(pos.longitudinal_arm)


# Предопределённые геометрии для популярных самолётов

BOEING_737_GEOMETRY = AircraftGeometry(
    number_of_engines=2,
    engine_positions={
        1: EnginePosition(lateral_arm=-10.0, vertical_arm=-5.0, longitudinal_arm=0.0),  # Левый
        2: EnginePosition(lateral_arm=+10.0, vertical_arm=-5.0, longitudinal_arm=0.0)   # Правый
    },
    vertical_stabilizer_height=15.0,
    aileron_effectiveness=1.0,
    rudder_effectiveness=1.0,
    dihedral_angle=3.0
)

AIRBUS_A320_GEOMETRY = AircraftGeometry(
    number_of_engines=2,
    engine_positions={
        1: EnginePosition(lateral_arm=-9.5, vertical_arm=-4.5, longitudinal_arm=0.0),
        2: EnginePosition(lateral_arm=+9.5, vertical_arm=-4.5, longitudinal_arm=0.0)
    },
    vertical_stabilizer_height=14.5,
    aileron_effectiveness=1.0,
    rudder_effectiveness=1.0,
    dihedral_angle=2.5
)

MD80_GEOMETRY = AircraftGeometry(
    number_of_engines=2,
    engine_positions={
        1: EnginePosition(lateral_arm=-1.5, vertical_arm=+10.0, longitudinal_arm=-20.0),  # Левый на хвосте
        2: EnginePosition(lateral_arm=+1.5, vertical_arm=+10.0, longitudinal_arm=-20.0)   # Правый на хвосте
    },
    vertical_stabilizer_height=20.0,
    aileron_effectiveness=0.9,
    rudder_effectiveness=1.1,
    dihedral_angle=3.5
)

BOEING_747_GEOMETRY = AircraftGeometry(
    number_of_engines=4,
    engine_positions={
        1: EnginePosition(lateral_arm=-18.0, vertical_arm=-6.0, longitudinal_arm=0.0),  # Левый внешний
        2: EnginePosition(lateral_arm=-10.0, vertical_arm=-5.5, longitudinal_arm=0.0),  # Левый внутренний
        3: EnginePosition(lateral_arm=+10.0, vertical_arm=-5.5, longitudinal_arm=0.0),  # Правый внутренний
        4: EnginePosition(lateral_arm=+18.0, vertical_arm=-6.0, longitudinal_arm=0.0)   # Правый внешний
    },
    vertical_stabilizer_height=18.0,
    aileron_effectiveness=0.8,
    rudder_effectiveness=1.0,
    dihedral_angle=4.0
)

CESSNA_172_GEOMETRY = AircraftGeometry(
    number_of_engines=1,
    engine_positions={
        1: EnginePosition(lateral_arm=0.0, vertical_arm=-1.0, longitudinal_arm=3.0)  # Центральный
    },
    vertical_stabilizer_height=6.0,
    aileron_effectiveness=1.0,
    rudder_effectiveness=1.0,
    dihedral_angle=2.0
)

# Словарь для быстрого доступа
AIRCRAFT_GEOMETRIES = {
    'Boeing 737': BOEING_737_GEOMETRY,
    'Airbus A320': AIRBUS_A320_GEOMETRY,
    'MD-80': MD80_GEOMETRY,
    'Boeing 747': BOEING_747_GEOMETRY,
    'Cessna 172': CESSNA_172_GEOMETRY
}


def get_aircraft_geometry(aircraft_name: str) -> AircraftGeometry:
    """
    Получить геометрию самолёта по имени

    Args:
        aircraft_name: Название самолёта

    Returns:
        AircraftGeometry или None если не найдено
    """
    return AIRCRAFT_GEOMETRIES.get(aircraft_name)


def create_default_geometry(number_of_engines: int) -> AircraftGeometry:
    """
    Создать геометрию по умолчанию для неизвестного самолёта

    Args:
        number_of_engines: Количество двигателей

    Returns:
        AircraftGeometry с усреднёнными параметрами
    """
    if number_of_engines == 1:
        # Одномоторный - двигатель по центру
        return AircraftGeometry(
            number_of_engines=1,
            engine_positions={
                1: EnginePosition(lateral_arm=0.0, vertical_arm=-1.0, longitudinal_arm=2.0)
            },
            vertical_stabilizer_height=6.0
        )

    elif number_of_engines == 2:
        # Двухмоторный - двигатели под крылом (типичная конфигурация)
        return AircraftGeometry(
            number_of_engines=2,
            engine_positions={
                1: EnginePosition(lateral_arm=-10.0, vertical_arm=-5.0, longitudinal_arm=0.0),
                2: EnginePosition(lateral_arm=+10.0, vertical_arm=-5.0, longitudinal_arm=0.0)
            },
            vertical_stabilizer_height=15.0
        )

    elif number_of_engines == 3:
        # Трёхмоторный - два под крылом, один на хвосте
        return AircraftGeometry(
            number_of_engines=3,
            engine_positions={
                1: EnginePosition(lateral_arm=-10.0, vertical_arm=-5.0, longitudinal_arm=0.0),
                2: EnginePosition(lateral_arm=0.0, vertical_arm=+8.0, longitudinal_arm=-15.0),
                3: EnginePosition(lateral_arm=+10.0, vertical_arm=-5.0, longitudinal_arm=0.0)
            },
            vertical_stabilizer_height=18.0
        )

    elif number_of_engines == 4:
        # Четырёхмоторный - все под крылом
        return AircraftGeometry(
            number_of_engines=4,
            engine_positions={
                1: EnginePosition(lateral_arm=-15.0, vertical_arm=-6.0, longitudinal_arm=0.0),
                2: EnginePosition(lateral_arm=-8.0, vertical_arm=-5.5, longitudinal_arm=0.0),
                3: EnginePosition(lateral_arm=+8.0, vertical_arm=-5.5, longitudinal_arm=0.0),
                4: EnginePosition(lateral_arm=+15.0, vertical_arm=-6.0, longitudinal_arm=0.0)
            },
            vertical_stabilizer_height=18.0
        )

    else:
        raise ValueError(f"Неподдерживаемое количество двигателей: {number_of_engines}")
