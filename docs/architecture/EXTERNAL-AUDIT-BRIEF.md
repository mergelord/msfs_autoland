# External Audit Brief

## Overview

This document provides instructions for an independent external audit of the `msfs_autoland` runtime architecture snapshot.

## Audit approach

### PASS A — Blind code-first audit

The auditor receives the repository and baseline commit, but NOT the architectural findings. They independently reconstruct:

1. Lifecycle and execution flow
2. Phase state machine
3. Telemetry/data flow
4. Command paths
5. Ownership/authorization
6. Actuator sinks
7. Safety/fail-safe mechanisms
8. Go-around/takeover paths
9. Dead/unreachable paths
10. Readiness verdict

### PASS B — Architecture cross-check

After PASS A is complete, the auditor receives:

```
docs/architecture/snapshots/3971ba1/
```

They determine:
1. Agreements between independent analysis and snapshot
2. Contradictions
3. Omissions
4. Incorrect evidence levels
5. Wrong file:line references
6. Ungrounded conclusions
7. Architectural risks
8. Recommendations

## Required audit domains

- Code correctness
- Architecture/modularity
- `self.system.*` coupling
- State management
- Telemetry freshness
- Error handling / fail-silent behavior
- CommandGateway / ownership
- Go-around atomicity
- Test/harness realism
- Aviation units/signs/geometry
- Operational readiness

## Auditor deliverables

```
EXTERNAL-CODE-AUDIT.md
EXTERNAL-ARCHITECTURE-AUDIT.md
ARCHITECTURE-CROSSCHECK.md
SAFETY-READINESS.md
RECOMMENDED-ROADMAP.md
FINDINGS.json
```

### FINDINGS.json schema

Each finding:
```json
{
  "id": "F-001",
  "severity": "P0|P1|P2|P3",
  "confidence": "HIGH|MEDIUM|LOW",
  "file:line": "main.py:125",
  "architecture_edge": "CommandGateway creation",
  "runtime_reachability": "STATIC_CONFIRMED|TEST_CONFIRMED|HARNESS_CONFIRMED|UNREACHED|DEAD",
  "existing_test": "test_name or NONE",
  "required_test": "description",
  "recommendation": "...",
  "fix_risk": "LOW|MEDIUM|HIGH"
}
```

### Readiness verdicts

The auditor provides separate readiness assessments:
- Unit/CI readiness
- Offline integration readiness
- Controlled MSFS test readiness
- Autonomous scenario readiness
- Operational safety readiness
