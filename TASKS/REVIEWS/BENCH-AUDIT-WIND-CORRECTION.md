# BENCH-AUDIT-WIND-CORRECTION

**Date:** 2026-07-14
**Commit:** e6fafffba4d6047e87664730cbc888738cceae62
**Auditor:** MiMo (independent blind audit)
**Scope:** modules/wind_correction.py + production call graph + consumers + tests

---

## 1. Точная структура кода

### calculate_corrected_heading() — structured pseudocode

```
function calculate_corrected_heading(self, desired_track, wind_speed, wind_direction, true_airspeed):
    headwind, crosswind = self.calculate_wind_components(wind_speed, wind_direction, desired_track)

    IF true_airspeed > 0:                          # ← outer IF
        crab = degrees(asin(min(1.0, abs(crosswind) / true_airspeed)))
        IF crosswind > 0:                          # ← inner IF (nested inside outer)
            crab = -crab
        # ELSE: crab stays positive (implicit)
    ELSE:                                          # ← ELSE of outer IF
        crab = 0.0

    corrected_heading = (desired_track + crab) % 360
    return corrected_heading
```

**Indentation verification:** The `if crosswind > 0:` block (line 105-106) is indented one level deeper than `if true_airspeed > 0:` (line 103), confirming it is nested inside the outer IF. The `else: crab = 0.0` (lines 107-108) belongs to the outer IF. Confirmed by reading raw file lines 103-108.

---

## 2. Компоненты ветра — авиационная конвенция и probes

### Конвенция по docstring (lines 28-29):
- `headwind > 0` = встречный
- `crosswind > 0` = справа

### Формула (lines 32-38):
```python
wind_angle = radians(wind_direction - aircraft_heading)
headwind = wind_speed * cos(wind_angle)
crosswind = wind_speed * sin(wind_angle)
```

### Probes (wind_speed=20 kt)

| Track | Wind from | headwind | crosswind | Docstring: CW>0 = "справа" |
|-------|-----------|----------|-----------|---------------------------|
| 0°    | 0°        | +20.00   | +0.00     | n/a (pure head)           |
| 0°    | 180°      | -20.00   | +0.00     | n/a (pure tail)           |
| 0°    | 270°      | -0.00    | -20.00    | wind from LEFT → CW<0 ✓   |
| 0°    | 90°       | +0.00    | +20.00    | wind from RIGHT → CW>0 ✓  |
| 90°   | 0°        | +0.00    | -20.00    | wind from LEFT → CW<0 ✓   |
| 90°   | 180°      | +0.00    | +20.00    | wind from RIGHT → CW>0 ✓  |
| 180°  | 90°       | +0.00    | -20.00    | wind from LEFT → CW<0 ✓   |
| 180°  | 270°      | +0.00    | +20.00    | wind from RIGHT → CW>0 ✓  |
| 270°  | 0°        | -0.00    | +20.00    | wind from RIGHT → CW>0 ✓  |
| 270°  | 180°      | +0.00    | -20.00    | wind from LEFT → CW<0 ✓   |

**Conclusion:** The crosswind formula is CORRECT per the documented convention. `crosswind > 0` consistently means wind from the right of the aircraft heading. The convention denotes the side the wind comes FROM, not the physical push direction. This is a valid convention.

---

## 3. Corrected heading — ground track verification

### Correct ground track computation

Coordinates: x=east, y=north. Heading CW from north.

```python
air_x = TAS * sin(heading)
air_y = TAS * cos(heading)
wind_x = -wind_speed * sin(wind_direction)   # FROM → negative
wind_y = -wind_speed * cos(wind_direction)
ground_x = air_x + wind_x
ground_y = air_y + wind_y
ground_track = atan2(ground_x, ground_y) % 360
```

### Probes (TAS=120 kt, wind=20 kt)

| Track | Wind from | Code heading | Ground track | Error | Correct heading | Correct GT |
|-------|-----------|-------------|-------------|-------|-----------------|------------|
| 0°    | 90° (R)   | 350.41°     | **341.32°** | **-18.68°** | 9.59°      | 0.00°      |
| 0°    | 270° (L)  | 9.59°       | **18.68°**  | **+18.68°** | 350.41°    | 360.00°    |
| 90°   | 0° (L)    | 99.59°      | **108.68°** | **+18.68°** | 80.41°     | 90.00°     |
| 90°   | 180° (R)  | 80.41°      | **71.32°**  | **-18.68°** | 99.59°     | 90.00°     |
| 180°  | 90° (L)   | 189.59°     | **198.68°** | **+18.68°** | 170.41°    | 180.00°    |
| 180°  | 270° (R)  | 170.41°     | **161.32°** | **-18.68°** | 189.59°    | 180.00°    |
| 270°  | 0° (R)    | 260.41°     | **251.32°** | **-18.68°** | 279.59°    | 270.00°    |
| 270°  | 180° (L)  | 279.59°     | **288.68°** | **+18.68°** | 260.41°    | 270.00°    |

