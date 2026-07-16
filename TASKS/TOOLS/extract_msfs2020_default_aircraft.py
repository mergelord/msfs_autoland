#!/usr/bin/env python3
"""
One-shot extractor: MSFS 2020 default aircraft dataset.
READ-ONLY — reads files from local MSFS installation, writes nothing to sim folders.

Usage: python TASKS/TOOLS/extract_msfs2020_default_aircraft.py
"""
import configparser
import io
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# CFG parser that handles MSFS quirks (duplicate keys, comments)
# ---------------------------------------------------------------------------

class MsfsCfgParser(configparser.RawConfigParser):
    """ConfigParser with duplicate-key tolerance and MSFS comment handling."""

    def __init__(self):
        super().__init__(strict=False, interpolation=None)

    def read(self, filenames, encoding="utf-8"):
        """Read with MSFS comment stripping (; and //)."""
        for filename in filenames:
            try:
                with open(filename, encoding=encoding, errors="replace") as f:
                    content = f.read()
                lines = []
                for line in content.splitlines():
                    stripped = line.split(";")[0].split("//")[0]
                    lines.append(stripped)
                super().read_file(io.StringIO("\n".join(lines)), source=filename)
            except Exception:
                pass


def read_cfg(path: Path) -> MsfsCfgParser:
    cfg = MsfsCfgParser()
    if path.exists():
        try:
            cfg.read([str(path)])
        except Exception:
            pass
    return cfg


def find_cfg(package: Path, name: str) -> Path | None:
    simobjects = package / "SimObjects" / "Airplanes"
    if not simobjects.exists():
        return None
    for variant_dir in simobjects.iterdir():
        if variant_dir.is_dir():
            cfg_path = variant_dir / name
            if cfg_path.exists():
                return cfg_path
    return None


# ---------------------------------------------------------------------------
# FIX-3: Strip quotes and trim
# ---------------------------------------------------------------------------

def strip_quotes(val: str | None) -> str | None:
    """Remove surrounding quotes (single or double) and trim whitespace."""
    if val is None:
        return None
    val = val.strip()
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ('"', "'"):
        val = val[1:-1].strip()
    return val if val else None


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

def extract_manifest(package: Path) -> dict | None:
    manifest_path = package / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Aircraft CFG (FIX-3: strip quotes)
# ---------------------------------------------------------------------------

