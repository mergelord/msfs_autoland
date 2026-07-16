## Summary

READ-ONLY extraction of MSFS 2020 default aircraft dataset from local installation.

### What was extracted

- **216 aircraft packages** scanned (asobo-aircraft-*, microsoft-aircraft-*)
- **212 readable**, 4 encrypted (Deluxe/Premium: Pitts S1 Reno, A310, A320neo, Volocity)
- **222 simobject variants**, **256 unique titles**
- Per-variant data: aircraft.cfg, engines.cfg, systems.cfg, flight_model.cfg
- L/H/B vars scanned from model XML, panel, html_ui files

### Key findings

- **13 aircraft without autopilot**: C152, Cabri G2, CAP10C, DG-1001E, DR400, E330, FlightDesign CT, ICON, LS8, Pitts, VL3, JN4, Wright Flyer
- **5 aircraft with autothrottle**: A320neo, F/A-18E, Generic Airliner (quad/twin), Bell 407
- **4 aircraft with 20+ LVars**: DG-1001E (26), F/A-18E (28), DHC-2 (28), Hughes H-4 (21)

### Deliverables

```
TASKS/TOOLS/extract_msfs2020_default_aircraft.py  — standalone extractor script
TASKS/DATA/msfs2020_default_aircraft_dataset.json — 10,700-line JSON dataset
TASKS/REVIEWS/DATASET-MSFS2020-DEFAULT-AIRCRAFT-5B15AE1.md — report
```

### Verification

```
JSON valid: python -m json.tool passes
399 tests unchanged (0 production code modified)
git diff --stat: only TASKS/ additions
```
