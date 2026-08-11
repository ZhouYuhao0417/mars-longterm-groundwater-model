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
ACCEPTED = DATA / "accepted-v2"


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


def validate_accepted_bundle() -> None:
    manifest_path = ACCEPTED / "accepted_v2_manifest.json"
    require(manifest_path.is_file(), "accepted v2 manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest.get("schema") == "accepted-hydrology-v2-browser-display-1",
            "accepted v2 schema mismatch")
    require(manifest.get("grid") == {"rows": 275, "cols": 342, "cell_m": 400},
            "accepted v2 grid mismatch")
    thresholds = manifest.get("thresholds_m", {})
    require(thresholds == {"numerical_front": 0.015, "reporting_reach": 0.05,
                           "default_map_display": 0.1},
            "accepted v2 threshold contract mismatch")
    source = manifest.get("source_interpretation", {})
    require("not surface flow" in source.get("en", "") and "不代表沿东北—西南向" in source.get("zh", ""),
            "accepted source interpretation is missing the NE-SW trough boundary")

    scenarios = manifest.get("scenarios", {})
    require(set(scenarios) == {"low_f64_v2", "medium_f64_v2"},
            "accepted viewer must contain exactly v2 low and medium")
    for key, scenario in scenarios.items():
        qa = scenario.get("qa", {})
        require(qa == {"complete": True, "paper_usable": True, "all_gates_true": True},
                f"{key}: accepted QA gates failed")
        numerics = scenario.get("numerics", {})
        require(numerics.get("downstream_time_skipping") is False,
                f"{key}: downstream time skipping is not allowed")
        require(abs(float(numerics.get("downstream_mass_error", 1.0))) < 1e-6,
                f"{key}: downstream mass error exceeds tolerance")
        require(abs(float(numerics.get("total_ledger_relative_error", 1.0))) < 1e-6,
                f"{key}: total ledger error exceeds tolerance")
        ledger = scenario["ledger_km3"]
        require(abs(ledger["raw_release"] - ledger["effective_after_c"]
                    - ledger["loss_one_minus_c"]) < 1e-5,
                f"{key}: raw/effective/loss ledger does not close")
        accounted = (ledger["source_basin_storage"] + ledger["downstream_surface_storage"]
                     + ledger["open_boundary_outflow"] + ledger["unresolved_if_partial"])
        require(abs(ledger["effective_after_c"] - accounted) < 2e-5,
                f"{key}: effective ledger does not close")
    low = scenarios["low_f64_v2"]
    medium = scenarios["medium_f64_v2"]
    require(low["fill_years"] is None and low["numerics"]["explicit_surface_years"] == 0.0,
            "low must remain analytical no-spill")
    require(abs(medium["fill_years"] - 2.66022743256382) < 1e-12,
            "medium source-fill time mismatch")
    require(abs(medium["numerics"]["explicit_surface_years"] - 17.339772567436178) < 1e-12,
            "medium explicit-routing duration mismatch")
    require(medium["numerics"]["hydrodynamic_dtype"] == "float64"
            and medium["numerics"]["surface_dt_s"] == 600.0,
            "medium numerical precision/step mismatch")

    files = manifest.get("files", {})
    require(len(files) == 12, "accepted v2 file inventory must contain 12 files")
    for name, record in files.items():
        path = ACCEPTED / name
        require(path.is_file(), f"accepted file missing: {name}")
        require(path.stat().st_size == int(record["bytes"]), f"accepted size mismatch: {name}")
        require(sha256(path) == record["display_sha256"], f"accepted hash mismatch: {name}")
        if name.endswith(".f32"):
            values = np.fromfile(path, dtype="<f4")
            require(values.size == 275 * 342, f"accepted array shape mismatch: {name}")

    sites = manifest.get("sites", [])
    require([item.get("site") for item in sites] == ["HW1", "HW2", "HW3"],
            "accepted site inventory mismatch")
    medium_maximum = np.fromfile(ACCEPTED / "medium_f64_v2_maximum.f32", dtype="<f4").reshape(275, 342)
    for site in sites:
        value = float(medium_maximum[int(site["row"]), int(site["col"])])
        require(value > thresholds["reporting_reach"], f"{site['site']}: not reporting-wet")
        require(abs(value - float(site["accepted_medium_maximum_depth_m"])) < 1e-5,
                f"{site['site']}: display depth mismatch")


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    required = [
        "index.html", "index_zh.html", "accepted_runs.html", "accepted_runs_zh.html",
        "README.md", "README_ZH.md", "METHODS.md",
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
    require("accepted_runs.html" in english and "accepted_runs.html?lang=zh" in chinese,
            "parameter explorers lack accepted low/medium viewer links")
    require("combined discharge of two conceptual troughs" not in english,
            "English parameter explorer retains the obsolete two-trough source claim")
    require("两条概念沟槽合计" not in chinese,
            "Chinese parameter explorer retains the obsolete two-trough source claim")

    accepted_page = (ROOT / "accepted_runs.html").read_text(encoding="utf-8")
    accepted_redirect = (ROOT / "accepted_runs_zh.html").read_text(encoding="utf-8")
    require("accepted-hydrology-v2-browser-display-1" in accepted_page,
            "accepted viewer lacks schema guard")
    require("data/accepted-v2/accepted_v2_manifest.json" in accepted_page,
            "accepted viewer lacks manifest request")
    require("accepted_runs.html?lang=zh" in accepted_redirect,
            "Chinese accepted-viewer redirect is invalid")

    validate_accepted_bundle()
    validate_summary("low")
    validate_summary("high")
    medium = json.loads((DATA / "excluded/medium_summary_incomplete.json").read_text(encoding="utf-8"))
    require(medium["complete"] is False and medium["paper_usable"] is False,
            "historical incomplete medium checkpoint must remain excluded")
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