**Result:** The code produces a consistent **±18.68° ground track error** in all 8 cases. The crab correction is inverted — the nose points in the same direction as the drift, approximately doubling the lateral displacement.

**Root cause location:** The crosswind formula (line 38) is CORRECT per its docstring. The error is in `calculate_corrected_heading` (lines 103-106):

```python
crab = math.degrees(math.asin(min(1.0, abs(crosswind) / true_airspeed)))
if crosswind > 0:
    crab = -crab  # BUG: "ветер справа → лететь левее" — WRONG
```

When `crosswind > 0` (wind from right), the code negates crab, pointing the nose LEFT. But wind from the right pushes the aircraft LEFT, so compensation requires pointing the nose RIGHT. The `if crosswind > 0: crab = -crab` line inverts the correction.

**Minimal fix** (preserve wind_components contract):
```python
crab = math.degrees(math.asin(min(1.0, crosswind / true_airspeed)))
# No sign flip needed: CW>0 (from right) → positive crab → nose RIGHT
```

Or equivalently, using signed ratio without abs:
```python
ratio = max(-1.0, min(1.0, crosswind / true_airspeed))
crab = math.degrees(math.asin(ratio))
corrected_heading = (desired_track + crab) % 360
```

This preserves the documented crosswind convention and all downstream consumers.

---

## 4. Drift/crab consistency

### Three-method comparison

| CW sign | calculate_drift_angle | calculate_crab_angle | calculate_corrected_heading | Internally consistent? | Physically correct? |
|---------|----------------------|---------------------|----------------------------|----------------------|-------------------|
| +20 (R) | +9.59°               | -10.30°             | track - 9.59°              | YES                  | **NO** — nose LEFT, should be RIGHT |
| -20 (L) | -9.59°               | +10.30°             | track + 9.59°              | YES                  | **NO** — nose RIGHT, should be LEFT |

**Internal consistency:** All three methods agree on the sign convention. But internal consistency does NOT prove physical correctness — all three share the same sign inversion.

**`calculate_drift_angle` and `calculate_crab_angle` are also affected:** They return drift/crab with the same inverted convention. However, since `calculate_crab_angle` is dead code (not called anywhere) and `calculate_drift_angle` is only logged (not used for heading control), the functional impact is limited to `calculate_corrected_heading`.

---

## 5. Vertical speed

### calculate_pitch_correction analysis (lines 144-164)

**Parameters actually used:**
- `headwind`: YES — multiplied by 10
- `target_vs`: NO — unused
- `airspeed`: NO — unused

**Formula:** `correction = headwind * 10` (line 160)

### Double-counting analysis

The code computes:
```python
base_vs = self.calculate_descent_rate(ground_speed, config.glideslope_angle)
vs_correction = self.calculate_pitch_correction(headwind, base_vs, airspeed_indicated)
corrected_vs = base_vs + vs_correction
```

The correct geometric formula for glideslope descent is:
```
VS = GS × tan(γ)
```

If `ground_speed` is the actual ground speed, it **already fully determines** the required vertical speed for a given glideslope angle. Two aircraft with identical GS and identical position on the glideslope need identical VS, regardless of headwind. The addition of `headwind * 10` changes the trajectory angle without documented physical model, dimensional derivation, or justification for the coefficient 10 fpm/kt.

### Sign consistency with set_vertical_speed(-int(vs))

In `approach_phases.py` line 488: `self.system.control.set_vertical_speed(-int(vs))`

- `corrected_vs` is positive (descent rate)
- `-int(vs)` makes it negative (MSFS convention: negative = descent)
- Sign is CONSISTENT ✓

---

## 6. Production usage и dead code

### Method status

