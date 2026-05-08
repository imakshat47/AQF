# record_family_index.py
from __future__ import annotations

from pathlib import Path
from collections import defaultdict

from record_unit_loader import group_record_units_by_family


def extract_record_units(folder: Path, allowed_json_types: list[str] | None = None):
    return group_record_units_by_family(folder, allowed_json_types=allowed_json_types)


def summarize_record_families(record_groups: dict) -> list[dict]:
    rows = []
    for family, units in record_groups.items():
        ehr_ids = {u.get("ehr_id") for u in units if u.get("ehr_id")}
        subject_ids = {u.get("subject_id") for u in units if u.get("subject_id")}
        unresolved_refs = sum(len(u.get("unresolved_composition_refs", [])) for u in units)
        rows.append({
            "record_family": family,
            "composition_units": len(units),
            "ehr_count": len(ehr_ids),
            "subject_count": len(subject_ids),
            "unresolved_refs": unresolved_refs,
        })
    rows.sort(key=lambda x: x["composition_units"], reverse=True)
    return rows


def summarize_json_types(scan_result: dict) -> list[dict]:
    grouped = defaultdict(list)
    for item in scan_result.get("detected", []):
        grouped[item.get("json_type", "unknown")].append(item)
    rows = []
    for json_type, items in grouped.items():
        rows.append({
            "json_type": json_type,
            "files": len(items),
            "avg_confidence": round(sum(i.get("confidence", 0.0) for i in items) / max(1, len(items)), 4),
            "sample_file": items[0].get("file"),
        })
    rows.sort(key=lambda x: x["files"], reverse=True)
    return rows
