# Known Limitations

## SimConnect timing
Real SimConnect communication timing, jitter, and frame synchronization cannot be measured without MSFS.

## Telemetry freshness/age
No timestamp or staleness detection exists in the current codebase. The snapshot documents this as an architectural risk.

## WASM/LVAR accuracy
Actual read/write accuracy of WASM modules and LVARs is not verified without MSFS.

## vJoy hardware behavior
Virtual joystick axis mapping, dead zones, and polling rates depend on hardware and are not testable offline.

## Real aircraft dynamics
The architecture models command flow but not actual aircraft response. Flight dynamics require MSFS.

## No real MSFS runtime confirmation
All evidence levels except RUNTIME_CONFIRMED are based on static analysis or mock execution. RUNTIME_CONFIRMED = 0 in this snapshot.

## Mock/harness boundaries
H harness scenarios use MagicMock for external dependencies (SimConnect, vJoy, WASM). This verifies production method logic but not integration with real hardware.

## Snapshot baseline limitation
This snapshot is valid only for baseline `3971ba1`. Changes to production code require new snapshots or architecture-diffs.

## Aviation units/signs/geometry
Aircraft-specific calculations (heading, bank, glidepath, wind correction) require separate physical verification with real flight data.

## Fail-silent actuator writes
`MSFSControl.set_*()` methods swallow exceptions and log errors without re-raising. This means actuator write failures may go undetected by the main loop error budget.
