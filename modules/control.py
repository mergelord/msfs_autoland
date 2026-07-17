"""
Модуль управления самолётом через SimConnect API
"""

import math
import logging
from typing import Optional

from SimConnect import AircraftEvents
from SimConnect.EventList import Event

logger = logging.getLogger(__name__)

# SDK-only events absent from SimConnect v0.4.26 static EventList
# but confirmed in official MSFS 2020 SDK.
SDK_ONLY_EVENTS = frozenset({
    "AP_VS_ON",
    "NAV1_RADIO_SET_HZ",
    "NAV2_RADIO_SET_HZ",
})


class MSFSControl:
    """Класс для управления самолётом через SimConnect"""

    FLAPS_EVENTS = {
        0: "FLAPS_UP",
        1: "FLAPS_1",
        2: "FLAPS_2",
        3: "FLAPS_3",
    }

    def __init__(self, aircraft_events: AircraftEvents, aircraft_requests=None):
        self.ae = aircraft_events
        self._aq = aircraft_requests  # Optional: для readback SimVars
        self._dynamic_events: dict[str, Event] = {}

    # ── SimConnect event dispatch (A-DISP-1) ─────────────────────

    def _resolve_event(self, name: str):
        event = self.ae.find(name)
        if event is not None:
            if not callable(event):
                raise TypeError(f"SimConnect event {name!r} is not callable")
            return event

        if name not in SDK_ONLY_EVENTS:
            raise ValueError(f"Unknown SimConnect event: {name}")

        event = self._dynamic_events.get(name)
        if event is None:
            sm = getattr(self.ae, "sm", None)
            if sm is None:
                raise RuntimeError(
                    f"Cannot register SDK-only event {name!r}: "
                    "AircraftEvents.sm unavailable"
                )
            event = Event(
                name.encode("ascii"), sm,
                _dec="Official MSFS SDK event missing from SimConnect 0.4.26 EventList",
            )
            self._dynamic_events[name] = event
        return event

    def _send_event(self, name: str, value=None):
        event = self._resolve_event(name)
        if value is None:
            event()
        else:
            event(value)

    # ── Helpers ──────────────────────────────────────────────────

    @staticmethod
    def _bounded_number(value, *, name, minimum, maximum):
        if isinstance(value, bool):
            raise ValueError(f"{name} must be numeric, not bool")
        try:
            value = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be numeric") from exc
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
        bounded = max(minimum, min(maximum, value))
        if bounded != value:
            logger.warning("Clamped %s from %s to %s", name, value, bounded)
        return bounded

    @classmethod
    def _unit_input(cls, value, *, name):
        return cls._bounded_number(value, name=name, minimum=-1.0, maximum=1.0)

    @classmethod
    def _throttle_input(cls, value, *, name="throttle"):
        return cls._bounded_number(value, name=name, minimum=0.0, maximum=1.0)

    # ── Commands ─────────────────────────────────────────────────

    def set_autopilot_master(self, state: bool):
        """Включить/выключить автопилот"""
        try:
            if state:
                self._send_event("AUTOPILOT_ON")
            else:
                self._send_event("AUTOPILOT_OFF")
            logger.info("Autopilot master: %s", state)
        except Exception as e:
            logger.error("Error setting autopilot master: %s", e)

    def set_heading_hold(self, heading: Optional[int] = None):
        """Установить режим удержания курса"""
        try:
            self._send_event("AP_HDG_HOLD_ON")
            if heading is not None:
                self._send_event("HEADING_BUG_SET", int(heading))
            logger.info("Heading hold ON, heading: %s", heading)
        except Exception as e:
            logger.error("Error setting heading hold: %s", e)

    def set_altitude_hold(self, altitude: Optional[int] = None):
        """Установить режим удержания высоты"""
        try:
            self._send_event("AP_ALT_HOLD_ON")
            if altitude is not None:
                self._send_event("AP_ALT_VAR_SET_ENGLISH", int(altitude))
            logger.info("Altitude hold ON, altitude: %s", altitude)
        except Exception as e:
            logger.error("Error setting altitude hold: %s", e)

    def set_nav_hold(self, state: bool):
        """Включить/выключить режим NAV (следование по VOR)"""
        try:
            if state:
                self._send_event("AP_NAV1_HOLD_ON")
            else:
                self._send_event("AP_NAV1_HOLD_OFF")
            logger.info("NAV hold: %s", state)
        except Exception as e:
            logger.error("Error setting NAV hold: %s", e)

    def set_approach_mode(self, state: bool):
        """Включить/выключить режим захода на посадку"""
        try:
            if state:
                self._send_event("AP_APR_HOLD_ON")
            else:
                self._send_event("AP_APR_HOLD_OFF")
            logger.info("Approach mode: %s", state)
        except Exception as e:
            logger.error("Error setting approach mode: %s", e)

    def set_airspeed_hold(self, speed: Optional[int] = None):
        """Установить режим удержания скорости"""
        try:
            self._send_event("AP_AIRSPEED_ON")
            if speed is not None:
                self._send_event("AP_SPD_VAR_SET", int(speed))
            logger.info("Airspeed hold ON, speed: %s", speed)
        except Exception as e:
            logger.error("Error setting airspeed hold: %s", e)

    def set_vertical_speed(self, vs: int):
        """Установить вертикальную скорость (футы/мин)

        Uses deterministic AP_VS_ON (not toggle AP_VS_HOLD).
        """
        try:
            self._send_event("AP_VS_ON")
            self._send_event("AP_VS_VAR_SET_ENGLISH", int(vs))
            logger.info("Vertical speed set: %s fpm", vs)
        except Exception as e:
            logger.error("Error setting vertical speed: %s", e)

    def set_nav_frequency(self, nav_index: int, frequency: int):
        """Установить частоту NAV радио (в Hz)"""
        try:
            if nav_index == 1:
                self._send_event("NAV1_RADIO_SET_HZ", frequency)
            elif nav_index == 2:
                self._send_event("NAV2_RADIO_SET_HZ", frequency)
            logger.info("NAV%s frequency set: %s Hz", nav_index, frequency)
        except Exception as e:
            logger.error("Error setting NAV frequency: %s", e)

    def set_adf_frequency(self, frequency: int):
        """Установить частоту ADF (в Hz)"""
        try:
            self._send_event("ADF_COMPLETE_SET", frequency)
            logger.info("ADF frequency set: %s Hz", frequency)
        except Exception as e:
            logger.error("Error setting ADF frequency: %s", e)

    def set_obs(self, nav_index: int, course: int):
        """Установить OBS (курс на VOR)"""
        try:
            if nav_index == 1:
                self._send_event("VOR1_SET", int(course))
            elif nav_index == 2:
                self._send_event("VOR2_SET", int(course))
            logger.info("NAV%s OBS set: %s°", nav_index, course)
        except Exception as e:
            logger.error("Error setting OBS: %s", e)

    def set_flaps(self, position: int):
        """Установить закрылки (логический детент 0-3 через дискретные события)"""
        try:
            position = int(self._bounded_number(position, name="flaps", minimum=0, maximum=3))
            event_name = self.FLAPS_EVENTS[position]
            self._send_event(event_name)
            logger.info("Flaps set: %s (%s)", position, event_name)
        except Exception as e:
            logger.error("Error setting flaps: %s", e)

    def set_gear(self, state: bool):
        """Выпустить/убрать шасси"""
        try:
            if state:
                self._send_event("GEAR_DOWN")
            else:
                self._send_event("GEAR_UP")
            logger.info("Gear: %s", 'DOWN' if state else 'UP')
        except Exception as e:
            logger.error("Error setting gear: %s", e)

    def set_throttle(self, percent: float):
        """
        Установить газ на всех двигателях (0.0 - 1.0)

        Args:
            percent: Процент тяги (0.0 - 1.0)
        """
        try:
            percent = self._throttle_input(percent)
            value = int(percent * 16384)
            self._send_event("THROTTLE_SET", value)
            logger.info("Throttle set: %.1f%%", percent*100)
        except Exception as e:
            logger.error("Error setting throttle: %s", e)

    def set_throttle_engine(self, engine_index: int, percent: float):
        """
        Установить газ на конкретном двигателе (0.0 - 1.0)

        Args:
            engine_index: Номер двигателя (1-4)
            percent: Процент тяги (0.0 - 1.0)
        """
        try:
            percent = self._throttle_input(percent, name=f"engine_{engine_index}_throttle")
            value = int(percent * 16384)

            # SimConnect события для индивидуальных двигателей
            event_map = {
                1: "THROTTLE1_SET",
                2: "THROTTLE2_SET",
                3: "THROTTLE3_SET",
                4: "THROTTLE4_SET"
            }

            if engine_index not in event_map:
                logger.error(f"Invalid engine index: {engine_index} (must be 1-4)")
                return

            self._send_event(event_map[engine_index], value)
            logger.info(f"Engine {engine_index} throttle set: {percent*100:.1f}%")

        except Exception as e:
            logger.error(f"Error setting engine {engine_index} throttle: {e}")

    def set_throttle_asymmetric(self, throttle_values: dict):
        """
        Установить асимметричную тягу (разные значения для каждого двигателя)

        Args:
            throttle_values: Словарь {engine_index: percent}
                            Например: {1: 0.8, 2: 0.0, 3: 0.8, 4: 0.0}
        """
        try:
            for engine_idx, percent in throttle_values.items():
                self.set_throttle_engine(engine_idx, percent)

            logger.info(f"Asymmetric throttle set: {throttle_values}")

        except Exception as e:
            logger.error(f"Error setting asymmetric throttle: {e}")

    def set_rudder(self, percent: float):
        """
        Установить руль направления (-1.0 до +1.0)

        Args:
            percent: Положение руля
                    -1.0 = полностью вправо
                     0.0 = нейтраль
                    +1.0 = полностью влево
        """
        try:
            # SimConnect использует диапазон -16384 до +16384
            percent = self._unit_input(percent, name="rudder")
            value = int(percent * 16384)
            self._send_event("RUDDER_SET", value)
            logger.debug(f"Rudder set: {percent:+.2f} ({value})")

        except Exception as e:
            logger.error(f"Error setting rudder: {e}")

    def set_aileron(self, percent: float):
        """
        Установить элероны (-1.0 до +1.0)

        Args:
            percent: Положение элеронов
                    -1.0 = полностью влево (левый крен)
                     0.0 = нейтраль
                    +1.0 = полностью вправо (правый крен)
        """
        try:
            # SimConnect использует диапазон -16384 до +16384
            percent = self._unit_input(percent, name="aileron")
            value = int(percent * 16384)
            self._send_event("AILERON_SET", value)
            logger.debug(f"Aileron set: {percent:+.2f} ({value})")

        except Exception as e:
            logger.error(f"Error setting aileron: {e}")

    # ── Readback methods (WP-3 / FIX-1) ──────────────────────────

    def get_autopilot_engaged(self) -> Optional[bool]:
        """Readback: AP включён?

        Returns:
            True = AP observed on, False = AP observed off,
            None = cannot read (SimVar unavailable).
        """
        if self._aq is None:
            return None
        try:
            return bool(self._aq.get("AUTOPILOT_MASTER"))
        except Exception:
            return None

    def get_autothrottle_engaged(self) -> Optional[bool]:
        """Readback: A/T включён?

        Returns:
            True = AT observed on, False = AT observed off,
            None = cannot read (SimVar unavailable).
        """
        if self._aq is None:
            return None
        try:
            return bool(self._aq.get("AUTOPILOT_THROTTLE_ARM"))
        except Exception:
            return None
