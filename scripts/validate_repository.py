"""Validate the bilingual release, data ledger, arrays, manifest and tests."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_summary(name: str) -> None:
    path = DATA / "completed-runs" / f"{name}_summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    require(summary["complete"] is True, f"{name}: complete must be true")
    require(summary["paper_usable"] is True, f"{name}: paper_usable must be true")
    require(summary["spatial_solver_changed"] is False, f"{name}: spatial solver changed")
    require(summary["source"]["geometry_drawn"] is False, f"{name}: trough geometry inferred")
    ledger = summary["water_ledger_km3"]
    require(abs(ledger["raw_release"] - ledger["loss_one_minus_c"] - ledger["effective_after_c"]) < 1e-5,
            f"{name}: raw/effective/loss ledger does not close")
    accounted = (ledger["source_basin_storage"] + ledger["downstream_surface_storage"]
                 + ledger["open_boundary_outflow"] + ledger["unresolved_if_partial"])
    require(abs(ledger["effective_after_c"] - accounted) < 2e-5,
            f"{name}: effective spatial ledger does not close")
    require(abs(summary["numerics"]["downstream_mass_error"]) < 1e-6,
            f"{name}: mass error exceeds tolerance")
    require(summary["outputs"]["site_count"] == 3, f"{name}: expected three CRISM sites")
    for suffix in ("arrival_years", "current_depth_m", "maximum_depth_m", "wet_duration_years"):
        array = np.load(DATA / "completed-runs" / f"{name}_{suffix}.npy")
        require(array.shape == (275, 342), f"{name}_{suffix}: unexpected shape {array.shape}")


def validate_manifest() -> None:
    manifest = DATA / "data_manifest.csv"
    require(manifest.exists(), "data/data_manifest.csv is missing")
    with manifest.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(rows, "data manifest is empty")
    for row in rows:
        path = DATA / Path(row["path"])
        require(path.is_file(), f"manifest file missing: {row['path']}")
        require(path.stat().st_size == int(row["bytes"]), f"size mismatch: {row['path']}")
        require(sha256(path) == row["sha256"], f"checksum mismatch: {row['path']}")


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    required = [
        "index.html", "index_zh.html", "README.md", "README_ZH.md", "METHODS.md",
        "METHODS_ZH.md", "DATA_SOURCES.md", "DATA_SOURCES_ZH.md", "CITATION.cff",
        "paper_english/Figure_1_interactive_model.tif",
        "paper_english/Figure_2_completed_runs.tif",
    ]
    for relative in required:
        require((ROOT / relative).is_file(), f"required file missing: {relative}")

    english = (ROOT / "index.html").read_text(encoding="utf-8")
    chinese = (ROOT / "index_zh.html").read_text(encoding="utf-8")
    require("index_zh.html" in english, "English page lacks Chinese switch")
    require("index.html" in chinese, "Chinese page lacks English switch")

    validate_summary("low")
    validate_summary("high")
    medium = json.loads((DATA / "excluded/medium_summary_incomplete.json").read_text(encoding="utf-8"))
    require(medium["complete"] is False and medium["paper_usable"] is False,
            "medium scenario must remain explicitly excluded")
    validate_manifest()

    duplicate = ROOT / "model/inputs/conservative-model.npz"
    if duplicate.exists():
        require(sha256(duplicate) == sha256(DATA / "conservative-model.npz"),
                "legacy duplicate model input differs from canonical data input")

    run([sys.executable, "-m", "unittest", "discover", "-s", "model/tests", "-p", "test_*.py", "-v"])
    node = shutil.which("node")
    if node:
        run([node, "model/validate_release.js"])
    else:
        print("node not found; JavaScript syntax validation skipped")
    print("repository validation passed")


if __name__ == "__main__":
    main()
