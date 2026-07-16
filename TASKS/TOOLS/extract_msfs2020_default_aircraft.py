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
                # Strip MSFS comments
                lines = []
                for line in content.splitlines():
                    stripped = line.split(";")[0].split("//")[0]
                    lines.append(stripped)
                super().read_file(io.StringIO("\n".join(lines)), source=filename)
            except Exception:
                pass


def read_cfg(path: Path) -> MsfsCfgParser:
    """Read a .cfg file, return parser (may be empty on error)."""
    cfg = MsfsCfgParser()
    if path.exists():
        try:
            cfg.read([str(path)])
        except Exception:
            pass
    return cfg


def find_cfg(package: Path, name: str) -> Path | None:
    """Find a .cfg file in SimObjects/Airplanes subdirectories."""
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
# Aircraft CFG
# ---------------------------------------------------------------------------

def extract_aircraft_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "aircraft.cfg")
    if not cfg_path:
        return {"error": "aircraft.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    # [GENERAL]
    if cfg.has_section("GENERAL"):
        for key in ["atc_type", "atc_model", "category", "icao_type_designator",
                     "icao_manufacturer", "icao_model"]:
            result[key] = cfg.get("GENERAL", key, fallback=None)

    # [FLTSIM.N] sections — titles
    titles = []
    for section in cfg.sections():
        if section.upper().startswith("FLTSIM"):
            title = cfg.get(section, "title", fallback=None)
            if title:
                titles.append(title)
            for key in ["ui_manufacturer", "ui_type", "ui_variation"]:
                val = cfg.get(section, key, fallback=None)
                if val and key not in result:
                    result[key] = val
    result["titles"] = titles

    return result


# ---------------------------------------------------------------------------
# Engines CFG
# ---------------------------------------------------------------------------

def extract_engines_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "engines.cfg")
    if not cfg_path:
        return {"error": "engines.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    # [GENERALENGINEDATA]
    if cfg.has_section("GENERALENGINEDATA"):
        result["engine_type"] = cfg.getint("GENERALENGINEDATA", "engine_type", fallback=None)

    # Count [ENGINE.N] sections
    engine_count = 0
    for section in cfg.sections():
        if section.upper().startswith("ENGINE"):
            try:
                num = int(section.split(".")[-1])
                engine_count = max(engine_count, num)
            except (ValueError, IndexError):
                pass
    result["engine_count"] = engine_count if engine_count > 0 else None

    return result


# ---------------------------------------------------------------------------
# Systems CFG — autopilot
# ---------------------------------------------------------------------------

def extract_systems_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "systems.cfg")
    if not cfg_path:
        return {"error": "systems.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    if cfg.has_section("AUTOPILOT"):
        ap = {}
        for key in ["autopilot_available", "flight_director_available",
                     "autothrottle_available", "max_bank",
                     "use_no_default_autopilot", "max_pitch",
                     "max_vertical_speed", "min_vertical_speed"]:
            val = cfg.get("AUTOPILOT", key, fallback=None)
            if val is not None:
                # Try numeric conversion
                try:
                    val = float(val)
                    if val == int(val):
                        val = int(val)
                except (ValueError, TypeError):
                    pass
                ap[key] = val
        result["autopilot"] = ap
    else:
        result["autopilot"] = None

    return result


# ---------------------------------------------------------------------------
# Flight model CFG — flaps
# ---------------------------------------------------------------------------

def extract_flight_model_cfg(package: Path) -> dict:
    cfg_path = find_cfg(package, "flight_model.cfg")
    if not cfg_path:
        return {"error": "flight_model.cfg not found", "source": None}

    cfg = read_cfg(cfg_path)
    result = {"source": str(cfg_path)}

    flaps_sections = 0
    flaps_positions = []
    for section in cfg.sections():
        if section.upper().startswith("FLAPS"):
            flaps_sections += 1
            # Look for flaps-position.N keys
            for key, val in cfg.items(section):
                if "flaps-position" in key.lower() or "position" in key.lower():
                    try:
                        flaps_positions.append(float(val))
                    except (ValueError, TypeError):
                        pass

    result["flaps_sections"] = flaps_sections
    result["flaps_positions"] = sorted(set(flaps_positions)) if flaps_positions else []

    return result


# ---------------------------------------------------------------------------
# Var scanning (L/H/B vars)
# ---------------------------------------------------------------------------

VAR_PATTERN = re.compile(r"\((L:[^),\s]+)\)|\(H:[^),\s]+\)\)|\(B:[^),\s]+\)")


def scan_vars_in_file(filepath: Path) -> tuple[set, set, set]:
    """Scan a single file for L/H/B vars."""
    lvars, hvars, bvars = set(), set(), set()
    try:
        # Skip files > 20MB
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
    """Scan model/*.xml, panel/*, html_ui/* for vars."""
    all_lvars, all_hvars, all_bvars = set(), set(), set()
    custom_logic = False

    simobjects = package / "SimObjects" / "Airplanes"
    if not simobjects.exists():
        return {"lvars": [], "hvars": [], "bvars": [], "custom_logic": False}

    for variant_dir in simobjects.iterdir():
        if not variant_dir.is_dir():
            continue

        # Scan model/*.xml
        model_dir = variant_dir / "model"
        if model_dir.exists():
            for xml_file in model_dir.glob("*.xml"):
                lv, hv, bv = scan_vars_in_file(xml_file)
                all_lvars |= lv
                all_hvars |= hv
                all_bvars |= bv

        # Scan panel/*.xml, panel/*.html
        panel_dir = variant_dir / "panel"
        if panel_dir.exists():
            for f in panel_dir.glob("*.*"):
                if f.suffix in (".xml", ".html", ".htm"):
                    lv, hv, bv = scan_vars_in_file(f)
                    all_lvars |= lv
                    all_hvars |= hv
                    all_bvars |= bv

        # Scan html_ui/* for custom JS
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
# Detect channel (Steam vs MS Store)
# ---------------------------------------------------------------------------

def detect_channel(usercfg_path: Path) -> str:
    try:
        content = usercfg_path.read_text(encoding="utf-8", errors="replace")
        if "Steam" in content or "steam" in str(usercfg_path):
            return "steam"
    except Exception:
        pass
    # Check parent dirs
    if "Steam" in str(usercfg_path):
        return "steam"
    return "msstore"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Step 0: Locate installation
    steam_cfg = Path.home() / "AppData" / "Roaming" / "Microsoft Flight Simulator" / "UserCfg.opt"
    msstore_cfg = Path.home() / "AppData" / "Local" / "Packages" / "Microsoft.FlightSimulator_8wekyb3d8bbwe" / "LocalCache" / "UserCfg.opt"

    usercfg = None
    if steam_cfg.exists():
        usercfg = steam_cfg
    elif msstore_cfg.exists():
        usercfg = msstore_cfg
    else:
        # Try known path
        known = Path(r"R:\GAMES\Official\Steam")
        if known.exists():
            # Derive UserCfg from known path
            usercfg = Path(r"C:\Users\MYRIG\AppData\Roaming\Microsoft Flight Simulator\UserCfg.opt")

    if not usercfg or not usercfg.exists():
        print("ERROR: UserCfg.opt not found", file=sys.stderr)
        sys.exit(1)

    # Read InstalledPackagesPath
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

    # Step 1: Find aircraft packages
    aircraft_packages = []
    for d in sorted(official_dir.iterdir()):
        if d.is_dir() and (d.name.startswith("asobo-aircraft-") or d.name.startswith("microsoft-aircraft-")):
            aircraft_packages.append(d)

    print(f"Found {len(aircraft_packages)} aircraft packages in {official_dir}")

    # Get game version
    game_version = None
    fs_base = official_dir / "fs-base"
    if fs_base.exists():
        manifest = extract_manifest(fs_base)
        if manifest:
            game_version = manifest.get("package_version")

    # Step 2: Extract per package
    packages_data = []
    total_variants = 0
    total_titles = 0
    readable_count = 0
    unreadable_count = 0

    for pkg in aircraft_packages:
        print(f"  Processing: {pkg.name}")
        pkg_data = {
            "package": pkg.name,
            "readable": True,
            "manifest": None,
            "variants": [],
            "errors": [],
        }

        # Manifest
        manifest = extract_manifest(pkg)
        if manifest:
            pkg_data["manifest"] = {
                "creator": manifest.get("creator"),
                "title": manifest.get("title"),
                "package_version": manifest.get("package_version"),
                "minimum_game_version": manifest.get("minimum_game_version"),
                "content_type": manifest.get("content_type"),
            }

        # Check for SimObjects
        simobjects = pkg / "SimObjects" / "Airplanes"
        if not simobjects.exists():
            pkg_data["errors"].append("No SimObjects/Airplanes directory")
            pkg_data["readable"] = False
            unreadable_count += 1
            packages_data.append(pkg_data)
            continue

        # Check for .fsarchive (encrypted)
        for f in pkg.rglob("*.fsarchive"):
            pkg_data["errors"].append(f"Encrypted archive: {f.name}")
            pkg_data["readable"] = False
            break

        if not pkg_data["readable"]:
            unreadable_count += 1
            packages_data.append(pkg_data)
            continue

        readable_count += 1

        # Process each variant
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

            # Aircraft CFG
            ac_cfg = extract_aircraft_cfg(pkg)
            variant_data["source_paths"]["aircraft_cfg"] = ac_cfg.get("source")
            variant_data["titles"] = ac_cfg.get("titles", [])
            variant_data["atc_type"] = ac_cfg.get("atc_type")
            variant_data["atc_model"] = ac_cfg.get("atc_model")
            variant_data["category"] = ac_cfg.get("category")
            variant_data["icao_type_designator"] = ac_cfg.get("icao_type_designator")
            variant_data["ui_manufacturer"] = ac_cfg.get("ui_manufacturer")
            variant_data["ui_type"] = ac_cfg.get("ui_type")

            # Engines CFG
            en_cfg = extract_engines_cfg(pkg)
            variant_data["source_paths"]["engines_cfg"] = en_cfg.get("source")
            variant_data["engine_type"] = en_cfg.get("engine_type")
            variant_data["engine_count"] = en_cfg.get("engine_count")

            # Systems CFG
            sys_cfg = extract_systems_cfg(pkg)
            variant_data["source_paths"]["systems_cfg"] = sys_cfg.get("source")
            variant_data["autopilot"] = sys_cfg.get("autopilot")

            # Flight model CFG
            fm_cfg = extract_flight_model_cfg(pkg)
            variant_data["source_paths"]["flight_model_cfg"] = fm_cfg.get("source")
            variant_data["flaps"] = {
                "sections": fm_cfg.get("flaps_sections"),
                "positions": fm_cfg.get("flaps_positions"),
            }

            # Vars scan (per variant)
            vars_data = scan_package_vars(pkg)
            variant_data["lvars"] = vars_data["lvars"]
            variant_data["hvars"] = vars_data["hvars"]
            variant_data["bvars"] = vars_data["bvars"]
            variant_data["custom_logic"] = vars_data["custom_logic"]

            pkg_data["variants"].append(variant_data)
            total_variants += 1
            total_titles += len(variant_data["titles"])

        packages_data.append(pkg_data)

    # Step 3: Build output
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
            "readable_packages": readable_count,
            "unreadable_packages": unreadable_count,
            "total_variants": total_variants,
            "total_titles": total_titles,
        },
        "packages": packages_data,
    }

    # Write JSON
    output_path = Path("TASKS/DATA/msfs2020_default_aircraft_dataset.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nDataset written to: {output_path}")
    print(f"Total packages: {len(aircraft_packages)}")
    print(f"Readable: {readable_count}, Unreadable: {unreadable_count}")
    print(f"Total variants: {total_variants}")
    print(f"Total titles: {total_titles}")


if __name__ == "__main__":
    main()
