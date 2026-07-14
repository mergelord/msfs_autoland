# Runtime Architecture Dynamic Harness

## Purpose

Verify runtime paths by executing phase states and command flows with mock dependencies.

## Scenarios

1. ILS FINAL, AP owner — commands flow through control.py
2. ILS FINAL, vJoy owner — commands flow through virtual_joystick.py
3. non-ILS synthetic glidepath — synthetic_glidepath.compute_target_vs()
4. SafetyGuard GO_AROUND — pre-command guard triggers go-around
5. stabilized monitor GO_AROUND — post-command stabilization fails
6. LOC signal loss — _calculate_approach_data returns None
7. takeover initiation — should_initiate_takeover → perform_takeover
8. takeover failure — perform_takeover returns False → go-around
9. missing telemetry — exception in get_all_data → error budget
10. actuator exception — exception in control.set_* → error budget

## Usage

```bash
python harness/run_harness.py
```

## Limitations

- SimConnect, vJoy, WASM are mocked — real hardware not tested
- Timing/jitter not measurable without MSFS
- Command order is deterministic in harness (no real concurrent frames)
