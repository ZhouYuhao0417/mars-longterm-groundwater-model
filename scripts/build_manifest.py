"""Build the checksum manifest for distributed data artifacts."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUTPUT = DATA / "data_manifest.csv"


def classify(relative: str) -> tuple[str, str, str]:
    if relative == "conservative-model.npz":
        return "canonical derived model input", "model input", "HRSC_CTX_derived"
    if relative == "crism_selected_sites.csv":
        return "prescribed CRISM site table", "model input", "CRISM_HRL0001FC92"
    if relative.startswith("completed-runs/"):
        return "completed exact 2-D run artifact", "paper-usable or numerical audit", "exact_2d_run"
    if relative.startswith("excluded/"):
        return "incomplete-run audit record", "excluded from quantitative claims", "incomplete_audit"
    if relative.startswith("derived/"):
        return "derived visualization layer", "non-quantitative", "CTX_HRSC_visualization"
    return "supporting data", "supporting", "project"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    rows = []
    for path in sorted(DATA.rglob("*")):
        if not path.is_file() or path == OUTPUT:
            continue
        relative = path.relative_to(DATA).as_posix()
        role, status, provenance = classify(relative)
        rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "role": role,
                "publication_status": status,
                "provenance_key": provenance,
            }
        )
    with OUTPUT.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {OUTPUT.relative_to(ROOT)} with {len(rows)} records")


if __name__ == "__main__":
    main()
