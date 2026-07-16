# TASK: Re-check Finding 2 (`calculate_descent_rate` NaN/inf) — correction to your crosscheck

## Context

In your cross-check report (`CROSSCHECK-REPORT-59d5118.md`) you AGREED with Alisa that:

> `calculate_descent_rate` is called from `wind_correction.py:180` and `wind_correction.py:215`.
> The `ground_speed` parameter comes from `speed.get('ground_speed', 0)` at line 163. If
> SimConnect returns NaN for ground_speed, it flows directly into `calculate_descent_rate` →
> crash.

I independently re-traced this call graph against the live repo
(`zhuk-mou-1/msfs_autoland` @ `59d5118779ec18017b138a09b172f5c321ec1dbe`) and found this
localization is **incorrect**. Please re-verify and correct.

## What I found

1. **There are two separate, differently-implemented methods with the same name:**
   - `modules/navigation.py`, `Navigation.calculate_descent_rate` (instance method):
     ```python
     def calculate_descent_rate(self, ground_speed: float, glideslope_angle: float) -> int:
         vs = ground_speed * math.tan(math.radians(glideslope_angle)) * 101.3
         return int(vs)
     ```
     This is the one Alisa originally cited (navigation.py audit, F2). It has no guard and
     `int(nan)`/`int(inf)` would raise. **But I could not find any call site for this exact
     method** (`self.system.navigation.calculate_descent_rate` or similar) anywhere in
     `main.py`, `approach_phases.py`, `wind_correction.py`, or `synthetic_glidepath.py`. It
     appears to be dead/unreachable code in the current production call graph.

   - `modules/wind_correction.py`, `WindCorrection.calculate_descent_rate` (`@staticmethod`,
     same name, different class, different body):
     ```python
     @staticmethod
     def calculate_descent_rate(ground_speed: float, glideslope_angle: float) -> float:
         if (not math.isfinite(glideslope_angle)
                 or glideslope_angle <= 0
                 or glideslope_angle > 10):
             logger.warning(...)
             return 0.0
         vs = ground_speed * math.tan(math.radians(glideslope_angle)) * 101.3
         return vs  # NOTE: no int() cast here
     ```
     This is the version actually called (twice) inside `WindCorrection.apply_wind_corrections`
     via `self.calculate_descent_rate(ground_speed, config.glideslope_angle)` — since it's
     invoked as `self.` on a `WindCorrection` instance, Python resolves it to this local
     staticmethod, NOT to `Navigation.calculate_descent_rate`. This version guards
     `glideslope_angle` but not `ground_speed`, and critically **does not call `int()`**, so it
     cannot itself raise `ValueError`/`OverflowError` on NaN/inf `ground_speed` — it just
     silently returns `NaN`/`inf` as a float.

2. **The real crash path (which neither Alisa's nor your report identified) is downstream, in
   `modules/approach_phases.py`, `FinalPhaseState._control_aircraft`:**
   ```python
   if ownership is None or ownership.pitch == ControlOwner.AIRCRAFT_AP:
       if self.system.synthetic_glidepath is not None:
           vs = self.system.synthetic_glidepath.compute_target_vs(
               telemetry, wind_data['corrected_vs']
           )
       else:
           vs = wind_data['corrected_vs']
       self.system.control.set_vertical_speed(-int(vs))  # <-- int(nan) raises ValueError here
   ```
   `wind_data['corrected_vs']` is the output of `WindCorrection.calculate_descent_rate`
   (i.e., `base_vs`, unchanged by `vs_correction: 0.0` in the current code). If `ground_speed`
   is NaN, `corrected_vs` is NaN.
   - For **ILS approaches**, `synthetic_glidepath is None`, so `vs = wind_data['corrected_vs']`
     directly — NaN flows straight into `int(vs)` → crash.
   - For **VOR/NDB/LOC approaches**, `vs` comes from `SyntheticGlidepath.compute_target_vs`,
     which does `raw_vs = wind_correction_vs + vs_correction` and returns it unless the MDA
     floor clamp triggers (`altitude_msl <= self._mda_msl` or `<= self._mda_msl + hysteresis`
     forces `0.0`/return early). Outside that floor band (i.e., during most of a normal
     descent), NaN would propagate through untouched → same crash at `int(vs)`.

## What to verify

1. Confirm (or refute) my claim that `Navigation.calculate_descent_rate` (navigation.py) is
   unreachable from the current production call graph. Search more broadly than I did if
   useful — e.g. check whether any test, script, or module I didn't fetch calls it.
2. Confirm (or refute) that the two `calculate_descent_rate` methods are genuinely distinct
   implementations resolved by class, not the same method somehow shared/imported.
3. Confirm (or refute) the crash path I traced through `_control_aircraft` — in particular
   whether `set_vertical_speed` or any earlier code coerces/sanitizes `vs` before the `int()`
   call (I did not find any).
4. Given this, should Finding 2's severity/categorization change? My read: the *practical*
   crash risk is real and reachable in production (not merely theoretical), but the fix
   location should be `approach_phases.py::_control_aircraft` (and/or upstream in
   `wind_correction.py`'s ground_speed handling), not `navigation.py`. This file is NOT part of
   the Wave 1 diff, so "not a Wave 1 regression" still holds — only the localization changes.

Please reply with a corrected verdict for Finding 2, citing the exact lines/files you
independently confirm.
