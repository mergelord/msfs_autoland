# Evidence Levels

Each edge/path in the runtime architecture is assigned exactly one evidence level.

## Definitions

### STATIC_CONFIRMED
A call, read, write, or transition directly proven by source code with `file:line` evidence.
- **Proves:** the code path exists in the source
- **Does NOT prove:** the path is executed at runtime, or that it produces correct results
- **Example:** `main.py:125` — `self.control = CommandGateway(raw_control, ...)` is statically confirmed

### TEST_CONFIRMED
A path is actually executed by an existing pytest test. Requires:
- test file name
- test function name
- assertion
- production path it confirms
- **Proves:** the path executes with specific inputs in test environment
- **Does NOT prove:** the path works with real SimConnect/MSFS

### HARNESS_CONFIRMED
A path is executed by a local harness with mock dependencies from `research/runtime_architecture/harness/`. Requires:
- harness scenario ID
- trace file
- expected vs observed order
- pass/fail condition
- **Proves:** the production method executes correctly with mocked dependencies
- **Does NOT prove:** real SimConnect communication, timing, or hardware behavior

### RUNTIME_CONFIRMED
A path confirmed by actual execution with real MSFS. Requires:
- real SimConnect connection
- actual telemetry data
- observed command output
- **Proves:** the path works in the real simulator
- **Note:** In this snapshot, RUNTIME_CONFIRMED = 0 (MSFS not used)

### INFERRED
A connection is logically presumed but no direct execution or unambiguous static evidence exists.
- **Example:** ConnectionMonitor behavior is inferred from its interface but not directly tested

### UNREACHED
A path exists in code but is not reached by any test or harness scenario.
- **Example:** 33 modules have no direct test import (structural metric, not runtime claim)

### DEAD
A component or path is proven to be both not created AND not called from entry points AND has no callback/registration/dynamic lookup path.
- **Example:** No go-around from INITIAL or LANDING phases (NO_TRANSITION_DEFINED)
