"""
Tests for REC-01 Stage 1 hardening: H1 (monotonic clock), H2 (input validation),
H5 (divide-by-zero guard).

Only validates the hardening fixes. Detection checks 1-6 and the
confirmation/recovery debounce algorithm are NOT tested here — they remain
behaviorally identical to pre-hardening.
"""

import unittest

from modules.engine_failure_detector import (
    EngineFailureDetector,
    EngineFailureThresholds,
    _is_valid_number,
)


def _make_telemetry(n1=85.0, n2=90.0, egt=650.0, fuel_flow=1500.0,
                     oil_pressure=45.0, throttle=0.8, running=True):
    """Helper: build a valid telemetry dict for engine 1."""
    return {
        'engines': {
            'engine_1': {
                'running': running,
                'n1': n1,
                'n2': n2,
                'egt': egt,
                'fuel_flow': fuel_flow,
                'oil_pressure': oil_pressure,
                'throttle': throttle,
            }
        }
    }


def _make_failure_telemetry():
    """Helper: telemetry that triggers check 1 (engine not running)."""
    return _make_telemetry(running=False, n1=0.0, n2=0.0, egt=200.0,
                           fuel_flow=0.0, oil_pressure=0.0, throttle=0.8)


# ---------------------------------------------------------------------------
# H1: Monotonic clock source
# ---------------------------------------------------------------------------
class TestH1MonotonicClock(unittest.TestCase):
    """H1: clock is swappable; >= 3 confirmations invariant preserved."""

    def test_default_clock_is_monotonic(self):
        """Omitted clock → time.monotonic (not time.time)."""
        import time
        det = EngineFailureDetector()
        self.assertEqual(det._clock, time.monotonic)
        self.assertIsInstance(det._clock(), float)

    def test_fake_clock_deterministic_confirmation(self):
        """Injected fake clock drives confirmation window; >= 3 calls required."""
        call_count = [0]

        def fake_clock():
            call_count[0] += 1
            return 100.0  # constant — all timestamps within window

        det = EngineFailureDetector(clock=fake_clock)
        det.initialize(number_of_engines=1)

        # Two calls: failure detected but NOT confirmed (< 3)
        det.update_engine_data(_make_failure_telemetry())
        det.update_engine_data(_make_failure_telemetry())
        self.assertFalse(det.has_engine_failure(),
                         "Failure must NOT be confirmed with only 2 confirmations")

        # Third call: now confirmed (>= 3)
        det.update_engine_data(_make_failure_telemetry())
        self.assertTrue(det.has_engine_failure(),
                        "Failure must be confirmed after exactly 3 confirmations")
        self.assertIn(1, det.get_failed_engines())

    def test_fake_clock_window_expires(self):
        """Timestamps outside confirmation window → old entries pruned."""
        tick = [100.0]

        def fake_clock():
            v = tick[0]
            tick[0] += 10.0  # each call jumps by 10s > confirmation_time (3s)
            return v

        det = EngineFailureDetector(clock=fake_clock)
        det.initialize(number_of_engines=1)

        # 5 calls, but each timestamp is 10s apart → only 1 within window
        for _ in range(5):
            det.update_engine_data(_make_failure_telemetry())

        self.assertFalse(det.has_engine_failure(),
                         "Failure must NOT be confirmed when timestamps exceed window")

    def test_keyword_only_clock(self):
        """clock is keyword-only; positional callers unaffected."""
        det = EngineFailureDetector()
        self.assertEqual(det._clock, __import__('time').monotonic)

        thresholds = EngineFailureThresholds()
        det2 = EngineFailureDetector(thresholds)
        self.assertEqual(det2._clock, __import__('time').monotonic)

    def test_existing_positional_caller_unchanged(self):
        """EngineFailureDetector(thresholds) still works — no TypeError."""
        t = EngineFailureThresholds()
        det = EngineFailureDetector(t)
        det.initialize(number_of_engines=2)
        self.assertEqual(det.number_of_engines, 2)


