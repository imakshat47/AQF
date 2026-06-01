from __future__ import annotations

import csv
import json
from pathlib import Path


def write_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def write_csv(rows: list[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
        return
    keys = []
    for r in rows:
        for k in r.keys():
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v for k, v in r.items()})


def try_write_plots(coverage_rows: list[dict], out_dir: Path):
    try:
        import matplotlib.pyplot as plt
    except Exception:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    # Coverage by method overall.
    overall = [r for r in coverage_rows if r.get("workload") == "ALL" and r.get("difficulty") == "ALL"]
    if overall:
        labels = [r["method"] for r in overall]
        vals = [r["strict_coverage"] for r in overall]
        plt.figure(figsize=(10, 4))
        plt.bar(labels, vals)
        plt.ylabel("Strict coverage")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(out_dir / "coverage_by_method.png")
        plt.close()
