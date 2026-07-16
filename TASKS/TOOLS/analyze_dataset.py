#!/usr/bin/env python3
"""Quick analysis of the extracted dataset."""
import json

with open("TASKS/DATA/msfs2020_default_aircraft_dataset.json") as f:
    d = json.load(f)

m = d["meta"]
print("=== DATASET SUMMARY ===")
print(f"Sim: {m['sim']}, Channel: {m['channel']}")
print(f"Packages: {m['total_packages']} (readable: {m['readable_packages']}, unreadable: {m['unreadable_packages']})")
print(f"Variants: {m['total_variants']}, Titles: {m['total_titles']}")
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
    if not p["readable"] or not p["variants"]:
        continue
    v = p["variants"][0]
    ap = v.get("autopilot", {})
    if ap and not ap.get("autopilot_available"):
        print(f"  NO AP: {p['package']}")
    if ap and ap.get("autothrottle_available"):
        print(f"  HAS AUTO throttle: {p['package']}")
    if len(v.get("lvars", [])) > 20:
        print(f"  MANY LVars ({len(v['lvars'])}): {p['package']}")
print()

# Count unique titles
all_titles = set()
for p in d["packages"]:
    for v in p.get("variants", []):
        for t in v.get("titles", []):
            all_titles.add(t)
print(f"Unique titles across dataset: {len(all_titles)}")