# ---------------------------------------------------------------------------
# H2: Input validation / sanitization
# ---------------------------------------------------------------------------
class TestH2InputValidation(unittest.TestCase):
    """H2: NaN/inf/None/bool in numeric fields → preserve previous state."""

    def setUp(self):
        self.det = EngineFailureDetector()
        self.det.initialize(number_of_engines=1)
        # Set known good state
        self.det.update_engine_data(_make_telemetry(n1=85.0))

    def _assert_state_unchanged(self, engine_idx=1):
        eng = self.det.engines[engine_idx]
        self.assertAlmostEqual(eng.n1, 85.0)
        self.assertAlmostEqual(eng.n2, 90.0)
        self.assertAlmostEqual(eng.egt, 650.0)
        self.assertAlmostEqual(eng.fuel_flow, 1500.0)
        self.assertAlmostEqual(eng.oil_pressure, 45.0)
        self.assertAlmostEqual(eng.throttle_position, 0.8)
        self.assertTrue(eng.running)

    def test_nan_in_n1(self):
        """NaN n1 → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(n1=float('nan')))
        self._assert_state_unchanged()

    def test_nan_in_egt(self):
        """NaN egt → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(egt=float('nan')))
        self._assert_state_unchanged()

    def test_nan_in_all_fields(self):
        """NaN in every field → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(
            n1=float('nan'), n2=float('nan'), egt=float('nan'),
            fuel_flow=float('nan'), oil_pressure=float('nan'),
            throttle=float('nan')
        ))
        self._assert_state_unchanged()

    def test_inf_in_n1(self):
        """+inf n1 → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(n1=float('inf')))
        self._assert_state_unchanged()

    def test_neg_inf_in_egt(self):
        """-inf egt → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(egt=float('-inf')))
        self._assert_state_unchanged()

    def test_none_in_n1(self):
        """None n1 → previous state preserved, no TypeError."""
        self.det.update_engine_data(_make_telemetry(n1=None))
        self._assert_state_unchanged()

    def test_none_in_running(self):
        """None running → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(running=None))
        self._assert_state_unchanged()

    def test_bool_in_n1(self):
        """True n1 (bool is not int/float for validation) → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(n1=True))
        self._assert_state_unchanged()

    def test_int_running_rejected(self):
        """int running=1 → rejected (must be bool)."""
        self.det.update_engine_data(_make_telemetry(running=1))
        self._assert_state_unchanged()

    def test_string_running_rejected(self):
        """str running='yes' → rejected."""
        self.det.update_engine_data(_make_telemetry(running='yes'))
        self._assert_state_unchanged()

    def test_string_in_n1(self):
        """str n1 → previous state preserved."""
        self.det.update_engine_data(_make_telemetry(n1="high"))
        self._assert_state_unchanged()

    def test_confirmed_failure_not_cleared_by_garbage(self):
        """Engine already failed → garbage frame does NOT clear failure."""
        # Confirm a failure first
        det = EngineFailureDetector()
        det.initialize(number_of_engines=1)
        for _ in range(5):
            det.update_engine_data(_make_failure_telemetry())
        self.assertTrue(det.has_engine_failure())

        # Garbage frame
        det.update_engine_data(_make_telemetry(n1=float('nan')))
        self.assertTrue(det.has_engine_failure(),
                        "Confirmed failure must NOT be cleared by garbage frame")
        self.assertIn(1, det.get_failed_engines())

    def test_valid_extreme_values_pass_through(self):
        """Finite-but-extreme values (e.g. EGT=999) pass to detection checks."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=1)
        # EGT 999 > threshold 900 → should trigger overheat after 3 confirmations
        for _ in range(5):
            det.update_engine_data(_make_telemetry(egt=999.0))
        self.assertTrue(det.has_engine_failure())

    def test_valid_low_n1_passes_through(self):
        """Low but finite N1 passes validation, triggers check 2."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=1)
        for _ in range(5):
            det.update_engine_data(_make_telemetry(n1=10.0, throttle=0.8))
        self.assertTrue(det.has_engine_failure())


class TestH2WarningRateLimit(unittest.TestCase):
    """H2: exactly one warning per (engine_idx, field) across repeated garbage."""

    def setUp(self):
        self.det = EngineFailureDetector()
        self.det.initialize(number_of_engines=1)
        self.det.update_engine_data(_make_telemetry(n1=85.0))

    def test_one_warning_per_field(self):
        """Same NaN field repeated 10 times → exactly 1 warning."""
        with self.assertLogs(level='WARNING') as cm:
            for _ in range(10):
                self.det.update_engine_data(_make_telemetry(n1=float('nan')))

        matching = [m for m in cm.output if "Engine 1" in m and "'n1'" in m]
        self.assertEqual(len(matching), 1,
                         f"Expected exactly 1 warning for (1, 'n1'), got {len(matching)}")

    def test_different_fields_get_separate_warnings(self):
        """NaN in n1 and NaN in egt → 2 separate warnings."""
        with self.assertLogs(level='WARNING') as cm:
            self.det.update_engine_data(_make_telemetry(n1=float('nan')))
            self.det.update_engine_data(_make_telemetry(egt=float('nan')))

        n1_warnings = [m for m in cm.output if "'n1'" in m]
        egt_warnings = [m for m in cm.output if "'egt'" in m]
        self.assertEqual(len(n1_warnings), 1)
        self.assertEqual(len(egt_warnings), 1)

    def test_running_field_warning(self):
        """Non-bool running → exactly 1 warning for (1, 'running')."""
        with self.assertLogs(level='WARNING') as cm:
            for _ in range(5):
                self.det.update_engine_data(_make_telemetry(running=1))

        matching = [m for m in cm.output
                    if "Engine 1" in m and "'running'" in m]
        self.assertEqual(len(matching), 1)

    def test_different_engine_gets_own_warning(self):
        """Two engines, same bad field → 2 warnings (one per engine)."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=2)
        det.update_engine_data({
            'engines': {
                'engine_1': {'running': True, 'n1': 85.0, 'n2': 90.0,
                             'egt': 650.0, 'fuel_flow': 1500.0,
                             'oil_pressure': 45.0, 'throttle': 0.8},
                'engine_2': {'running': True, 'n1': 85.0, 'n2': 90.0,
                             'egt': 650.0, 'fuel_flow': 1500.0,
                             'oil_pressure': 45.0, 'throttle': 0.8},
            }
        })

        with self.assertLogs(level='WARNING') as cm:
            # Both engines get NaN n1
            det.update_engine_data({
                'engines': {
                    'engine_1': {'running': True, 'n1': float('nan'),
                                 'n2': 90.0, 'egt': 650.0,
                                 'fuel_flow': 1500.0, 'oil_pressure': 45.0,
                                 'throttle': 0.8},
                    'engine_2': {'running': True, 'n1': float('nan'),
                                 'n2': 90.0, 'egt': 650.0,
                                 'fuel_flow': 1500.0, 'oil_pressure': 45.0,
                                 'throttle': 0.8},
                }
            })

        n1_warnings = [m for m in cm.output if "'n1'" in m]
        self.assertEqual(len(n1_warnings), 2,
                         "Each engine should get its own warning")


