"""Verify runtime-architecture artifacts — standalone v5.

Runs from any directory after ZIP extraction. Uses evidence/ bundle.
"""

import csv
import json
import hashlib
import sys
from pathlib import Path

# Auto-detect roots
SCRIPT_DIR = Path(__file__).resolve().parent
ARTIFACT_ROOT = SCRIPT_DIR
EVIDENCE_DIR = ARTIFACT_ROOT / "evidence"
DEPGRAPH_PATH = EVIDENCE_DIR / "depgraph.json"
SOURCE_INDEX_PATH = EVIDENCE_DIR / "source-line-index.json"

errors = []


def check(condition, msg):
    if not condition:
        errors.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  PASS: {msg}")


print("=== verify_runtime_architecture v5 (standalone) ===\n")

# 1. Baseline commit
print("[1] Baseline commit")
if DEPGRAPH_PATH.exists():
    with open(DEPGRAPH_PATH) as f:
        dg = json.load(f)
    check(dg["meta"]["commit"] == "3971ba12113d8994665b1c9a172f2dca6c9e3855",
          f"commit = {dg['meta']['commit']}")
else:
    check(False, "depgraph.json not found in evidence/")

# 2. Production files
print("\n[2] Production files")
inv_path = ARTIFACT_ROOT / "module-inventory.csv"
if inv_path.exists():
    with open(inv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    check(len(rows) == 49, f"inventory rows = {len(rows)}")
else:
    check(False, "module-inventory.csv not found")

# 3. DEPGRAPH reconciliation
print("\n[3] DEPGRAPH reconciliation")
if DEPGRAPH_PATH.exists():
    dg_nodes = {n["id"] for n in dg["nodes"]}
    inv_modules = {r["module"] for r in rows}
    check(len(dg_nodes) == 49, f"DEPGRAPH nodes = {len(dg_nodes)}")
    only_dg = dg_nodes - inv_modules
    only_inv = inv_modules - dg_nodes
    check(len(only_dg) == 0, f"In DEPGRAPH not inventory: {only_dg or 'none'}")
    check(len(only_inv) == 0, f"In inventory not DEPGRAPH: {only_inv or 'none'}")

# 4. Required artifacts
print("\n[4] Required artifacts")
required = [
    "module-inventory.csv", "actuator-sinks.csv", "go-around-call-sites.csv",
    "self-system-accesses.csv", "data-dictionary.csv", "command-paths.csv",
    "phase-transitions.csv", "frame-command-order.csv", "fail-safe-matrix.csv",
    "execution-flow.mmd", "execution-flow.dot", "execution-flow.png",
    "phase-state-machine.mmd", "phase-state-machine.dot", "phase-state-machine.png",
    "data-flow.mmd", "data-flow.dot", "data-flow.png",
    "command-flow.mmd", "command-flow.dot", "command-flow.png",
    "safety-flow.mmd", "safety-flow.dot", "safety-flow.png",
    "runtime-architecture.json", "RUNTIME-ARCHITECTURE-REPORT.md",
    "artifact-manifest.json", "verify_runtime_architecture.py",
]
for fname in required:
    check((ARTIFACT_ROOT / fname).exists(), f"{fname}")

# 5. JSON schema
print("\n[5] JSON schema")
json_path = ARTIFACT_ROOT / "runtime-architecture.json"
if json_path.exists():
    with open(json_path) as f:
        rj = json.load(f)
    check(rj.get("meta", {}).get("schema_version") == "2.0", "schema_version = 2.0")
    check(len(rj.get("nodes", [])) == 49, f"nodes = {len(rj.get('nodes', []))}")
    check(len(rj.get("data_items", [])) > 0, f"data_items = {len(rj.get('data_items', []))}")
    check(len(rj.get("scenarios", [])) == 11, f"scenarios = {len(rj.get('scenarios', []))}")
    check(len(rj.get("actuator_sinks", [])) == 72, f"actuator_sinks = {len(rj.get('actuator_sinks', []))}")
    # Check evidence levels
    VALID = {"STATIC_CONFIRMED", "TEST_CONFIRMED", "HARNESS_CONFIRMED",
             "RUNTIME_CONFIRMED", "INFERRED", "UNREACHED", "DEAD"}
    bad_sinks = [s for s in rj.get("actuator_sinks", []) if s.get("evidence_level") not in VALID]
    check(len(bad_sinks) == 0, f"actuator sinks with invalid evidence_level: {len(bad_sinks)}")
    bad_edges = [e for e in rj.get("edges", []) if e.get("evidence_level") not in VALID]
    check(len(bad_edges) == 0, f"edges with invalid evidence_level: {len(bad_edges)}")
    # Check no free-form evidence
    bad_evidence = [e for e in rj.get("edges", []) if len(e.get("evidence_level", "")) > 20]
    check(len(bad_evidence) == 0, f"edges with free-form evidence: {len(bad_evidence)}")
else:
    check(False, "runtime-architecture.json not found")

# 6. Harness scenarios
print("\n[6] Harness scenarios")
harness_results = ARTIFACT_ROOT / "harness" / "results.json"
if harness_results.exists():
    with open(harness_results) as f:
        hr = json.load(f)
    scenario_ids = {s["id"] for s in hr["scenarios"]}
    required_ids = {
        "ils_final_ap", "ils_final_vjoy", "non_ils_synthetic_glidepath",
        "safety_guard_goaround", "stabilized_monitor_goaround",
        "loc_signal_loss", "takeover_initiation", "takeover_failure",
        "missing_telemetry", "raw_ae_event_exception_swallowed",
        "gateway_command_rejected",
    }
    missing = required_ids - scenario_ids
    check(len(missing) == 0, f"Missing scenario IDs: {missing or 'none'}")
    check(hr["passed"] == 11, f"harness passed = {hr['passed']}, expected 11")
    # JSON scenarios match harness
    json_scenarios = {s["id"] for s in rj.get("scenarios", [])}
    check(json_scenarios == scenario_ids, f"JSON scenarios == harness scenarios")
else:
    check(False, "harness/results.json not found")

# 7. Trace files
print("\n[7] Trace files")
trace_dir = ARTIFACT_ROOT / "harness" / "command-traces"
if trace_dir.exists():
    for sid in required_ids:
        check((trace_dir / f"{sid}.json").exists(), f"trace {sid}.json")
    trace_files = {f.stem for f in trace_dir.glob("*.json")}
    check(trace_files == required_ids, f"trace set == scenario set")
else:
    check(False, "harness/command-traces/ not found")

# 8. Semantic trace validation
print("\n[8] Semantic trace validation")
if trace_dir.exists():
    # loc_signal_loss
    loc_trace = json.load(open(trace_dir / "loc_signal_loss.json"))
    check(loc_trace.get("go_around") is True, "loc_signal_loss: go_around = true")
    loc_cmds = [e for e in loc_trace.get("entries", []) if "loc" in e.get("command", "").lower()]
    check(len(loc_cmds) > 0, "loc_signal_loss: LOC command in trace")

    # gateway_command_rejected
    gw_trace = json.load(open(trace_dir / "gateway_command_rejected.json"))
    gw_rejected = [e for e in gw_trace.get("entries", []) if "REJECTED" in e.get("authorization", "")]
    check(len(gw_rejected) > 0, "gateway_command_rejected: rejection in trace")

    # raw_ae_event_exception_swallowed
    ae_trace = json.load(open(trace_dir / "raw_ae_event_exception_swallowed.json"))
    ae_swallowed = [e for e in ae_trace.get("entries", []) if "swallow" in e.get("result", "").lower() or "logged" in e.get("result", "").lower()]
    check(len(ae_swallowed) > 0, "raw_ae_event_exception_swallowed: swallowed event in trace")

    # missing_telemetry
    mt_trace = json.load(open(trace_dir / "missing_telemetry.json"))
    check(mt_trace.get("stop") is True or mt_trace.get("go_around") is True,
          "missing_telemetry: stop or go_around")
    check(len(mt_trace.get("entries", [])) >= 3, "missing_telemetry: >= 3 trace entries")

    # Each trace has at least 1 entry
    for sid in required_ids:
        t = json.load(open(trace_dir / f"{sid}.json"))
        check(len(t.get("entries", [])) >= 1, f"{sid}: >= 1 trace entry")
else:
    check(False, "traces not found")

# 9. Transitions
print("\n[9] Transitions")
trans_path = ARTIFACT_ROOT / "phase-transitions.csv"
if trans_path.exists():
    with open(trans_path, newline="", encoding="utf-8") as f:
        trans = list(csv.DictReader(f))
    check(len(trans) == 7, f"phase-transitions rows = {len(trans)}, expected 7")
    # No fake transitions
    fake = [t for t in trans if t["from"] == "INITIAL" and t["to"] == "IDLE"]
    check(len(fake) == 0, "no INITIAL->IDLE fake transition")
    fake2 = [t for t in trans if t["from"] == "LANDING" and t["to"] == "IDLE"]
    check(len(fake2) == 0, "no LANDING->IDLE fake transition")
else:
    check(False, "phase-transitions.csv not found")

# 10. Manifest
print("\n[10] Manifest")
manifest_path = ARTIFACT_ROOT / "artifact-manifest.json"
if manifest_path.exists():
    with open(manifest_path) as f:
        manifest = json.load(f)
    check(len(manifest) >= 40, f"manifest entries = {len(manifest)}")
    # Verify ALL hashes
    hash_errors = 0
    for rel, info in manifest.items():
        fpath = ARTIFACT_ROOT / rel
        if fpath.exists():
            actual = hashlib.sha256(fpath.read_bytes()).hexdigest()
            if actual != info.get("sha256", ""):
                hash_errors += 1
    check(hash_errors == 0, f"hash mismatches = {hash_errors}")
else:
    check(False, "artifact-manifest.json not found")

# 11. Source line bounds
print("\n[11] Source line bounds")
if SOURCE_INDEX_PATH.exists():
    with open(SOURCE_INDEX_PATH) as f:
        source_index = json.load(f)
    ga_path = ARTIFACT_ROOT / "go-around-call-sites.csv"
    if ga_path.exists():
        with open(ga_path, newline="", encoding="utf-8") as f:
            ga = list(csv.DictReader(f))
        for row in ga:
            fname = row["file"].replace("\\", "/")
            line = int(row["line"])
            if fname in source_index:
                check(line <= source_index[fname],
                      f"{fname}:{line} within bounds ({source_index[fname]} lines)")
            else:
                check(False, f"{fname} not in source-line-index")
else:
    check(False, "source-line-index.json not found")

# 12. Report content
print("\n[12] Report content")
report_path = ARTIFACT_ROOT / "RUNTIME-ARCHITECTURE-REPORT.md"
if report_path.exists():
    report_text = report_path.read_text(encoding="utf-8")
    check("COMPLETED_WITH_UNRESOLVED" in report_text, "status correct")
    check("11/11" in report_text, "harness 11/11")
    check("RAW_CONTROL_BYPASS" in report_text, "RAW_CONTROL_BYPASS discussed")
else:
    check(False, "report not found")

# Summary
print(f"\n{'='*50}")
if errors:
    print(f"RESULT: FAIL ({len(errors)} errors)")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("RESULT: PASS")
    sys.exit(0)
