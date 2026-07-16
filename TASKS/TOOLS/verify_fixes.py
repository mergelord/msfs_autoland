#!/usr/bin/env python3
"""Verify all 6 fixes."""
import json

with open("TASKS/DATA/msfs2020_default_aircraft_dataset.json") as f:
    d = json.load(f)

m = d["meta"]
print("=== META ===")
print(f"Aircraft packages: {m['aircraft_packages']}")
print(f"Livery packages: {m['livery_packages']}")
print(f"Aircraft variants: {m['aircraft_variants']}")
print(f"Aircraft titles: {m['aircraft_titles']}")
print()

# FIX-1: Flaps
print("=== FIX-1: FLAPS ===")
for pkg in d["packages"]:
    if "a320-neo" in pkg["package"] and not pkg["is_livery"] and pkg["readable"]:
        for v in pkg["variants"]:
            flaps = v.get("flaps", {})
            sections = flaps.get("sections", [])
            print(f"{pkg['package']}: {len(sections)} sections, total_positions={flaps.get('total_positions')}")
            for s in sections:
                pos = s.get("positions", [])
                angles = [p["angle_deg"] for p in pos]
                print(f"  {s['section']}: {len(pos)} positions, angles={angles}")
    if "c152" in pkg["package"] and "aerobat" not in pkg["package"] and not pkg["is_livery"] and pkg["readable"]:
        for v in pkg["variants"]:
            flaps = v.get("flaps", {})
            sections = flaps.get("sections", [])
            print(f"{pkg['package']}: {len(sections)} sections, total_positions={flaps.get('total_positions')}")
            for s in sections:
                pos = s.get("positions", [])
                angles = [p["angle_deg"] for p in pos]
                print(f"  {s['section']}: {len(pos)} positions, angles={angles}")
print()

# FIX-2: Engine count
print("=== FIX-2: ENGINE COUNT ===")
for pkg in d["packages"]:
    if not pkg["readable"] or pkg["is_livery"]:
        continue
    for v in pkg["variants"]:
        ec = v.get("engine_count")
        name = pkg["package"]
        if "208b" in name and "livery" not in name:
            print(f"{name}: engine_count={ec}")
        if "a320-neo" in name and "livery" not in name:
            print(f"{name}: engine_count={ec}")
        if "quadengines" in name:
            print(f"{name}: engine_count={ec}")
        if "twinengines" in name:
            print(f"{name}: engine_count={ec}")
print()

# FIX-3: Quotes
print("=== FIX-3: QUOTES ===")
quote_issues = []
for pkg in d["packages"]:
    for v in pkg.get("variants", []):
        for t in v.get("titles", []):
            if t.startswith('"') or t.startswith("'"):
                quote_issues.append(f"{pkg['package']}: {t}")
        for field in ["atc_type", "atc_model", "category"]:
            val = v.get(field)
            if val and (val.startswith('"') or val.startswith("'")):
                quote_issues.append(f"{pkg['package']}.{field}: {val}")
if quote_issues:
    for q in quote_issues:
        print(f"  QUOTE ISSUE: {q}")
else:
    print("  No quote issues found")
print()

# FIX-4: Liveries
print("=== FIX-4: LIVERIES ===")
print(f"  Aircraft packages: {m['aircraft_packages']}")
print(f"  Livery packages: {m['livery_packages']}")
print(f"  Total: {m['aircraft_packages'] + m['livery_packages']}")
print()

# FIX-5: max_bank
print("=== FIX-5: MAX_BANK ===")
for pkg in d["packages"]:
    if not pkg["readable"] or pkg["is_livery"]:
        continue
    for v in pkg["variants"]:
        ap = v.get("autopilot", {})
        if ap and "max_bank" in ap:
            mb = ap["max_bank"]
            if isinstance(mb, dict):
                print(f"{pkg['package']}: raw='{mb.get('raw')}', values={mb.get('values')}")
            else:
                print(f"{pkg['package']}: max_bank={mb} (NOT structured)")
print()

# FIX-6: analyze_dataset.py
print("=== FIX-6: analyze_dataset.py ===")
print("  Kept as validator, will update to new schema")