# ---------------------------------------------------------------------------
# H5: Divide-by-zero guard in asymmetric correction
# ---------------------------------------------------------------------------
class TestH5DivideByZero(unittest.TestCase):
    """H5: all engines failed → all-zero corrections, no ZeroDivisionError."""

    def test_all_engines_failed_returns_all_zero(self):
        """All engines failed → every correction is 0.0."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=2)
        det.engines[1].failed = True
        det.engines[2].failed = True
        det.active_failures = [1, 2]

        corrections = det.calculate_asymmetric_thrust_correction()

        self.assertEqual(corrections['engine_1'], 0.0)
        self.assertEqual(corrections['engine_2'], 0.0)

    def test_all_engines_failed_no_exception(self):
        """All engines failed → no ZeroDivisionError."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=4)
        for i in range(1, 5):
            det.engines[i].failed = True
        det.active_failures = [1, 2, 3, 4]

        # Must not raise ZeroDivisionError
        corrections = det.calculate_asymmetric_thrust_correction()
        self.assertEqual(len(corrections), 4)
        for v in corrections.values():
            self.assertEqual(v, 0.0)

    def test_all_engines_failed_critical_log(self):
        """All engines failed → logger.critical called."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=2)
        det.engines[1].failed = True
        det.engines[2].failed = True
        det.active_failures = [1, 2]

        with self.assertLogs(level='CRITICAL') as cm:
            det.calculate_asymmetric_thrust_correction()

        critical_msgs = [m for m in cm.output
                         if "ALL ENGINES FAILED" in m]
        self.assertEqual(len(critical_msgs), 1)

    def test_partial_failure_still_compensates(self):
        """One engine failed (not all) → working engines get compensation."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=2)
        det.engines[1].failed = True
        det.active_failures = [1]

        corrections = det.calculate_asymmetric_thrust_correction()

        self.assertEqual(corrections['engine_1'], 0.0)
        self.assertGreater(corrections['engine_2'], 0.0)
        self.assertEqual(corrections['engine_2'], 1.0)

    def test_no_failure_returns_all_one(self):
        """No failures → all engines get 1.0."""
        det = EngineFailureDetector()
        det.initialize(number_of_engines=3)

        corrections = det.calculate_asymmetric_thrust_correction()

        for i in range(1, 4):
            self.assertEqual(corrections[f'engine_{i}'], 1.0)


# ---------------------------------------------------------------------------
# _is_valid_number unit tests
# ---------------------------------------------------------------------------
class TestIsValidNumber(unittest.TestCase):
    """Unit tests for the _is_valid_number helper."""

    def test_valid_float(self):
        self.assertTrue(_is_valid_number(3.14))

    def test_valid_int(self):
        self.assertTrue(_is_valid_number(42))

    def test_zero(self):
        self.assertTrue(_is_valid_number(0.0))

    def test_negative(self):
        self.assertTrue(_is_valid_number(-100.5))

    def test_nan_rejected(self):
        self.assertFalse(_is_valid_number(float('nan')))

    def test_inf_rejected(self):
        self.assertFalse(_is_valid_number(float('inf')))

    def test_neg_inf_rejected(self):
        self.assertFalse(_is_valid_number(float('-inf')))

    def test_bool_rejected(self):
        self.assertFalse(_is_valid_number(True))
        self.assertFalse(_is_valid_number(False))

    def test_none_rejected(self):
        self.assertFalse(_is_valid_number(None))

    def test_string_rejected(self):
        self.assertFalse(_is_valid_number("42"))

    def test_list_rejected(self):
        self.assertFalse(_is_valid_number([1, 2]))


if __name__ == '__main__':
    unittest.main(verbosity=2)