| Method | Status | Evidence |
|--------|--------|----------|
| `calculate_wind_components` | **production-used** | Called by `apply_wind_corrections` (line 194) and `calculate_corrected_heading` (line 98) |
| `calculate_drift_angle` | **production-used** | Called by `apply_wind_corrections` (line 204) |
| `calculate_crab_angle` | **dead/unreferenced** | Not called anywhere in production or tests |
| `calculate_corrected_heading` | **production-used** | Called by `apply_wind_corrections` (line 199) |
| `calculate_bank_angle_for_crosswind` | **production-used** | Called by `apply_wind_corrections` (line 207) |
| `calculate_pitch_correction` | **production-used** | Called by `apply_wind_corrections` (line 213) |
| `apply_wind_corrections` | **production-used** | Called in `main.py` line 713 |
| `calculate_descent_rate` | **production-used** | Called by `apply_wind_corrections` (line 212) |

### Field consumption from apply_wind_corrections return dict

| Field | Produced (line) | Consumers | Status |
|-------|-----------------|-----------|--------|
| `wind_speed` | 219 | approach_phases.py:65 (log) | **production-used** |
| `wind_direction` | 220 | approach_phases.py:65 (log) | **production-used** |
| `headwind` | 221 | approach_phases.py:121,425,653; flare_controller.py:284-313; autothrottle.py:287-289 | **production-used** (VS, flare, autothrottle) |
| `crosswind` | 222 | approach_phases.py:66,435; autothrottle.py:288,292 | **production-used** (log, autothrottle) |
| `drift_angle` | 223 | approach_phases.py:436 (log only) | **result-produced-but-not-consumed** |
| `corrected_heading` | 224 | approach_phases.py:69,125,447 → set_heading_hold() | **production-used** (heading control) |
| `recommended_bank` | 225 | — | **result-produced-but-not-consumed** |
| `base_vs` | 226 | — | **result-produced-but-not-consumed** (feeds corrected_vs) |
| `vs_correction` | 227 | — | **result-produced-but-not-consumed** (feeds corrected_vs) |
| `corrected_vs` | 228 | approach_phases.py:484,487 → set_vertical_speed() | **production-used** (VS control) |

### Production call path

```
main.py:713  wind_data = self.wind_correction.apply_wind_corrections(telemetry, approach_data, self.approach_config)
  → wind_correction.py:194  headwind, crosswind = self.calculate_wind_components(...)
  → wind_correction.py:199  corrected_heading = self.calculate_corrected_heading(...)
  → wind_correction.py:204  drift_angle = self.calculate_drift_angle(crosswind, true_airspeed)
  → wind_correction.py:207  recommended_bank = self.calculate_bank_angle_for_crosswind(...)
  → wind_correction.py:212  base_vs = self.calculate_descent_rate(ground_speed, config.glideslope_angle)
  → wind_correction.py:213  vs_correction = self.calculate_pitch_correction(headwind, base_vs, airspeed_indicated)
  → wind_correction.py:216  corrected_vs = base_vs + vs_correction
  → return dict → approach_phases.py, flare_controller.py, autothrottle.py consume wind_data
```

### Approach-type impact on corrected_heading

| Approach type | Heading source in FINAL | Wind correction applied? | Feedback mitigation? |
|--------------|------------------------|------------------------|---------------------|
| ILS | `approach_data['corrected_heading']` from `ils_navigation.py` (LOC deviation × 3) | Yes, on top of LOC heading | Partial: LOC feedback can compensate over time |
| LOC | `approach_data['corrected_heading']` from `ils_navigation.py` (LOC deviation × 3) | Yes, on top of LOC heading | Partial: LOC feedback can compensate over time |
| VOR | `config.final_approach_course` | Yes | No: no lateral feedback for heading |
| NDB | `config.final_approach_course` | Yes | No: no lateral feedback for heading |

**Key insight:** ILS/LOC approaches derive `corrected_heading` from localizer deviation (`heading_correction = -loc_dev * 3`), not from wind_correction. The wind correction is applied on top. LOC feedback can partially compensate for the inverted crab over time, but adds constant lateral displacement. VOR/NDB approaches have no feedback and suffer the full ±18.68° error.

---

## 7. Валидация

### Edge case probes

