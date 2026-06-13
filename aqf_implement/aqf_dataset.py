import json
from pathlib import Path
from collections import defaultdict


def load_dataset(folder):

    records = []

    for p in Path(folder).glob("*.json"):
        try:
            records.append(json.load(open(p)))
        except:
            continue

    return records


def extract_field_stats(records):

    stats = defaultdict(lambda: {
        "count": 0,
        "values": [],
        "label": None
    })

    total_records = len(records)

    for rec in records:

        for f in rec.get("fields", []):

            fid = str(f.get("field_id"))

            stats[fid]["count"] += 1
            stats[fid]["values"].append(f.get("value"))
            stats[fid]["label"] = f.get("label")

    # finalize
    fields = []

    for fid, s in stats.items():

        coverage = s["count"] / total_records

        unique_vals = len(set(str(v) for v in s["values"] if v is not None))
        total_vals = len(s["values"]) or 1

        diversity = unique_vals / total_vals

        fields.append({
            "field_id": fid,
            "label": s["label"],
            "coverage": coverage,
            "distinct_ratio": diversity
        })

    return fields