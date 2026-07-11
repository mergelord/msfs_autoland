"""
Deterministic safety guard for approach phase.

Pure evaluation: snapshot -> decision. No actuators, no network, no LLM.
Guard runs BEFORE phase_state.handle() in FINAL phase only.

Debounce: per-rule counter increments on violation, resets to 0 when the
rule passes on the current frame. GO_AROUND only after DEBOUNCE_N
consecutive violating frames for the SAME rule. Non-adjacent spikes
from different rules do NOT accumulate.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)

# Debounce: consecutive frames before GO_AROUND
DEBOUNCE_N = 2


class GuardDecision(Enum):
    CONTINUE = "CONTINUE"
    GO_AROUND = "GO_AROUND"


@dataclass(frozen=True)
class GuardResult:
    decision: GuardDecision
    reason: str
    details: dict


@dataclass(frozen=True)
class SafetySnapshot:
    """Immutable snapshot for guard evaluation.

    No control, vJoy, autothrottle, system, or callback references.
    All values are plain scalars with explicit units.
    """
    altitude_agl: float       # feet AGL
    radio_height: float       # feet (radio altimeter; fallback altitude_agl)
    airspeed_indicated: float # knots IAS
    vertical_speed: float     # fpm (positive = climb)
    bank: float               # degrees (absolute value)
    vref: float               # knots (config.approach_speed)

    @classmethod
    def from_telemetry(cls, telemetry: dict, config) -> 'SafetySnapshot':
        """Build snapshot from raw telemetry and approach config.

        Height: radio_height if available, else altitude_agl.
        Both None -> snapshot still builds; G5 handles it via has_* flags.
        """
        position = telemetry.get('position', {})
        speed = telemetry.get('speed', {})
        attitude = telemetry.get('attitude', {})

        altitude_agl = position.get('altitude_agl')
        radio_height = position.get('radio_height')

        height = radio_height if radio_height is not None else altitude_agl

        return cls(
            altitude_agl=altitude_agl if altitude_agl is not None else 0.0,
            radio_height=height if height is not None else 0.0,
            airspeed_indicated=(speed.get('airspeed_indicated')
                                if speed.get('airspeed_indicated') is not None
                                else 0.0),
            vertical_speed=(speed.get('vertical_speed')
                            if speed.get('vertical_speed') is not None
                            else 0.0),
            bank=abs(attitude.get('bank') if attitude.get('bank') is not None else 0.0),
            vref=config.approach_speed,
        )


class ApproachSafetyGuard:
    """Deterministic safety guard. Pure evaluation, no actuators.

    Active in FINAL phase only (phase-gate at call-site in _handle_phase).
    Per-rule debounce: counter increments on violation, resets to 0 on clean frame.
    """

    def __init__(self, debounce_n: int = DEBOUNCE_N):
        self._debounce_n = debounce_n
        self._counters: Dict[str, int] = {}
        self._go_around_executed = False

    def _check_rule(self, key: str, violated: bool, details: dict):
        """Check one rule: increment counter on violation, reset on clean frame.

        Returns:
            ("go_around", GuardResult) if threshold reached.
            ("debounce", key, count) if counting but not yet at threshold.
            ("ok",) if rule passes.
        """
        if violated:
            self._counters[key] = self._counters.get(key, 0) + 1
            if self._counters[key] >= self._debounce_n:
                self._go_around_executed = True
                return ("go_around", GuardResult(GuardDecision.GO_AROUND, key, details))
            return ("debounce", key, self._counters[key])
        else:
            self._counters[key] = 0
            return ("ok",)

    def evaluate(self, snapshot: SafetySnapshot,
                 has_altitude: bool = True,
                 has_radio_height: bool = True,
                 has_airspeed: bool = True) -> GuardResult:
        """Evaluate snapshot against all rules.

        All rules evaluated every frame. Per-rule counter resets on clean frame.
        First rule to reach DEBOUNCE_N consecutive violations triggers GO_AROUND.

        Args:
            snapshot: Immutable safety snapshot.
            has_altitude: True if altitude_agl was present in telemetry.
            has_radio_height: True if radio_height was present in telemetry.
            has_airspeed: True if airspeed_indicated was present in telemetry.
        """
        if self._go_around_executed:
            return GuardResult(GuardDecision.CONTINUE, "already_go_around", {})

        first_debounce = None  # track first rule in debounce for reason

        # G5: Invalid critical telemetry
        has_height = has_radio_height or has_altitude
        g5_violated = not has_height or not has_airspeed
        status = self._check_rule(
            "INVALID_TELEMETRY", g5_violated,
            {"has_height": has_height, "has_airspeed": has_airspeed})
        if status[0] == "go_around":
            return status[1]
        if status[0] == "debounce" and first_debounce is None:
            first_debounce = status

        # G1: Critical sink rate
        g1_violated = abs(snapshot.vertical_speed) > 1500
        status = self._check_rule(
            "CRITICAL_SINK_RATE", g1_violated,
            {"vertical_speed": snapshot.vertical_speed, "threshold": 1500})
        if status[0] == "go_around":
            return status[1]
        if status[0] == "debounce" and first_debounce is None:
            first_debounce = status

        # G2: Critical bank angle
        g2_violated = snapshot.bank > 15.0
        status = self._check_rule(
            "CRITICAL_BANK", g2_violated,
            {"bank": snapshot.bank, "threshold": 15.0})
        if status[0] == "go_around":
            return status[1]
        if status[0] == "debounce" and first_debounce is None:
            first_debounce = status

        # G3: Gross underspeed
        g3_violated = snapshot.airspeed_indicated < snapshot.vref - 10
        status = self._check_rule(
            "GROSS_UNDERSPEED", g3_violated,
            {"airspeed": snapshot.airspeed_indicated,
             "vref": snapshot.vref,
             "threshold": snapshot.vref - 10})
        if status[0] == "go_around":
            return status[1]
        if status[0] == "debounce" and first_debounce is None:
            first_debounce = status

        # G4: Gross overspeed
        g4_violated = snapshot.airspeed_indicated > snapshot.vref + 20
        status = self._check_rule(
            "GROSS_OVERSPEED", g4_violated,
            {"airspeed": snapshot.airspeed_indicated,
             "vref": snapshot.vref,
             "threshold": snapshot.vref + 20})
        if status[0] == "go_around":
            return status[1]
        if status[0] == "debounce" and first_debounce is None:
            first_debounce = status

        # Any rule in debounce? Report it.
        if first_debounce is not None:
            _, key, count = first_debounce
            return GuardResult(GuardDecision.CONTINUE, f"{key}_debounce", {
                "consecutive": count,
                "required": self._debounce_n,
            })

        return GuardResult(GuardDecision.CONTINUE, "all_checks_passed", {})

    def reset(self):
        """Reset state for new approach."""
        self._counters.clear()
        self._go_around_executed = False
