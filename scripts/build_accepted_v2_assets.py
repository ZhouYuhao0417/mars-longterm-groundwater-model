"""Build browser-ready display assets for the accepted low/medium v2 runs.

The browser files are float32 display copies of the authoritative arrays. The
manifest records source and display hashes so the website never becomes the
quantitative archive of record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


LAYERS = {
    "current_depth_m": "current",
    "maximum_depth_m": "maximum",
    "arrival_years": "arrival",
    "wet_duration_years": "duration",
}
SCENARIOS = ("low_f64_v2", "medium_f64_v2")
EXPECTED_SHAPE = (275, 342)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_summary(summary: dict, key: str) -> None:
    if summary.get("scenario", {}).get("key") != key:
        raise ValueError(f"{key}: scenario key mismatch")
    if summary.get("complete") is not True or summary.get("paper_usable") is not True:
        raise ValueError(f"{key}: run is not accepted")
    gates = summary.get("paper_usable_gates", {})
    if not gates or not all(value is True for value in gates.values()):
        raise ValueError(f"{key}: at least one paper gate is not true")
    if summary.get("numerics", {}).get("downstream_time_skipping") is not False:
        raise ValueError(f"{key}: downstream time skipping must be false")


def scenario_record(summary: dict) -> dict:
    key = summary["scenario"]["key"]
    low = key == "low_f64_v2"
    return {
        "key": key,
        "label_en": "Low — analytical no-spill" if low else "Medium — accepted routed run",
        "label_zh": "低情景—解析蓄水、不溢流" if low else "中情景—已验收二维路由",
        "mode_en": (
            "Analytical basin filling; no downstream hydrodynamic steps"
            if low
            else "Analytical prefill plus 17.339773 yr of explicit routing"
        ),
        "mode_zh": (
            "解析计算源坑蓄水；未执行下游水动力步"
            if low
            else "解析预填充后进行 17.339773 年显式二维路由"
        ),
        "duration_years": summary["completed_years"],
        "fill_years": summary.get("source_fill_years"),
        "parameters": summary["scenario"],
        "ledger_km3": summary["water_ledger_km3"],
        "outputs": summary["outputs"],
        "numerics": {
            "grid_m": summary["numerics"]["grid_m"],
            "surface_dt_s": summary["numerics"]["surface_dt_s"],
            "hydrodynamic_dtype": summary["numerics"]["hydrodynamic_dtype"],
            "explicit_surface_years": summary["numerics"]["explicit_surface_years"],
            "downstream_time_skipping": summary["numerics"]["downstream_time_skipping"],
            "downstream_mass_error": summary["numerics"]["downstream_mass_error"],
            "total_ledger_relative_error": summary["numerics"]["total_ledger_relative_error"],
        },
        "qa": {
            "complete": summary["complete"],
            "paper_usable": summary["paper_usable"],
            "all_gates_true": all(summary["paper_usable_gates"].values()),
        },
    }


def published_scenario_record(summary: dict) -> dict:
    """Return the browser record with encoding-safe bilingual labels.

    The accepted source summaries contain legacy localized names.  The browser
    package uses explicit labels so a Windows console code page cannot leak
    mojibake into the published UTF-8 manifest.
    """
    record = scenario_record(summary)
    low = summary["scenario"]["key"] == "low_f64_v2"
    record["label_en"] = (
        "Low - analytical no-spill" if low else "Medium - accepted routed run"
    )
    record["label_zh"] = (
        "\u4f4e\u60c5\u666f\u2014\u89e3\u6790\u84c4\u6c34\u3001\u4e0d\u6ea2\u6d41"
        if low
        else "\u4e2d\u60c5\u666f\u2014\u5df2\u9a8c\u6536\u4e8c\u7ef4\u8def\u7531"
    )
    record["mode_zh"] = (
        "\u89e3\u6790\u8ba1\u7b97\u6e90\u5751\u84c4\u6c34\uff1b\u672a\u6267\u884c\u4e0b\u6e38\u6c34\u52a8\u529b\u6b65"
        if low
        else "\u89e3\u6790\u9884\u586b\u5145\u540e\u8fdb\u884c 17.339773 \u5e74\u663e\u5f0f\u4e8c\u7ef4\u8def\u7531"
    )
    record["parameters"] = {
        field: summary["scenario"][field]
        for field in (
            "key", "process", "qb_m3s", "q0_m3s", "tau_years",
            "duration_years", "retention",
        )
    }
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--site-audit", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "accepted-v2",
    )
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)

    audit = json.loads(args.site_audit.read_text(encoding="utf-8"))
    selected = sorted(
        (
            {
                "site": item["site"],
                "class": item["class"],
                "row": int(item["hydrology_row"]),
                "col": int(item["hydrology_col"]),
                "lon_e": float(item["lon_e"]),
                "lat_n": float(item["lat_n"]),
                "accepted_medium_maximum_depth_m": float(item["maximum_depth_m"]),
                "cell_center_offset_m": float(item["crism_to_hydrology_cell_center_m"]),
            }
            for item in audit["candidate_pool"]
            if item.get("site")
        ),
        key=lambda item: item["site"],
    )
    if [item["site"] for item in selected] != ["HW1", "HW2", "HW3"]:
        raise ValueError("Expected retained HW1-HW3 in the site audit")

    manifest = {
        "schema": "accepted-hydrology-v2-browser-display-1",
        "grid": {"rows": EXPECTED_SHAPE[0], "cols": EXPECTED_SHAPE[1], "cell_m": 400},
        "thresholds_m": {
            "numerical_front": 0.015,
            "reporting_reach": 0.05,
            "default_map_display": 0.1,
        },
        "display_conversion": (
            "All browser arrays are little-endian float32 copies made only for display. "
            "Authoritative source arrays and JSON summaries remain the quantitative record."
        ),
        "source_interpretation": {
            "en": (
                "The prescribed source is an equivalent crater-side overflow input applied "
                "after basin filling at the candidate low-rim outlet. It is not surface flow "
                "along the northeast-southwest Nili Fossae trough and does not assume hydraulic "
                "delivery through that trough to Jezero's western-delta headwaters."
            ),
            "zh": (
                "规定源项是在源坑蓄满后、候选低坑缘出口处施加的坑侧等效溢流输入；"
                "它不代表沿东北—西南向 Nili Fossae 沟槽的地表输水，也不预设水可沿该沟槽"
                "到达 Jezero 西三角洲流域上游。"
            ),
        },
        "sites": selected,
        "scenarios": {},
        "files": {},
    }
    manifest["source_interpretation"]["zh"] = (
        "\u89c4\u5b9a\u6e90\u9879\u662f\u5728\u6e90\u5751\u84c4\u6ee1\u540e\u3001\u5019\u9009\u4f4e\u5751\u7f18\u51fa\u53e3\u5904\u65bd\u52a0\u7684\u5751\u4fa7\u7b49\u6548\u6ea2\u6d41\u8f93\u5165\uff1b"
        "\u5b83\u4e0d\u4ee3\u8868\u6cbf\u4e1c\u5317\u2014\u897f\u5357\u5411 Nili Fossae \u6c9f\u69fd\u7684\u5730\u8868\u8f93\u6c34\uff0c"
        "\u4e5f\u4e0d\u9884\u8bbe\u6c34\u53ef\u6cbf\u8be5\u6c9f\u69fd\u5230\u8fbe Jezero \u897f\u4e09\u89d2\u6d32\u6d41\u57df\u4e0a\u6e38\u3002"
    )

    for key in SCENARIOS:
        summary_path = args.source_dir / f"{key}_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        validate_summary(summary, key)
        manifest["scenarios"][key] = published_scenario_record(summary)
        summary_copy = output / summary_path.name
        shutil.copy2(summary_path, summary_copy)
        manifest["files"][summary_copy.name] = {
            "role": "authoritative accepted summary copy",
            "source_sha256": sha256(summary_path),
            "display_sha256": sha256(summary_copy),
            "bytes": summary_copy.stat().st_size,
        }

        map_source = args.source_dir / f"{key}_map.png"
        map_copy = output / map_source.name
        shutil.copy2(map_source, map_copy)
        manifest["files"][map_copy.name] = {
            "role": "authoritative runner preview map copy",
            "source_sha256": sha256(map_source),
            "display_sha256": sha256(map_copy),
            "bytes": map_copy.stat().st_size,
        }

        for source_suffix, web_suffix in LAYERS.items():
            source = args.source_dir / f"{key}_{source_suffix}.npy"
            array = np.load(source, allow_pickle=False)
            if array.shape != EXPECTED_SHAPE:
                raise ValueError(f"{source.name}: expected {EXPECTED_SHAPE}, got {array.shape}")
            if np.isinf(array).any():
                raise ValueError(f"{source.name}: infinity is not allowed")
            finite = array[np.isfinite(array)]
            if finite.size and (finite < 0).any():
                raise ValueError(f"{source.name}: negative values are not allowed")
            display = np.asarray(array, dtype="<f4")
            destination = output / f"{key}_{web_suffix}.f32"
            display.tofile(destination)
            manifest["files"][destination.name] = {
                "role": web_suffix,
                "source_name": source.name,
                "source_dtype": str(array.dtype),
                "display_dtype": "float32 little-endian",
                "shape": list(array.shape),
                "source_sha256": sha256(source),
                "display_sha256": sha256(destination),
                "bytes": destination.stat().st_size,
                "finite_min": float(finite.min()) if finite.size else None,
                "finite_max": float(finite.max()) if finite.size else None,
                "nan_count": int(np.isnan(array).sum()),
            }

    manifest_path = output / "accepted_v2_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"manifest": str(manifest_path), "files": len(manifest["files"])}, indent=2))


if __name__ == "__main__":
    main()
