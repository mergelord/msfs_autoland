# Verification Guide

## Standalone verifier

The `verify_runtime_architecture.py` script validates all artifacts in a snapshot. It can run from any directory after extracting the snapshot.

```bash
cd docs/architecture/snapshots/3971ba1
python verify_runtime_architecture.py
```

Expected: `RESULT: PASS`, exit code 0.

### What the verifier checks

1. Baseline commit matches expected value
2. 49 production files in inventory
3. DEPGRAPH reconciliation (49/49 nodes)
4. All required artifact files exist
5. JSON schema (version 2.0, data_items > 0, scenarios = 11, evidence levels valid)
6. Harness scenario IDs match (11 scenarios)
7. All trace files present and matching scenario set
8. Semantic trace validation (loc_signal_loss, gateway rejection, fail-silent, missing telemetry)
9. Phase transitions (7 rows, no fake transitions)
10. Manifest hash verification (all entries)
11. Source line bounds (go-around call sites within file limits)
12. Report content checks

## Evidence bundle

The `evidence/` directory contains immutable reference data:
- `depgraph.json` — import graph for reconciliation
- `source-line-index.json` — file line counts for bounds checking

## Manifest

`artifact-manifest.json` contains SHA-256 hashes and sizes for all snapshot files. The verifier checks every entry.

## DEPGRAPH reconciliation

The runtime architecture nodes must exactly match the DEPGRAPH nodes (49/49). Import edges are preserved as a structural layer but not treated as runtime execution evidence.

## Freshness checker

```bash
python docs/architecture/check_snapshot_freshness.py \
  --repo-root . \
  --current-file docs/architecture/CURRENT.json
```

Statuses:
- `CURRENT` — production digest matches snapshot
- `CURRENT_WITH_ARCHITECTURE_DIFF` — production changed but valid diff exists
- `STALE` — production changed, no valid diff or new snapshot
- `ERROR` — computation failed
