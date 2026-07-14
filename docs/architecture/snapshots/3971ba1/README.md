# Snapshot 3971ba1

## Baseline commit
```
3971ba12113d8994665b1c9a172f2dca6c9e3855
```

## Production scope
47 Python files in modules/ + main.py + gui.py = 49 files

## Snapshot status
CANONICAL

## Runtime confirmation
RUNTIME_CONFIRMED = 0

## Important disclaimers

- This snapshot describes only baseline `3971ba1`. It is NOT automatically current for subsequent commits.
- `STATIC_CONFIRMED` does NOT mean the code has been executed in MSFS.
- `HARNESS_CONFIRMED` does NOT equal `RUNTIME_CONFIRMED`.
- Real SimConnect/WASM/vJoy/timing properties require MSFS.
- Diagrams are visualizations of the machine-readable JSON/CSV registry.
- Sources of truth: baseline source + JSON/CSV evidence + verifier.
- This canonical package has passed independent verification.
- Architectural findings are NOT a safety certification.

## Verification

```bash
cd docs/architecture/snapshots/3971ba1
python verify_runtime_architecture.py
```

Expected result:
```
RESULT: PASS
exit code 0
```

## Contents

| Category | Files |
|----------|-------|
| Reports | DEPGRAPH-REPORT.md, RUNTIME-ARCHITECTURE-REPORT.md |
| Machine-readable | runtime-architecture.json, depgraph.json |
| CSVs | module-inventory.csv, actuator-sinks.csv, data-dictionary.csv, command-paths.csv, phase-transitions.csv, frame-command-order.csv, fail-safe-matrix.csv, go-around-call-sites.csv, self-system-accesses.csv |
| Diagrams | execution-flow, phase-state-machine, data-flow, command-flow, safety-flow (.mmd/.dot/.png each) |
| Harness | results.json, 11 command traces |
| Evidence | depgraph.json, source-line-index.json |
| Verification | verify_runtime_architecture.py, verifier-stdout.txt, artifact-manifest.json |