def extract_aircraft_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "aircraft.cfg")
    if not cfg_path:
        return {"error": "aircraft.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    if cfg.has_section("GENERAL"):
        for key in ["atc_type", "atc_model", "category", "icao_type_designator",
                     "icao_manufacturer", "icao_model"]:
            result[key] = strip_quotes(cfg.get("GENERAL", key, fallback=None))

    titles = []
    for section in cfg.sections():
        if section.upper().startswith("FLTSIM"):
            title = strip_quotes(cfg.get(section, "title", fallback=None))
            if title:
                titles.append(title)
            for key in ["ui_manufacturer", "ui_type", "ui_variation"]:
                val = strip_quotes(cfg.get(section, key, fallback=None))
                if val and key not in result:
                    result[key] = val
    result["titles"] = titles

    return result


# ---------------------------------------------------------------------------
# Engines CFG (FIX-2: count ENGINE.N sections properly)
# ---------------------------------------------------------------------------

ENGINE_SECTION_RE = re.compile(r"^ENGINE\.(\d+)$", re.IGNORECASE)
ENGINE_KEY_RE = re.compile(r"^Engine\.(\d+)$", re.IGNORECASE)

def extract_engines_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "engines.cfg")
    if not cfg_path:
        return {"error": "engines.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    if cfg.has_section("GENERALENGINEDATA"):
        result["engine_type"] = cfg.getint("GENERALENGINEDATA", "engine_type", fallback=None)

    # Count engine sources:
    # 1. [ENGINE.N] sections (piston aircraft)
    engine_indices = set()
    for section in cfg.sections():
        m = ENGINE_SECTION_RE.match(section)
        if m:
            engine_indices.add(int(m.group(1)))

    # 2. Engine.N keys in [GENERALENGINEDATA] (jet/turboprop aircraft)
    if cfg.has_section("GENERALENGINEDATA"):
        for key, _ in cfg.items("GENERALENGINEDATA"):
            m = ENGINE_KEY_RE.match(key)
            if m:
                engine_indices.add(int(m.group(1)))

    if engine_indices:
        result["engine_count"] = len(engine_indices)
    else:
        result["engine_count"] = None

    return result


# ---------------------------------------------------------------------------
# Systems CFG — autopilot (FIX-5: parse max_bank)
# ---------------------------------------------------------------------------

def parse_csv_numeric(val: str | None) -> list[float] | None:
    """Parse a CSV string of numbers, return list of floats."""
    if val is None:
        return None
    parts = [p.strip() for p in val.split(",") if p.strip()]
    result = []
    for p in parts:
        try:
            result.append(float(p))
        except (ValueError, TypeError):
            pass
    return result if result else None


def extract_systems_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "systems.cfg")
    if not cfg_path:
        return {"error": "systems.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    if cfg.has_section("AUTOPILOT"):
        ap = {}
        for key in ["autopilot_available", "flight_director_available",
                     "autothrottle_available", "use_no_default_autopilot",
                     "max_pitch", "max_vertical_speed", "min_vertical_speed"]:
            val = cfg.get("AUTOPILOT", key, fallback=None)
            if val is not None:
                try:
                    val = float(val)
                    if val == int(val):
                        val = int(val)
                except (ValueError, TypeError):
                    pass
                ap[key] = val

        # FIX-5: max_bank as structured data
        raw_bank = cfg.get("AUTOPILOT", "max_bank", fallback=None)
        if raw_bank is not None:
            bank_values = parse_csv_numeric(raw_bank)
            ap["max_bank"] = {
                "raw": raw_bank,
                "values": bank_values,
            }

        result["autopilot"] = ap
    else:
        result["autopilot"] = None

    return result


# ---------------------------------------------------------------------------
# Flight model CFG — flaps (FIX-1: match only flaps-position.<N>)
# ---------------------------------------------------------------------------

FLAPS_POSITION_KEY_RE = re.compile(r"^flaps[\-_\.]?position[\-_\.]?(\d+)$", re.IGNORECASE)


def extract_flight_model_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "flight_model.cfg")
    if not cfg_path:
        return {"error": "flight_model.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    # Find all FLAPS sections
    flaps_sections = []
    for section in cfg.sections():
        if section.upper().startswith("FLAPS"):
            section_data = {"section": section, "positions": []}
            for key, val in cfg.items(section):
                m = FLAPS_POSITION_KEY_RE.match(key)
                if m:
                    idx = int(m.group(1))
                    # Parse CSV: first component = angle_deg
                    angle_deg = None
                    parts = [p.strip() for p in val.split(",") if p.strip()]
                    if parts:
                        try:
                            angle_deg = float(parts[0])
                        except (ValueError, TypeError):
                            pass
                    section_data["positions"].append({
                        "index": idx,
                        "angle_deg": angle_deg,
                        "raw": val,
                    })
            # Sort positions by index
            section_data["positions"].sort(key=lambda x: x["index"])
            flaps_sections.append(section_data)

    result["flaps"] = {
        "sections": flaps_sections,
        "total_positions": sum(len(s["positions"]) for s in flaps_sections),
    }

    if cfg_path and not flaps_sections:
        result["flaps"]["note"] = "No flaps-position.N keys found in flight_model.cfg"

    return result


# ---------------------------------------------------------------------------
# Var scanning (unchanged)
# ---------------------------------------------------------------------------

def scan_vars_in_file(filepath: Path) -> tuple[set, set, set]:
    lvars, hvars, bvars = set(), set(), set()
    try:
        if filepath.stat().st_size > 20 * 1024 * 1024:
            return lvars, hvars, bvars
        content = filepath.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\(L:([^),\s]+)\)", content):
            lvars.add(m.group(1))
        for m in re.finditer(r"\(H:([^),\s]+)\)", content):
            hvars.add(m.group(1))
        for m in re.finditer(r"\(B:([^),\s]+)\)", content):
            bvars.add(m.group(1))
    except Exception:
        pass
    return lvars, hvars, bvars