| Input | Method | Result | Classification |
|-------|--------|--------|----------------|
| TAS=0 | `calculate_drift_angle` | 0.0 | **safe fallback** (line 54-55) |
| TAS=0 | `calculate_corrected_heading` | heading=track | **safe fallback** (line 103, 107-108) |
| TAS=-10 | `calculate_drift_angle` | 0.0 | **safe fallback** (TAS ≤ 0 check) |
| TAS=-10 | `calculate_corrected_heading` | heading=track | **safe fallback** |
| GS=0 | `calculate_crab_angle` | 0.0 | **safe fallback** (line 75-76) |
| GS=-10 | `calculate_crab_angle` | 0.0 | **safe fallback** |
| wind_speed=-20 | `calculate_wind_components` | hw=0, cw=-20 | **silent sign inversion** — negative wind speed flips both components. Not validated. |
| crosswind=inf | `calculate_drift_angle` | 90.0 | **safe clamping** — `abs(crosswind)/TAS` → inf → `min(1.0, inf)` = 1.0 → asin(1.0) = 90° |
| wind_dir=inf | `calculate_wind_components` | **EXCEPTION** | `math.radians(inf)` raises `ValueError` |
| wind_speed=NaN | `calculate_wind_components` | hw=NaN, cw=NaN | **silent corruption** — NaN propagates to all outputs |
| angle=0° | `calculate_descent_rate` | 0.0 | safe |
| angle=-3° | `calculate_descent_rate` | -530.89 | negative VS (climb) — technically correct |
| angle=89° | `calculate_descent_rate` | 580,347 fpm | **huge but finite** |
| angle=90° | `calculate_descent_rate` | 1.65×10²⁰ fpm | **astronomical value** — Python int handles arbitrary precision (no overflow). Risk: SimConnect binding may reject the value range. |
| angle=91° | `calculate_descent_rate` | -580,347 fpm | **sign flip** |

### inf error behavior

Main loop (`main.py:517`): catches exception → increments `consecutive_errors` → retries → after exhausting budget (3) → executes stop or go-around. Does NOT substitute default values.

---

## 8. Тестовое покрытие

### Direct WindCorrection instantiation

| Test file | Test | Creates WindCorrection? | Nonzero wind? | Both CW signs? |
|-----------|------|------------------------|---------------|----------------|
| `test_loc_approach.py:572` | `test_loc_cdi_heading_reaches_control` | YES | NO (zero wind) | NO |
| `test_loc_approach.py:625` | `test_red_without_fix_cdi_pipeline` | YES | NO (zero wind) | NO |
| `test_loc_approach.py:796` | `test_red_without_fix_loc_signal_loss` | YES | N/A (tests None crash) | N/A |

### Mock-based tests

All tests in `test_telemetry_recorder.py`, `test_safety_guard.py`, `test_synthetic_glidepath.py` use `MagicMock()` with hardcoded return values. They verify consumers handle wind_data correctly, but do NOT verify WindCorrection computes correct values.

### Critical test gaps

1. **No nonzero-wind test** — all direct WindCorrection tests use zero wind
2. **No ground track verification** — no test checks that heading + wind → desired track
3. **No test verifies both crosswind signs** — P1 sign defect is invisible to test suite
4. **No unit test** for `calculate_wind_components`, `calculate_drift_angle`, `calculate_corrected_heading` in isolation
5. **No validation test** for NaN, inf, negative wind, TAS=0

---

## Findings

### WCB-06: calculate_corrected_heading crab sign inverted — nose points in drift direction [P1]

