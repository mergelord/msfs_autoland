# Architecture Diffs

This directory stores architecture-diffs that track changes between a snapshot baseline and subsequent production changes.

## Structure

```
diffs/<from>-to-<production-digest-prefix>/
├── architecture-diff.json
├── ARCHITECTURE-DIFF.md
└── affected-tests.md
```

## architecture-diff.json schema

```json
{
  "schema_version": "1.0",
  "from_snapshot": "3971ba1",
  "from_production_digest": "...",
  "to_production_digest": "...",
  "changed_production_files": [],
  "changed_nodes": [],
  "added_edges": [],
  "removed_edges": [],
  "changed_safety_paths": [],
  "required_regression_tests": [],
  "review_status": "PENDING|APPROVED|REJECTED"
}
```

## CI validation rules

The CI considers production tree documented if:
- `from_production_digest` matches `CURRENT.json`
- `to_production_digest` matches actual production digest
- `changed_production_files` exactly matches git diff of production scope
- `review_status` is not empty
- All required fields are present

Empty or invalid diff files are rejected.