def scan_package_vars(package: Path) -> dict:
    all_lvars, all_hvars, all_bvars = set(), set(), set()
    custom_logic = False

    simobjects = package / "SimObjects" / "Airplanes"
    if not simobjects.exists():
        return {"lvars": [], "hvars": [], "bvars": [], "custom_logic": False}

    for variant_dir in simobjects.iterdir():
        if not variant_dir.is_dir():
            continue

        model_dir = variant_dir / "model"
        if model_dir.exists():
            for xml_file in model_dir.glob("*.xml"):
                lv, hv, bv = scan_vars_in_file(xml_file)
                all_lvars |= lv
                all_hvars |= hv
                all_bvars |= bv

        panel_dir = variant_dir / "panel"
        if panel_dir.exists():
            for f in panel_dir.glob("*.*"):
                if f.suffix in (".xml", ".html", ".htm"):
                    lv, hv, bv = scan_vars_in_file(f)
                    all_lvars |= lv
                    all_hvars |= hv
                    all_bvars |= bv

        html_ui_dir = variant_dir / "html_ui"
        if html_ui_dir.exists():
            custom_logic = True
            for f in html_ui_dir.rglob("*.js"):
                lv, hv, bv = scan_vars_in_file(f)
                all_lvars |= lv
                all_hvars |= hv
                all_bvars |= bv

    return {
        "lvars": sorted(all_lvars),
        "hvars": sorted(all_hvars),
        "bvars": sorted(all_bvars),
        "custom_logic": custom_logic,
    }


# ---------------------------------------------------------------------------
# Detect channel
# ---------------------------------------------------------------------------