- **Severity:** P1
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:104-106`
- **Exact quote:**
  ```python
  crab = math.degrees(math.asin(min(1.0, abs(crosswind) / true_airspeed)))
  if crosswind > 0:
      crab = -crab  # Ветер справа - лететь левее
  ```
- **Production call path:** `main.py:713 → wind_correction.py:199 → approach_phases.py:69,125,447 → set_heading_hold(int(corrected_heading))`
- **Probe (reproducing):**
  ```python
  import math
  from modules.wind_correction import WindCorrection
  wc = WindCorrection()
  TAS, W = 120, 20
  # Case 1: track=0, wind FROM 90 (right)
  heading = wc.calculate_corrected_heading(0, W, 90, TAS)   # = 350.41°
  air_x = TAS * math.sin(math.radians(heading))              # = -20.0
  air_y = TAS * math.cos(math.radians(heading))              # = 118.32
  wind_x = -W * math.sin(math.radians(90))                   # = -20.0 (FROM east → westward)
  wind_y = -W * math.cos(math.radians(90))                   # = 0
  gt = math.degrees(math.atan2(air_x + wind_x, air_y + wind_y)) % 360  # = 341.32°
  # Error from desired 0° = -18.68°
  ```
  ```
  Case 1: track=0, wind_from=90, code_heading=350.41 → ground_track=341.32, error=-18.68°
  Case 2: track=0, wind_from=270, code_heading=9.59 → ground_track=18.68, error=+18.68°
  Correct for case 1: heading=9.59 → ground_track=0.00
  Correct for case 2: heading=350.41 → ground_track=360.00
  ```
- **Crosswind formula:** CORRECT per docstring. `crosswind = W * sin(wind_from - heading)` gives CW>0 for wind from right. The convention "CW>0 = from right" is valid.
- **Bug location:** `calculate_corrected_heading` line 105-106. When CW>0 (wind from right, pushes aircraft LEFT), code negates crab → nose goes LEFT (same as drift). Should go RIGHT (into wind).
- **Consequence:** In any crosswind, the commanded heading is ~18.7° off the correct value (at 20kt/120kt TAS). The aircraft drifts laterally instead of compensating. Impact varies by approach type:
  - **VOR/NDB:** Full error, no lateral feedback to compensate.
  - **ILS/LOC:** Partial mitigation — LOC feedback can compensate over time, but adds constant lateral displacement and oscillation.
- **Minimal fix (preserve wind_components contract):**
  ```python
  # Remove abs() and sign flip:
  ratio = max(-1.0, min(1.0, crosswind / true_airspeed))
  crab = math.degrees(math.asin(ratio))
  corrected_heading = (desired_track + crab) % 360
  ```
  This preserves the documented crosswind convention and all downstream consumers.
- **Regression test:**
  ```python
  def test_ground_track_maintained_with_crosswind():
      wc = WindCorrection()
      TAS, W = 120, 20
      for track, wind_from in [(0, 90), (0, 270), (90, 0), (90, 180)]:
          heading = wc.calculate_corrected_heading(track, W, wind_from, TAS)
          air_x = TAS * math.sin(math.radians(heading))
          air_y = TAS * math.cos(math.radians(heading))
          wind_x = -W * math.sin(math.radians(wind_from))
          wind_y = -W * math.cos(math.radians(wind_from))
          gt = math.degrees(math.atan2(air_x + wind_x, air_y + wind_y)) % 360
          error = abs(gt - track)
          if error > 180: error = 360 - error
          assert error < 1.0, f"track={track}, wind={wind_from}: GT={gt:.1f}, error={error:.1f}"
  ```

### WCB-04: NaN wind speed propagates silently → ValueError in consumer → error budget → stop/go-around [P1]

- **Severity:** P1
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:32-38`
- **Probe:**
  ```python
  from modules.wind_correction import WindCorrection
  wc = WindCorrection()
  hw, cw = wc.calculate_wind_components(float('nan'), 90, 0)
  # hw=nan, cw=nan
  heading = wc.calculate_corrected_heading(0, float('nan'), 90, 120)
  # heading=nan
  ```
- **Production call path:** `main.py:713 → wind_correction.py:182 (weather.get('ambient_wind_velocity', 0)) → all outputs → approach_phases.py:447 → set_heading_hold(int(NaN))`
- **Mechanism:** `int(float('nan'))` raises `ValueError` in Python. Main loop catches exception, increments `consecutive_errors`, retries. After 3 consecutive failures, executes go-around.
- **Consequence:** Not silent corruption, but disruptive failure: forces go-around on every frame until telemetry recovers from NaN. If SimConnect returns NaN for wind due to sensor failure, the autoland is non-functional.
- **Direction:** Validate `math.isfinite(wind_speed)` at entry; return zero corrections on invalid input.

### WCB-07: Double-counting headwind in VS correction [P2]

