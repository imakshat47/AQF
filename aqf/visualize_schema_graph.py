#!/usr/bin/env python3
"""
visualize_schema_graph.py

Visualize AQF schema graph JSON output and save a paper-friendly PNG.

Use after running aqf_schema_graph.py, for example:
  python visualize_schema_graph.py --graph_json output/reduced_schema_graph.json --output_png output/reduced_schema_graph.png
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

NODE_COLORS = {
    "section": "#4C78A8",
    "substructure": "#F58518",
    "leaf": "#54A24B",
}

EDGE_COLORS = {
    "containment": "#444444",
    "cooccurrence": "#B279A2",
}


def load_graph(graph_json: str | Path) -> Dict[str, Any]:
    with open(graph_json, "r", encoding="utf-8") as f:
        return json.load(f)


def short_label(text: Any, max_len: int = 28) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def node_score(node: Dict[str, Any]) -> float:
    return float(node.get("queriability") or node.get("local_utility") or 0.0)


def filter_graph(
    payload: Dict[str, Any],
    edge_mode: str = "all",
    max_nodes: int = 120,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    nodes = payload.get("nodes", [])
    edges = payload.get("edges", [])

    if max_nodes and len(nodes) > max_nodes:
        nodes = sorted(nodes, key=node_score, reverse=True)[:max_nodes]

    kept = {n["node_id"] for n in nodes}

    if edge_mode != "all":
        edges = [e for e in edges if e.get("edge_type") == edge_mode]

    edges = [e for e in edges if e.get("source") in kept and e.get("target") in kept]
    return nodes, edges


def build_hierarchy_positions(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Dict[str, Tuple[float, float]]:
    node_ids = [n["node_id"] for n in nodes]
    node_set = set(node_ids)

    children = defaultdict(list)
    indegree = defaultdict(int)

    for e in edges:
        if e.get("edge_type") != "containment":
            continue
        source = e.get("source")
        target = e.get("target")
        if source in node_set and target in node_set:
            children[source].append(target)
            indegree[target] += 1
            indegree.setdefault(source, indegree.get(source, 0))

    roots = [nid for nid in node_ids if indegree.get(nid, 0) == 0]
    if not roots and node_ids:
        roots = [node_ids[0]]

    depth = {}
    queue = deque()

    for root in roots:
        depth[root] = 0
        queue.append(root)

    while queue:
        u = queue.popleft()
        for v in children.get(u, []):
            if v not in depth:
                depth[v] = depth[u] + 1
                queue.append(v)

    max_depth = max(depth.values()) if depth else 0
    for nid in node_ids:
        if nid not in depth:
            max_depth += 1
            depth[nid] = max_depth

    levels = defaultdict(list)
    for nid, d in depth.items():
        levels[d].append(nid)

    pos = {}
    for d in sorted(levels):
        level_nodes = sorted(levels[d])
        count = len(level_nodes)
        for i, nid in enumerate(level_nodes):
            x = i - (count - 1) / 2.0
            y = -d
            pos[nid] = (x, y)

    return pos


def draw_graph(
    payload: Dict[str, Any],
    output_png: str | Path,
    edge_mode: str = "all",
    max_nodes: int = 120,
    title: str = "AQF Reduced Weighted Schema Graph",
    dpi: int = 300,
    width: float = 18,
    height: float = 12,
    show_labels: bool = True,
) -> None:
    nodes, edges = filter_graph(payload, edge_mode=edge_mode, max_nodes=max_nodes)

    if not nodes:
        raise ValueError("No nodes available for visualization.")

    pos = build_hierarchy_positions(nodes, edges)

    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_title(title, fontsize=18, pad=20)
    ax.axis("off")

    max_weight = max([float(e.get("weight") or e.get("structural_connectivity") or 0.0) for e in edges], default=1.0)
    max_weight = max(max_weight, 1e-9)

    for e in edges:
        source = e.get("source")
        target = e.get("target")
        if source not in pos or target not in pos:
            continue

        x1, y1 = pos[source]
        x2, y2 = pos[target]
        edge_type = e.get("edge_type", "containment")
        weight = float(e.get("weight") or e.get("structural_connectivity") or 0.0)
        line_width = 0.6 + 2.4 * (weight / max_weight)
        alpha = 0.68 if edge_type == "containment" else 0.32
        linestyle = "-" if edge_type == "containment" else "--"

        ax.plot(
            [x1, x2],
            [y1, y2],
            color=EDGE_COLORS.get(edge_type, "#888888"),
            linewidth=line_width,
            alpha=alpha,
            linestyle=linestyle,
            zorder=1,
        )

    scores = [node_score(n) for n in nodes]
    max_score = max(max(scores), 1e-9) if scores else 1.0

    for n in nodes:
        nid = n["node_id"]
        x, y = pos[nid]
        aqf_type = n.get("aqf_type", "substructure")
        score = node_score(n)
        size = 180 + 1450 * math.sqrt(score / max_score)

        ax.scatter(
            [x],
            [y],
            s=size,
            color=NODE_COLORS.get(aqf_type, "#999999"),
            edgecolors="black",
            linewidths=0.7,
            alpha=0.92,
            zorder=3,
        )

        if show_labels:
            label = short_label(n.get("name", nid), max_len=30)
            q = float(n.get("queriability") or 0.0)
            ax.text(
                x,
                y - 0.16,
                f"{label}\nQ={q:.3f}",
                fontsize=8,
                ha="center",
                va="top",
                zorder=4,
            )

    legend_items = [
        Line2D([0], [0], marker="o", color="w", label="Section", markerfacecolor=NODE_COLORS["section"], markeredgecolor="black", markersize=10),
        Line2D([0], [0], marker="o", color="w", label="Substructure", markerfacecolor=NODE_COLORS["substructure"], markeredgecolor="black", markersize=10),
        Line2D([0], [0], marker="o", color="w", label="Leaf / ELEMENT", markerfacecolor=NODE_COLORS["leaf"], markeredgecolor="black", markersize=10),
        Line2D([0], [0], color=EDGE_COLORS["containment"], lw=2, label="Containment"),
        Line2D([0], [0], color=EDGE_COLORS["cooccurrence"], lw=2, linestyle="--", label="Co-occurrence"),
    ]
    ax.legend(handles=legend_items, loc="upper right", frameon=True, fontsize=10)

    meta = payload.get("metadata", {})
    footer = (
        f"records={meta.get('total_records', 'NA')} | "
        f"nodes shown={len(nodes)} | edges shown={len(edges)} | "
        f"lambda={meta.get('lambda_cc', 'NA')} | mu={meta.get('mu', 'NA')} | theta={meta.get('theta', 'NA')}"
    )
    fig.text(0.5, 0.02, footer, ha="center", fontsize=10)

    output_png = Path(output_png)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=(0.02, 0.04, 0.98, 0.96))
    plt.savefig(output_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize AQF schema graph JSON as PNG.")
    parser.add_argument("--graph_json", required=True, help="Path to schema_graph.json, weighted_schema_graph.json, or reduced_schema_graph.json")
    parser.add_argument("--output_png", required=True, help="Path where PNG should be saved")
    parser.add_argument("--edge_mode", choices=["all", "containment", "cooccurrence"], default="all", help="Which edge types to draw")
    parser.add_argument("--max_nodes", type=int, default=120, help="Maximum nodes to show, ranked by queriability")
    parser.add_argument("--title", default="AQF Reduced Weighted Schema Graph", help="Figure title")
    parser.add_argument("--dpi", type=int, default=300, help="PNG DPI")
    parser.add_argument("--width", type=float, default=18, help="Figure width in inches")
    parser.add_argument("--height", type=float, default=12, help="Figure height in inches")
    parser.add_argument("--hide_labels", action="store_true", help="Hide node labels for dense graphs")

    args = parser.parse_args()

    payload = load_graph(args.graph_json)
    draw_graph(
        payload=payload,
        output_png=args.output_png,
        edge_mode=args.edge_mode,
        max_nodes=args.max_nodes,
        title=args.title,
        dpi=args.dpi,
        width=args.width,
        height=args.height,
        show_labels=not args.hide_labels,
    )

    print(f"Saved PNG visualization: {args.output_png}")


if __name__ == "__main__":
    main()
