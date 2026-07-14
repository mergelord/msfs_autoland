#!/usr/bin/env python3
"""Check if the current architecture snapshot is fresh relative to production code.

Usage:
    python check_snapshot_freshness.py --repo-root . --current-file docs/architecture/CURRENT.json
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def compute_production_digest(repo_root: Path) -> str:
    """Compute deterministic SHA-256 digest of production files.

    Algorithm: sha256-path-null-content-v1
    - Sort files by relative path
    - For each file: hash(path_bytes + b'\x00' + content_bytes)
    - Concatenate all hashes and hash the result
    """
    production_patterns = ["main.py", "gui.py"]
    module_files = sorted(repo_root.glob("modules/**/*.py"))

    all_files = []
    for pattern in production_patterns:
        p = repo_root / pattern
        if p.exists():
            all_files.append(p)
    all_files.extend(module_files)

    # Filter out __pycache__
    all_files = [f for f in all_files if "__pycache__" not in str(f)]

    hasher = hashlib.sha256()
    for f in sorted(all_files, key=lambda x: str(x.relative_to(repo_root))):
        rel = str(f.relative_to(repo_root)).replace("\\", "/")
        content = f.read_bytes()
        # Hash: path + null + content
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\x00")
        hasher.update(content)

    return hasher.hexdigest()


def find_valid_diff(diff_root: Path, to_digest: str) -> dict | None:
    """Find an architecture-diff whose to_production_digest matches."""
    if not diff_root.exists():
        return None

    for diff_dir in diff_root.iterdir():
        if not diff_dir.is_dir():
            continue
        diff_file = diff_dir / "architecture-diff.json"
        if not diff_file.exists():
            continue
        try:
            with open(diff_file) as f:
                diff = json.load(f)
            if diff.get("to_production_digest") == to_digest:
                if diff.get("review_status") in ("APPROVED", "PENDING"):
                    return diff
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def main():
    parser = argparse.ArgumentParser(description="Check architecture snapshot freshness")
    parser.add_argument("--repo-root", default=".", help="Repository root directory")
    parser.add_argument("--current-file", default="docs/architecture/CURRENT.json",
                        help="Path to CURRENT.json")
    parser.add_argument("--diff-root", default="docs/architecture/diffs",
                        help="Root directory for architecture diffs")
    parser.add_argument("--json-output", action="store_true",
                        help="Output machine-readable JSON")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    current_file = repo_root / args.current_file
    diff_root = repo_root / args.diff_root

    # Read CURRENT.json
    if not current_file.exists():
        status = "ERROR"
        message = f"CURRENT.json not found: {current_file}"
        _output(status, message, args.json_output)
        return 1

    with open(current_file) as f:
        current = json.load(f)

    snapshot_digest = current.get("production_digest", "")

    # Compute current production digest
    try:
        production_digest = compute_production_digest(repo_root)
    except Exception as e:
        status = "ERROR"
        message = f"Failed to compute production digest: {e}"
        _output(status, message, args.json_output)
        return 1

    # Compare
    if snapshot_digest == "PLACEHOLDER_COMPUTED_AT_COMMIT_TIME":
        # First run — compute and write
        current["production_digest"] = production_digest
        current["status"] = "CURRENT"
        with open(current_file, "w") as f:
            json.dump(current, f, indent=2)
        status = "CURRENT"
        message = f"Production digest computed and written: {production_digest[:16]}..."
    elif production_digest == snapshot_digest:
        status = "CURRENT"
        message = "Production digest matches snapshot."
    else:
        # Check for valid architecture-diff
        diff = find_valid_diff(diff_root, production_digest)
        if diff:
            status = "CURRENT_WITH_ARCHITECTURE_DIFF"
            message = (f"Production changed but valid architecture-diff found: "
                       f"{diff.get('from_snapshot', 'unknown')}")
        else:
            status = "STALE"
            message = ("Current production tree differs from baseline snapshot.\n"
                       "Required: regenerate snapshot or add a validated architecture-diff.")

    _output(status, message, args.json_output)
    return 0 if status in ("CURRENT", "CURRENT_WITH_ARCHITECTURE_DIFF") else 1


def _output(status: str, message: str, json_output: bool):
    if json_output:
        print(json.dumps({"status": status, "message": message}))
    else:
        print(f"ARCHITECTURE STATUS: {status}")
        print(message)

    # Write to GITHUB_STEP_SUMMARY if available
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"## Architecture Documentation\n\n")
            f.write(f"**Status:** {status}\n\n")
            f.write(f"{message}\n\n")


if __name__ == "__main__":
    sys.exit(main())
