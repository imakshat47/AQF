#!/usr/bin/env python3
"""
visualize_operator_aware_canonical.py

Visualize operator-aware canonical forms after operator_aware_field_selector.py.

Input:
  output/operator_aware/operator_aware_forms.json

Output:
  PNG images for top-k operator-aware canonical forms.

Visual encoding:
  blue    = input-only field
  green   = output-only field
  purple  = input+output field
  gray    = relationship-only/intermediate node if present
  edge width = relationship priority / structural connectivity
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROLE_COLORS = {
    "input_only": "#4C78A8",
    "output_only": "#54A24B",
    "input_output": "#B279A2",
    "relationship": "#9D9D9D",
    "root": "#F58518",
}


def load_json(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def short_label(text: Any, max_len: int = 26) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def collect_form_nodes(form: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    nodes: Dict[str, Dict[str, Any]] = {}

    root_id = form.get("root_canonical_id")
    nodes[root_id] = {
        "canonical_id": root_id,
        "name": form.get("form_group", "Form Group"),
        "role": "root",
        "score": form.get("operator_form_utility", 0.0),
    }

    input_ids = set()
    output_ids = set()

    for item in form.get("operator_input_tree", []):
        cid = item.get("canonical_id")
        input_ids.add(cid)
        nodes[cid] = {
            "canonical_id": cid,
            "name": item.get("name"),
            "role": "input_only",
            "score": float(item.get("best_input_score") or 0.0),
            "operator": item.get("best_input_operator"),
            "datatype": item.get("datatype"),
        }

    for item in form.get("operator_output_tree", []):
        cid = item.get("canonical_id")
        output_ids.add(cid)
        if cid in nodes:
            nodes[cid]["role"] = "input_output"
            nodes[cid]["output_operator"] = item.get("best_output_operator")
            nodes[cid]["score"] = max(float(nodes[cid].get("score") or 0.0), float(item.get("best_output_score") or 0.0))
        else:
            nodes[cid] = {
                "canonical_id": cid,
                "name": item.get("name"),
                "role": "output_only",
                "score": float(item.get("best_output_score") or 0.0),
                "operator": item.get("best_output_operator"),
                "datatype": item.get("datatype"),
            }

    # Include relationship endpoints even if they were not selected as IT/OT fields.
    for rel in form.get("operator_relationship_tree", []):
        for key in ("source", "target"):
            cid = rel.get(key)
            if cid and cid not in nodes:
                nodes[cid] = {
                    "canonical_id": cid,
                    "name": short_label(cid, 18),
                    "role": "relationship",
                    "score": float(rel.get("relationship_priority") or rel.get("weight") or 0.0),
                }

    return nodes


def circular_operator_layout(nodes: Dict[str, Dict[str, Any]], root_id: str) -> Dict[str, Tuple[float, float]]:
    pos = {}
    if root_id in nodes:
        pos[root_id] = (0.0, 0.0)

    groups = {
        "input_only": [],
        "input_output": [],
        "output_only": [],
        "relationship": [],
    }
    for cid, node in nodes.items():
        if cid == root_id:
            continue
        groups.setdefault(node.get("role", "relationship"), []).append(cid)

    angle_offsets = {
        "input_only": math.pi * 0.90,
        "input_output": math.pi * 1.50,
        "output_only": math.pi * 0.10,
        "relationship": math.pi * 1.95,
    }
    radius_map = {
        "input_only": 2.0,
        "input_output": 2.6,
        "output_only": 2.0,
        "relationship": 3.2,
    }

    for role, ids in groups.items():
        ids = sorted(ids)
        count = max(len(ids), 1)
        spread = math.pi * 0.70 if role != "relationship" else math.pi * 1.75
        start = angle_offsets.get(role, 0.0) - spread / 2
        for i, cid in enumerate(ids):
            angle = start + spread * (i / max(count - 1, 1))
            radius = radius_map.get(role, 2.5)
            pos[cid] = (radius * math.cos(angle), radius * math.sin(angle))

    return pos


def draw_form(form: Dict[str, Any], output_png: Path, dpi: int = 300, width: float = 16, height: float = 12) -> None:
    nodes = collect_form_nodes(form)
    root_id = form.get("root_canonical_id")
    pos = circular_operator_layout(nodes, root_id)

    fig, ax = plt.subplots(figsize=(width, height))
    title = f"Operator-Aware Canonical Form: {form.get('form_group', '')}"
    ax.set_title(title, fontsize=20, fontweight="bold", pad=18)
    ax.axis("off")

    # Draw relationship edges.
    rels = form.get("operator_relationship_tree", [])
    max_priority = max([float(r.get("relationship_priority") or r.get("weight") or 0.0) for r in rels], default=1.0)
    max_priority = max(max_priority, 1e-9)
    for rel in rels:
        s, t = rel.get("source"), rel.get("target")
        if s not in pos or t not in pos:
            continue
        x1, y1 = pos[s]
        x2, y2 = pos[t]
        priority = float(rel.get("relationship_priority") or rel.get("weight") or 0.0)
        lw = 0.5 + 3.0 * (priority / max_priority)
        color = "#333333" if rel.get("source_schema_edge_type") == "containment" else "#B279A2"
        style = "-" if rel.get("source_schema_edge_type") == "containment" else "--"
        alpha = 0.55 if rel.get("source_schema_edge_type") == "containment" else 0.18
        ax.plot([x1, x2], [y1, y2], color=color, linestyle=style, linewidth=lw, alpha=alpha, zorder=1)

    max_score = max([float(n.get("score") or 0.0) for n in nodes.values()], default=1.0)
    max_score = max(max_score, 1e-9)

    for cid, node in nodes.items():
        x, y = pos.get(cid, (0.0, 0.0))
        role = node.get("role", "relationship")
        size = 650 + 3200 * math.sqrt(float(node.get("score") or 0.0) / max_score)
        if role == "root":
            size *= 1.35
        ax.scatter([x], [y], s=size, color=ROLE_COLORS.get(role, "#9D9D9D"), edgecolors="black", linewidths=0.9, alpha=0.94, zorder=3)

        label = short_label(node.get("name", cid), 25)
        operator = node.get("operator") or node.get("output_operator")
        if operator:
            label = f"{label}\n{operator}"
        ax.text(x, y - 0.20, label, ha="center", va="top", fontsize=13, bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.65), zorder=4)

    legend_items = [
        Line2D([0], [0], marker="o", color="w", label="Form group", markerfacecolor=ROLE_COLORS["root"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], marker="o", color="w", label="Input field", markerfacecolor=ROLE_COLORS["input_only"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], marker="o", color="w", label="Output field", markerfacecolor=ROLE_COLORS["output_only"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], marker="o", color="w", label="Input + Output field", markerfacecolor=ROLE_COLORS["input_output"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], color="#333333", lw=2, label="Containment relation"),
        Line2D([0], [0], color="#B279A2", lw=2, linestyle="--", label="Co-occurrence relation"),
    ]
    ax.legend(handles=legend_items, loc="upper right", fontsize=12, frameon=True)

    footer = (
        f"IT={form.get('input_field_count', 0)} | OT={form.get('output_field_count', 0)} | "
        f"RT={form.get('relationship_count', 0)} | Utility={float(form.get('operator_form_utility') or 0.0):.3f}"
    )
    fig.text(0.5, 0.025, footer, ha="center", fontsize=12)

    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=(0.02, 0.05, 0.98, 0.94))
    plt.savefig(output_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize operator-aware AQF canonical forms.")
    parser.add_argument("--operator_aware_forms_json", required=True, help="Path to operator_aware_forms.json")
    parser.add_argument("--output_dir", required=True, help="Output directory for PNG files")
    parser.add_argument("--top_k_forms", type=int, default=5, help="Number of top forms to visualize")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--width", type=float, default=16)
    parser.add_argument("--height", type=float, default=12)
    args = parser.parse_args()

    payload = load_json(args.operator_aware_forms_json)
    forms = payload.get("operator_aware_forms", [])
    forms = sorted(forms, key=lambda f: float(f.get("operator_form_utility") or 0.0), reverse=True)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, form in enumerate(forms[: args.top_k_forms], start=1):
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in str(form.get("form_group", "form"))).strip("_")
        out = output_dir / f"operator_aware_canonical_form_{i:02d}_{safe_name}.png"
        draw_form(form, out, dpi=args.dpi, width=args.width, height=args.height)
        print(f"Saved: {out}")


if __name__ == "__main__":
    main()