- **Severity:** P2
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:212-216`
- **Exact quote:**
  ```python
  base_vs = self.calculate_descent_rate(ground_speed, config.glideslope_angle)
  vs_correction = self.calculate_pitch_correction(headwind, base_vs, speed.get('airspeed_indicated', 0))
  corrected_vs = base_vs + vs_correction
  ```
- **Physical analysis:** The geometric formula `VS = GS × tan(γ)` fully determines the required vertical speed from ground speed and glideslope angle. If `ground_speed` already reflects headwind, adding `headwind * 10` changes the trajectory angle. No physical model, dimensional derivation, or justification for the coefficient 10 fpm/kt is provided. Parameters `target_vs` and `airspeed` are passed but ignored.
- **Consequence:** At GS=100kt, angle=3°, 20kt headwind: base_vs=531 fpm, correction=200 fpm (38% deviation). The aircraft follows a steeper-than-intended approach path.
- **Fix:** Remove `vs_correction` and use `base_vs` directly, or provide a documented physical model.

### WCB-03: Negative wind speed causes silent sign inversion [P2]

- **Severity:** P2
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:32-38`
- **Probe:** `calculate_wind_components(-20, 90, 0) → headwind=-0.0, crosswind=-20.0`. With positive wind_speed: crosswind=+20.0.
- **Consumers:** `headwind` and `crosswind` are consumed by:
  - `approach_phases.py:425,435` — logging
  - `approach_phases.py:653` — flare `adjust_for_wind(headwind)`
  - `autothrottle.py:287-289` — `calculate_wind_correction(headwind, crosswind)` → throttle adjustment
  - `autothrottle.py:292` — `calculate_crosswind_drag_factor(crosswind)` → drag factor
- **Consequence:** Negative wind speed inverts all component signs. Autothrottle receives wrong headwind/crosswind, applying incorrect throttle correction and drag factor. Flare controller receives wrong headwind, adjusting flare height incorrectly.
- **Direction:** Add `wind_speed = max(0, wind_speed)` or `abs(wind_speed)` at line 32.

### WCB-01: calculate_crab_angle is dead code [P3]

- **Severity:** P3
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:64-81`
- **Evidence:** Zero calls in production or tests.
- **Direction:** Remove or integrate into `calculate_corrected_heading`.

### WCB-02: calculate_pitch_correction ignores target_vs and airspeed parameters [P3]

- **Severity:** P3
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:144-164`
- **Probe:** `calculate_pitch_correction(10, 9999, 120) → 100.0` and `calculate_pitch_correction(10, 700, 9999) → 100.0` — identical.
- **Direction:** Remove unused parameters or implement physics-based model.

### WCB-05: calculate_descent_rate produces astronomical values at glideslope ≥ 90° [P2]

- **Severity:** P2
- **Status:** ПОДТВЕРЖДЕНО
- **File:** `modules/wind_correction.py:243`
- **Probe:** `calculate_descent_rate(100, 90) → 1.65×10²⁰`.
- **Mechanism:** Python int has arbitrary precision — `int(1.65e20)` succeeds without overflow. The risk is in the external API: SimConnect binding may reject the value range, or the command is meaningless. Config-driven, so runtime risk is low.
- **Direction:** Clamp glideslope angle to (0, 45] or validate at config load time.

---

## Отвергнутые тревоги

### 1. "Crosswind formula is wrong"
**ОПРОВЕРГНУТО.** The crosswind formula is CORRECT per the documented convention `crosswind > 0 = wind from right`. The bug is in `calculate_corrected_heading`, not in `calculate_wind_components`.

### 2. "TAS=0 causes division by zero"
**ОПРОВЕРГНУТО.** All methods with TAS/GS denominators have explicit `≤ 0` checks returning 0.0.

### 3. "inf wind direction uses defaults"
**ОПРОВЕРГНУТО.** Main loop catches exception, increments error counter, retries, then go-around. Does NOT use defaults.

### 4. "Python int overflows at glideslope=90°"
**ОПРОВЕРГНУТО.** Python integers have arbitrary precision. `int(1.65e20)` succeeds. Risk is in SimConnect binding range, not Python overflow.

---

## Таблица использования методов и полей

| Method | Production | Tests | Dead? |
|--------|-----------|-------|-------|
| `calculate_wind_components` | ✓ | indirect | No |
| `calculate_drift_angle` | ✓ | indirect | No |
| `calculate_crab_angle` | ✗ | ✗ | **YES** |
| `calculate_corrected_heading` | ✓ | indirect | No |
| `calculate_bank_angle_for_crosswind` | ✓ | indirect | No |
| `calculate_pitch_correction` | ✓ | indirect | No |
| `apply_wind_corrections` | ✓ | ✓ | No |
| `calculate_descent_rate` | ✓ | indirect | No |