def detect_channel(usercfg_path: Path) -> str:
    try:
        content = usercfg_path.read_text(encoding="utf-8", errors="replace")
        if "Steam" in content or "steam" in str(usercfg_path):
            return "steam"
    except Exception:
        pass
    if "Steam" in str(usercfg_path):
        return "steam"
    return "msstore"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    steam_cfg = Path.home() / "AppData" / "Roaming" / "Microsoft Flight Simulator" / "UserCfg.opt"
    msstore_cfg = Path.home() / "AppData" / "Local" / "Packages" / "Microsoft.FlightSimulator_8wekyb3d8bbwe" / "LocalCache" / "UserCfg.opt"

    usercfg = None
    if steam_cfg.exists():
        usercfg = steam_cfg
    elif msstore_cfg.exists():
        usercfg = msstore_cfg
    else:
        known = Path(r"R:\GAMES\Official\Steam")
        if known.exists():
            usercfg = Path(r"C:\Users\MYRIG\AppData\Roaming\Microsoft Flight Simulator\UserCfg.opt")

    if not usercfg or not usercfg.exists():
        print("ERROR: UserCfg.opt not found", file=sys.stderr)
        sys.exit(1)

    installed_path = None
    try:
        for line in usercfg.read_text(encoding="utf-8", errors="replace").splitlines():
            if "InstalledPackagesPath" in line:
                parts = line.split('"')
                if len(parts) >= 2:
                    installed_path = Path(parts[1])
                    break
    except Exception:
        pass

    if not installed_path:
        print("ERROR: Cannot read InstalledPackagesPath", file=sys.stderr)
        sys.exit(1)

    channel = detect_channel(usercfg)
    official_dir = installed_path / "Official" / ("Steam" if channel == "steam" else "OneStore")

    if not official_dir.exists():
        print(f"ERROR: Official dir not found: {official_dir}", file=sys.stderr)
        sys.exit(1)

    aircraft_packages = []
    for d in sorted(official_dir.iterdir()):
        if d.is_dir() and (d.name.startswith("asobo-aircraft-") or d.name.startswith("microsoft-aircraft-")):
            aircraft_packages.append(d)

    print(f"Found {len(aircraft_packages)} aircraft packages in {official_dir}")

    game_version = None
    fs_base = official_dir / "fs-base"
    if fs_base.exists():
        manifest = extract_manifest(fs_base)
        if manifest:
            game_version = manifest.get("package_version")

    # Counters
    packages_data = []
    aircraft_variants = 0
    aircraft_titles = 0
    livery_packages = 0
    aircraft_packages_count = 0
    readable_count = 0
    unreadable_count = 0

    for pkg in aircraft_packages:
        print(f"  Processing: {pkg.name}")
        pkg_data = {
            "package": pkg.name,
            "readable": True,
            "is_livery": False,
            "manifest": None,
            "variants": [],
            "errors": [],
        }

        manifest = extract_manifest(pkg)
        if manifest:
            content_type = manifest.get("content_type", "")
            pkg_data["is_livery"] = content_type == "LIVERY"
            pkg_data["manifest"] = {
                "creator": manifest.get("creator"),
                "title": manifest.get("title"),
                "package_version": manifest.get("package_version"),
                "minimum_game_version": manifest.get("minimum_game_version"),
                "content_type": content_type,
            }

        simobjects = pkg / "SimObjects" / "Airplanes"
        if not simobjects.exists():
            pkg_data["errors"].append("No SimObjects/Airplanes directory")
            pkg_data["readable"] = False
            unreadable_count += 1
            packages_data.append(pkg_data)
            continue

        for f in pkg.rglob("*.fsarchive"):
            pkg_data["errors"].append(f"Encrypted archive: {f.name}")
            pkg_data["readable"] = False
            break

        if not pkg_data["readable"]:
            unreadable_count += 1
            packages_data.append(pkg_data)
            continue

        readable_count += 1
        if pkg_data["is_livery"]:
            livery_packages += 1
        else:
            aircraft_packages_count += 1

        for variant_dir in sorted(simobjects.iterdir()):
            if not variant_dir.is_dir():
                continue

            variant_data = {
                "simobject": variant_dir.name,
                "titles": [],
                "atc_type": None,
                "atc_model": None,
                "category": None,
                "icao_type_designator": None,
                "ui_manufacturer": None,
                "ui_type": None,
                "engine_type": None,
                "engine_count": None,
                "autopilot": None,
                "flaps": None,
                "lvars": [],
                "hvars": [],
                "bvars": [],
                "custom_logic": False,
                "source_paths": {},
            }

            ac_cfg = extract_aircraft_cfg(pkg)
            variant_data["source_paths"]["aircraft_cfg"] = ac_cfg.get("source")
            variant_data["titles"] = ac_cfg.get("titles", [])
            variant_data["atc_type"] = ac_cfg.get("atc_type")
            variant_data["atc_model"] = ac_cfg.get("atc_model")
            variant_data["category"] = ac_cfg.get("category")
            variant_data["icao_type_designator"] = ac_cfg.get("icao_type_designator")
            variant_data["ui_manufacturer"] = ac_cfg.get("ui_manufacturer")
            variant_data["ui_type"] = ac_cfg.get("ui_type")

            en_cfg = extract_engines_cfg(pkg)
            variant_data["source_paths"]["engines_cfg"] = en_cfg.get("source")
            variant_data["engine_type"] = en_cfg.get("engine_type")
            variant_data["engine_count"] = en_cfg.get("engine_count")

            sys_cfg = extract_systems_cfg(pkg)
            variant_data["source_paths"]["systems_cfg"] = sys_cfg.get("source")
            variant_data["autopilot"] = sys_cfg.get("autopilot")

            fm_cfg = extract_flight_model_cfg(pkg)
            variant_data["source_paths"]["flight_model_cfg"] = fm_cfg.get("source")
            variant_data["flaps"] = fm_cfg.get("flaps")

            vars_data = scan_package_vars(pkg)
            variant_data["lvars"] = vars_data["lvars"]
            variant_data["hvars"] = vars_data["hvars"]
            variant_data["bvars"] = vars_data["bvars"]
            variant_data["custom_logic"] = vars_data["custom_logic"]

            pkg_data["variants"].append(variant_data)

            if not pkg_data["is_livery"]:
                aircraft_variants += 1
                aircraft_titles += len(variant_data["titles"])

        packages_data.append(pkg_data)

    output = {
        "meta": {
            "sim": "MSFS 2020",
            "channel": channel,
            "installed_packages_path": str(installed_path),
            "official_dir": str(official_dir),
            "game_version": game_version,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "script": "TASKS/TOOLS/extract_msfs2020_default_aircraft.py",
            "total_packages": len(aircraft_packages),
            "aircraft_packages": aircraft_packages_count,
            "livery_packages": livery_packages,
            "readable_packages": readable_count,
            "unreadable_packages": unreadable_count,
            "aircraft_variants": aircraft_variants,
            "aircraft_titles": aircraft_titles,
        },
        "packages": packages_data,
    }

    output_path = Path("TASKS/DATA/msfs2020_default_aircraft_dataset.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDataset written to: {output_path}")
    print(f"Total packages: {len(aircraft_packages)} (aircraft: {aircraft_packages_count}, liveries: {livery_packages})")
    print(f"Readable: {readable_count}, Unreadable: {unreadable_count}")
    print(f"Aircraft variants: {aircraft_variants}, Aircraft titles: {aircraft_titles}")


if __name__ == "__main__":
    main()
