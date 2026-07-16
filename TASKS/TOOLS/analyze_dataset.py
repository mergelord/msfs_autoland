#!/usr/bin/env python3
"""Analyze the extracted MSFS 2020 aircraft dataset."""
import json

with open("TASKS/DATA/msfs2020_default_aircraft_dataset.json") as f:
    d = json.load(f)

m = d["meta"]
print("=== DATASET SUMMARY ===")
print(f"Sim: {m['sim']}, Channel: {m['channel']}")
print(f"Total packages: {m['total_packages']}")
print(f"  Aircraft packages: {m['aircraft_packages']}")
print(f"  Livery packages: {m['livery_packages']}")
print(f"Readable: {m['readable_packages']}, Unreadable: {m['unreadable_packages']}")
print(f"Aircraft variants: {m['aircraft_variants']}, Aircraft titles: {m['aircraft_titles']}")
print()

# Unreadable
print("=== UNREADABLE PACKAGES ===")
for p in d["packages"]:
    if not p["readable"]:
        print(f"  {p['package']}: {p['errors']}")
print()

# Anomalies
print("=== ANOMALIES ===")
for p in d["packages"]:
    if not p["readable"] or p["is_livery"] or not p["variants"]:
        continue
    v = p["variants"][0]
    ap = v.get("autopilot", {})
    if ap and not ap.get("autopilot_available"):
        print(f"  NO AP: {p['package']}")
    if ap and ap.get("autothrottle_available"):
        print(f"  HAS AUTO throttle: {p['package']}")
    if len(v.get("lvars", [])) > 20:
        print(f"  MANY LVars ({len(v['lvars'])}): {p['package']}")
    ec = v.get("engine_count")
    if ec is None:
        print(f"  NULL ENGINE COUNT: {p['package']}")
print()

# Count unique titles (aircraft only)
all_titles = set()
for p in d["packages"]:
    if p["is_livery"]:
        continue
    for v in p.get("variants", []):
        for t in v.get("titles", []):
            all_titles.add(t)
print(f"Unique aircraft titles: {len(all_titles)}")

# FLAPS summary
print("\n=== FLAPS SUMMARY (aircraft only) ===")
for p in d["packages"]:
    if not p["readable"] or p["is_livery"] or not p["variants"]:
        continue
    v = p["variants"][0]
    flaps = v.get("flaps", {})
    total = flaps.get("total_positions", 0)
    sections = flaps.get("sections", [])
    if total == 0 and sections:
        print(f"  {p['package']}: {len(sections)} sections but 0 positions")
    elif total > 0:
        angles = []
        for s in sections:
            for pos in s.get("positions", []):
                angles.append(pos.get("angle_deg"))
        print(f"  {p['package']}: {total} positions, angles={angles}")