| Field | Consumers |
|-------|----------|
| `wind_speed` | approach_phases.py:65 (log) |
| `wind_direction` | approach_phases.py:65 (log) |
| `headwind` | approach_phases.py:121,425,653; flare_controller; autothrottle |
| `crosswind` | approach_phases.py:66,435; autothrottle |
| `drift_angle` | approach_phases.py:436 (log only) |
| `corrected_heading` | approach_phases.py:69,125,447 → set_heading_hold() |
| `recommended_bank` | — (unused) |
| `base_vs` | feeds corrected_vs |
| `vs_correction` | feeds corrected_vs |
| `corrected_vs` | approach_phases.py:484,487 → set_vertical_speed() |

---

## Результаты probes

| Probe | Input | Output | Expected | Match? |
|-------|-------|--------|----------|--------|
| CW, track=0, wind=90 | (20, 90, 0) | cw=+20 | +20 (from right per docstring) | ✓ |
| CW, track=0, wind=270 | (20, 270, 0) | cw=-20 | -20 (from left per docstring) | ✓ |
| Heading, track=0, wind=90 | (0, 20, 90, 120) | 350.41° | ~9.59° | **✗ inverted** |
| GT, heading=350.41, wind_from=90 | code output | 341.32° | 0° | **✗ -18.68°** |
| GT, heading=9.59, wind_from=270 | code output | 18.68° | 0° | **✗ +18.68°** |
| All 8 cases GT | code headings | ±18.68° error | 0° error | **✗ all wrong** |
| Correct heading, case 1 | 9.59° | GT=0.00° | 0° | ✓ |
| Correct heading, case 2 | 350.41° | GT=360.00° | 0° | ✓ |
| VS, GS=100, angle=3° | (100, 3.0) | 530.9 fpm | ~530 | ✓ |
| Pitch corr, hw=10 | (10, 700, 120) | 100.0 | 100 | ✓ |
| TAS=0 fallback | drift(0, 0) | 0.0 | 0 | ✓ |
| GS=0 fallback | crab(20, 0) | 0.0 | 0 | ✓ |
| Negative wind | (-20, 90, 0) | hw=0, cw=-20 | sign inverted | confirmed |
| NaN propagation | (NaN, 90, 0) | hw=NaN, cw=NaN | NaN | confirmed |
| inf wind direction | (20, inf, 0) | ValueError | exception | confirmed |
| Glideslope=90° | (100, 90) | 1.65×10²⁰ | huge (no overflow) | confirmed |

---

## Матрица тестов

| Test | Type | Direct WC? | Nonzero wind? | Both CW signs? |
|------|------|-----------|---------------|----------------|
| test_loc_cdi_heading_reaches_control | pipeline | YES | NO | NO |
| test_red_without_fix_cdi_pipeline | pipeline | YES | NO | NO |
| test_red_without_fix_loc_signal_loss | crash guard | YES | N/A | N/A |
| test_wind_pushes_vs_down_near_mda | glidepath | NO (mock) | N/A | N/A |
| test_clamp_order_independence | glidepath | NO (mock) | N/A | N/A |
| test_on_profile_zero_error | glidepath | NO (mock) | N/A | N/A |
| test_telemetry_recorder_* (6 tests) | recorder | NO (mock) | N/A | N/A |
| test_safety_guard_* (10 tests) | guard | NO (mock) | N/A | N/A |

**Critical gap:** No test exercises WindCorrection with nonzero wind. No test verifies ground track. The P1 sign defect (WCB-06) is completely invisible to the test suite.

---

## Вердикт

**FIX BEFORE SIM**

**P1 (2 items):**
- WCB-06: `calculate_corrected_heading` crab sign inverted → nose points in drift direction → ±18.68° ground track error at 20kt/120kt TAS. Affects VOR/NDB fully, ILS/LOC partially (LOC feedback can compensate over time).
- WCB-04: NaN wind speed → `int(NaN)` → ValueError in consumer → error budget exhaustion → go-around on every frame.

**P2 (3 items):**
- WCB-07: Double-counting headwind in VS correction (no physical model, unjustified 10 fpm/kt coefficient).
- WCB-03: Negative wind speed → silent sign inversion → wrong throttle correction in autothrottle, wrong flare height adjustment.
- WCB-05: Glideslope ≥ 90° → astronomical VS (Python handles big int, SimConnect may reject).

**P3 (2 items):**
- WCB-01: `calculate_crab_angle` is dead code.
- WCB-02: `calculate_pitch_correction` ignores 2 of 3 parameters.

**Test debt:** Zero nonzero-wind tests. Zero ground track verification. The P1 sign defect is invisible to the existing test suite.

**Status:** COMPLETED_NO_CHANGES
