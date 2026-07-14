# Architecture Documentation

This directory contains the verified runtime architecture documentation for `msfs_autoland`.

## Structure

- `CURRENT.md` / `CURRENT.json` — pointer to the current canonical snapshot
- `methodology/` — evidence levels, verification guide, known limitations
- `diffs/` — architecture-diff protocol for tracking production changes
- `snapshots/` — immutable architectural snapshots per baseline commit
- `EXTERNAL-AUDIT-BRIEF.md` — instructions for independent external audit
- `check_snapshot_freshness.py` — CLI tool to verify snapshot is current

## Snapshot-based approach

Each snapshot is an immutable record of the architecture at a specific baseline commit. Snapshots are NEVER updated after creation. When production code changes, either:

1. A new snapshot is created for the new baseline, OR
2. An architecture-diff is created linking the old snapshot to the new production state

## How to verify a snapshot

```bash
cd docs/architecture/snapshots/<commit-prefix>
python verify_runtime_architecture.py
```

## How to check freshness

```bash
python docs/architecture/check_snapshot_freshness.py \
  --repo-root . \
  --current-file docs/architecture/CURRENT.json \
  --diff-root docs/architecture/diffs
```

## How to add a new snapshot

1. Run the runtime architecture analysis on the new baseline
2. Create `docs/architecture/snapshots/<commit-prefix>/`
3. Copy all artifacts from the analysis
4. Update `CURRENT.json` to point to the new snapshot
5. Verify with the freshness checker

## Why old snapshots must not be silently updated

Snapshots serve as historical evidence. If a snapshot is updated after the fact, it loses its value as a baseline record. Always create new snapshots or architecture-diffs instead.
