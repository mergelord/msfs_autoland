# Current Architecture Snapshot

Current canonical snapshot: `snapshots/3971ba1/`
Baseline: `3971ba12113d8994665b1c9a172f2dca6c9e3855`
Status relative to current production tree: CURRENT

## Freshness rule

If the production digest differs from the snapshot digest:
- STATUS = STALE
- Required: regenerate snapshot or add a validated architecture-diff

Check freshness:
```bash
python docs/architecture/check_snapshot_freshness.py \
  --repo-root . \
  --current-file docs/architecture/CURRENT.json
```
