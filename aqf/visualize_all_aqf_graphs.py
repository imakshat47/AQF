#!/usr/bin/env python3
"""
visualize_all_aqf_graphs.py

Create paper-friendly organic/radial PNG visualizations for all three AQF graph outputs:
  1. schema_graph.json
  2. weighted_schema_graph.json
  3. reduced_schema_graph.json

This version supports edge-weight labels for ALL edges or only TOP weighted edges.

Recommended:
  python visualize_all_aqf_graphs.py \
    --input_dir output \
    --output_dir output/figures_all_weights \
    --edge_mode all \
    --edge_label_mode all \
    --max_nodes 120
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

NODE_COLORS = {
    "section": "#4C78A8",
    "substructure": "#F58518",
    "leaf": "#54A24B",
    "unknown": "#9D9D9D",
}

EDGE_COLORS = {
    "containment": "#333333",
    "cooccurrence": "#B279A2",
}

GRAPH_CONFIG = {
    "schema_graph": {
        "file": "schema_graph.json",
        "title": "AQF Schema Graph: Full Repository Structure",
        "subtitle": "High structural complexity before queriability weighting",
        "png": "01_schema_graph_organic.png",
        "edge_mode": "containment",
    },
    "weighted_schema_graph": {
        "file": "weighted_schema_graph.json",
        "title": "AQF Weighted Schema Graph: Queriability and Structural Connectivity",
        "subtitle": "Node size encodes queriability; edge width and labels encode structural connectivity",
        "png": "02_weighted_schema_graph_organic.png",
        "edge_mode": "all",
    },
    "reduced_schema_graph": {
        "file": "reduced_schema_graph.json",
        "title": "AQF Reduced Weighted Schema Graph: Candidate Query Region",
        "subtitle": "Low-queriability regions pruned while preserving containment context",
        "png": "03_reduced_schema_graph_organic.png",
        "edge_mode": "all",
    },
}


def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def node_score(node: Dict[str, Any]) -> float:
    return float(node.get("queriability") or node.get("local_utility") or node.get("coverage") or 0.0)


def edge_weight(edge: Dict[str, Any]) -> float:
    return float(edge.get("weight") or edge.get("structural_connectivity") or 0.0)


def edge_label(edge: Dict[str, Any], label_type: str = "w") -> str:
    w = edge_weight(edge)
    cc = float(edge.get("containment_connectivity") or 0.0)
    co = float(edge.get("cooccurrence_connectivity") or 0.0)
    if label_type == "full":
        return f"w={w:.2f}\nCC={cc:.2f}, CO={co:.2f}"
    return f"w={w:.2f}"


def short_label(text: Any, max_len: int = 24) -> str:
    text = "" if text is None else str(text)
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def complexity_stats(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(nodes)
    e = len(edges)
    density = e / max(n * (n - 1), 1)
    return {
        "nodes": n,
        "edges": e,
        "density": density,
        "sections": sum(1 for x in nodes if x.get("aqf_type") == "section"),
        "substructures": sum(1 for x in nodes if x.get("aqf_type") == "substructure"),
        "leaf_nodes": sum(1 for x in nodes if x.get("aqf_type") == "leaf"),
        "containment_edges": sum(1 for x in edges if x.get("edge_type") == "containment"),
        "cooccurrence_edges": sum(1 for x in edges if x.get("edge_type") == "cooccurrence"),
    }


def filter_edges(edges: List[Dict[str, Any]], edge_mode: str) -> List[Dict[str, Any]]:
    if edge_mode == "all":
        return edges
    return [e for e in edges if e.get("edge_type") == edge_mode]


def select_nodes(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], max_nodes: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not max_nodes or len(nodes) <= max_nodes:
        kept = {n["node_id"] for n in nodes}
        return nodes, [e for e in edges if e.get("source") in kept and e.get("target") in kept]

    section_nodes = [n for n in nodes if n.get("aqf_type") == "section"]
    section_ids = {n["node_id"] for n in section_nodes}
    remaining = sorted([n for n in nodes if n["node_id"] not in section_ids], key=node_score, reverse=True)
    selected = section_nodes + remaining[: max(0, max_nodes - len(section_nodes))]
    kept = {n["node_id"] for n in selected}
    return selected, [e for e in edges if e.get("source") in kept and e.get("target") in kept]


def build_graph_maps(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
    node_ids = {n["node_id"] for n in nodes}
    children = defaultdict(list)
    parent = {}
    for e in edges:
        s, t = e.get("source"), e.get("target")
        if s in node_ids and t in node_ids and e.get("edge_type") == "containment":
            children[s].append(t)
            parent[t] = s
    return children, parent


def organic_radial_layout(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]], seed: int = 42, iterations: int = 180) -> Dict[str, Tuple[float, float]]:
    random.seed(seed)
    node_ids = [n["node_id"] for n in nodes]
    children, parent = build_graph_maps(nodes, edges)
    roots = [n["node_id"] for n in nodes if n.get("aqf_type") == "section" or n["node_id"] not in parent]
    if not roots and node_ids:
        roots = [node_ids[0]]

    depth = {}
    q = deque()
    for r in roots:
        depth[r] = 0
        q.append(r)
    while q:
        u = q.popleft()
        for v in children.get(u, []):
            if v not in depth:
                depth[v] = depth[u] + 1
                q.append(v)
    for nid in node_ids:
        depth.setdefault(nid, 2)

    levels = defaultdict(list)
    for nid, d in depth.items():
        levels[d].append(nid)

    pos = {}
    root_count = max(len(roots), 1)
    for i, r in enumerate(roots):
        angle = 2 * math.pi * i / root_count
        radius = 0.22 if root_count > 1 else 0.0
        pos[r] = (radius * math.cos(angle), radius * math.sin(angle))

    for d in sorted(levels):
        if d == 0:
            continue
        level_nodes = sorted(levels[d])
        count = len(level_nodes)
        radius = 1.35 * d
        for i, nid in enumerate(level_nodes):
            angle = 2 * math.pi * i / max(count, 1)
            jitter = random.uniform(-0.14, 0.14)
            rr = radius + random.uniform(-0.18, 0.18)
            pos[nid] = (rr * math.cos(angle + jitter), rr * math.sin(angle + jitter))

    area = max(len(node_ids), 1)
    k = math.sqrt(area) * 0.28
    for _ in range(iterations):
        disp = {nid: [0.0, 0.0] for nid in node_ids}
        for i, u in enumerate(node_ids):
            x1, y1 = pos[u]
            for v in node_ids[i + 1:]:
                x2, y2 = pos[v]
                dx, dy = x1 - x2, y1 - y2
                dist = math.sqrt(dx * dx + dy * dy) + 1e-6
                force = (k * k) / dist
                fx, fy = (dx / dist) * force, (dy / dist) * force
                disp[u][0] += fx; disp[u][1] += fy
                disp[v][0] -= fx; disp[v][1] -= fy
        for e in edges:
            u, v = e.get("source"), e.get("target")
            if u not in pos or v not in pos:
                continue
            x1, y1 = pos[u]; x2, y2 = pos[v]
            dx, dy = x1 - x2, y1 - y2
            dist = math.sqrt(dx * dx + dy * dy) + 1e-6
            base = 0.035 if e.get("edge_type") == "containment" else 0.010
            force = base * max(edge_weight(e), 0.1) * dist * dist / max(k, 1e-6)
            fx, fy = (dx / dist) * force, (dy / dist) * force
            disp[u][0] -= fx; disp[u][1] -= fy
            disp[v][0] += fx; disp[v][1] += fy
        temp = 0.035
        for nid in node_ids:
            x, y = pos[nid]
            d = depth.get(nid, 1)
            desired_r = 0.2 if d == 0 else 1.35 * d
            r = math.sqrt(x * x + y * y) + 1e-6
            radial_force = 0.025 * (desired_r - r)
            disp[nid][0] += (x / r) * radial_force
            disp[nid][1] += (y / r) * radial_force
            if nid in roots:
                disp[nid][0] += -0.08 * x
                disp[nid][1] += -0.08 * y
            dx, dy = disp[nid]
            mag = math.sqrt(dx * dx + dy * dy)
            if mag > 0:
                scale = min(temp, mag) / mag
                pos[nid] = (x + dx * scale, y + dy * scale)
    return pos


def edge_label_key_set(edges: List[Dict[str, Any]], edge_label_mode: str, top_edge_labels: int) -> set:
    if edge_label_mode == "none":
        return set()
    if edge_label_mode == "all":
        return {(e.get("source"), e.get("target"), e.get("edge_type")) for e in edges}
    candidates = sorted(edges, key=edge_weight, reverse=True)[:top_edge_labels]
    return {(e.get("source"), e.get("target"), e.get("edge_type")) for e in candidates}


def draw_organic_graph(
    payload: Dict[str, Any],
    output_png: Path,
    title: str,
    subtitle: str,
    edge_mode: str,
    max_nodes: int,
    dpi: int,
    width: float,
    height: float,
    hide_labels: bool,
    seed: int,
    edge_label_mode: str,
    edge_label_type: str,
    top_edge_labels: int,
    min_node_size: float,
    max_node_size: float,
    node_font_size: float,
    edge_font_size: float,
    title_font_size: float,
    subtitle_font_size: float,
    legend_font_size: float,
) -> None:
    all_nodes = payload.get("nodes", [])
    all_edges = payload.get("edges", [])
    raw_stats = complexity_stats(all_nodes, all_edges)
    edges = filter_edges(all_edges, edge_mode=edge_mode)
    nodes, edges = select_nodes(all_nodes, edges, max_nodes=max_nodes)
    shown_stats = complexity_stats(nodes, edges)
    pos = organic_radial_layout(nodes, edges, seed=seed)

    fig, ax = plt.subplots(figsize=(width, height))
    ax.set_title(title, fontsize=title_font_size, fontweight="bold", pad=22)
    ax.text(0.5, 0.965, subtitle, transform=fig.transFigure, ha="center", fontsize=subtitle_font_size)
    ax.axis("off")

    max_w = max([edge_weight(e) for e in edges], default=1.0)
    max_w = max(max_w, 1e-9)
    max_s = max([node_score(n) for n in nodes], default=1.0)
    max_s = max(max_s, 1e-9)

    sorted_edges = sorted(edges, key=lambda e: 0 if e.get("edge_type") == "cooccurrence" else 1)
    label_keys = edge_label_key_set(sorted_edges, edge_label_mode=edge_label_mode, top_edge_labels=top_edge_labels)

    for e in sorted_edges:
        s, t = e.get("source"), e.get("target")
        if s not in pos or t not in pos:
            continue
        x1, y1 = pos[s]; x2, y2 = pos[t]
        et = e.get("edge_type", "containment")
        w = edge_weight(e)
        lw = 0.85 + 5.20 * (w / max_w)
        alpha = 0.68 if et == "containment" else 0.22
        linestyle = "-" if et == "containment" else "--"
        ax.plot([x1, x2], [y1, y2], color=EDGE_COLORS.get(et, "#888888"), lw=lw, alpha=alpha, linestyle=linestyle, zorder=1)
        if (s, t, et) in label_keys:
            mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            ax.text(mx, my, edge_label(e, edge_label_type), fontsize=edge_font_size, color="#222222", ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.16", fc="white", ec="none", alpha=0.74), zorder=2)

    for n in nodes:
        nid = n["node_id"]
        x, y = pos[nid]
        aqf_type = n.get("aqf_type", "unknown")
        score = node_score(n)
        size = min_node_size + (max_node_size - min_node_size) * math.sqrt(score / max_s) if max_s > 0 else min_node_size
        if aqf_type == "section":
            size *= 1.28
        elif aqf_type == "leaf":
            size *= 0.92
        ax.scatter([x], [y], s=size, color=NODE_COLORS.get(aqf_type, NODE_COLORS["unknown"]), edgecolors="black", linewidths=0.85, alpha=0.94, zorder=3)
        if not hide_labels:
            label = short_label(n.get("name", nid), max_len=23)
            q = float(n.get("queriability") or 0.0)
            if q > 0:
                label = f"{label}\nQ={q:.3f}"
            ax.text(x, y - 0.24, label, fontsize=node_font_size, ha="center", va="top", zorder=4,
                    bbox=dict(boxstyle="round,pad=0.14", fc="white", ec="none", alpha=0.62))

    legend_items = [
        Line2D([0], [0], marker="o", color="w", label="Composition / Section", markerfacecolor=NODE_COLORS["section"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], marker="o", color="w", label="Entry / Cluster / Item structure", markerfacecolor=NODE_COLORS["substructure"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], marker="o", color="w", label="Element / Leaf", markerfacecolor=NODE_COLORS["leaf"], markeredgecolor="black", markersize=12),
        Line2D([0], [0], color=EDGE_COLORS["containment"], lw=3, label="Containment edge"),
        Line2D([0], [0], color=EDGE_COLORS["cooccurrence"], lw=3, linestyle="--", label="Co-occurrence edge"),
    ]
    ax.legend(handles=legend_items, loc="upper right", frameon=True, fontsize=legend_font_size)

    meta = payload.get("metadata", {})
    stats_line = (
        f"Full graph: |V|={raw_stats['nodes']}, |E|={raw_stats['edges']}, "
        f"containment={raw_stats['containment_edges']}, co-occurrence={raw_stats['cooccurrence_edges']} | "
        f"Shown: |V|={shown_stats['nodes']}, |E|={shown_stats['edges']}"
    )
    param_line = (
        f"records={meta.get('total_records', 'NA')} | lambda={meta.get('lambda_cc', 'NA')} | "
        f"mu={meta.get('mu', 'NA')} | theta={meta.get('theta', 'NA')} | edge mode={edge_mode} | edge labels={edge_label_mode}"
    )
    fig.text(0.5, 0.035, stats_line, ha="center", fontsize=max(11, legend_font_size - 1))
    fig.text(0.5, 0.017, param_line, ha="center", fontsize=max(11, legend_font_size - 1))

    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(rect=(0.02, 0.06, 0.98, 0.94))
    plt.savefig(output_png, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def create_complexity_summary(input_dir: Path, output_dir: Path) -> None:
    out = output_dir / "graph_complexity_summary.csv"
    with open(out, "w", encoding="utf-8") as f:
        f.write("graph,file,total_records,nodes,edges,sections,substructures,leaf_nodes,containment_edges,cooccurrence_edges,density,lambda,mu,theta\n")
        for key, cfg in GRAPH_CONFIG.items():
            path = input_dir / cfg["file"]
            if not path.exists():
                continue
            payload = load_json(path)
            stats = complexity_stats(payload.get("nodes", []), payload.get("edges", []))
            meta = payload.get("metadata", {})
            f.write(f"{key},{cfg['file']},{meta.get('total_records','')},{stats['nodes']},{stats['edges']},{stats['sections']},{stats['substructures']},{stats['leaf_nodes']},{stats['containment_edges']},{stats['cooccurrence_edges']},{stats['density']:.8f},{meta.get('lambda_cc','')},{meta.get('mu','')},{meta.get('theta','')}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create organic PNGs for AQF schema, weighted, and reduced graphs with edge-weight labels.")
    parser.add_argument("--input_dir", required=True, help="Folder containing schema_graph.json, weighted_schema_graph.json, reduced_schema_graph.json")
    parser.add_argument("--output_dir", required=True, help="Folder where PNG figures will be saved")
    parser.add_argument("--max_nodes", type=int, default=180, help="Maximum nodes shown per graph")
    parser.add_argument("--edge_mode", choices=["auto", "all", "containment", "cooccurrence"], default="auto", help="Global edge mode; auto uses per-graph defaults")
    parser.add_argument("--edge_label_mode", choices=["none", "top", "all"], default="top", help="Which edge weights to label")
    parser.add_argument("--edge_label_type", choices=["w", "full"], default="w", help="w = only final weight; full = weight plus CC and CO")
    parser.add_argument("--top_edge_labels", type=int, default=45, help="Number of edge labels if edge_label_mode=top")
    parser.add_argument("--dpi", type=int, default=300, help="PNG resolution")
    parser.add_argument("--width", type=float, default=22, help="Figure width in inches")
    parser.add_argument("--height", type=float, default=16, help="Figure height in inches")
    parser.add_argument("--hide_labels", action="store_true", help="Hide node labels for dense graphs")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic organic layout")
    parser.add_argument("--min_node_size", type=float, default=650, help="Minimum node size")
    parser.add_argument("--max_node_size", type=float, default=5200, help="Maximum node size")
    parser.add_argument("--node_font_size", type=float, default=16, help="Node label font size")
    parser.add_argument("--edge_font_size", type=float, default=12, help="Edge weight label font size")
    parser.add_argument("--title_font_size", type=float, default=22, help="Title font size")
    parser.add_argument("--subtitle_font_size", type=float, default=16, help="Subtitle font size")
    parser.add_argument("--legend_font_size", type=float, default=14, help="Legend and footer font size")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created = []
    for key, cfg in GRAPH_CONFIG.items():
        graph_path = input_dir / cfg["file"]
        if not graph_path.exists():
            print(f"[WARN] Missing {graph_path}; skipping {key}")
            continue
        payload = load_json(graph_path)
        edge_mode = cfg["edge_mode"] if args.edge_mode == "auto" else args.edge_mode
        out_png = output_dir / cfg["png"]
        draw_organic_graph(
            payload=payload,
            output_png=out_png,
            title=cfg["title"],
            subtitle=cfg["subtitle"],
            edge_mode=edge_mode,
            max_nodes=args.max_nodes,
            dpi=args.dpi,
            width=args.width,
            height=args.height,
            hide_labels=args.hide_labels,
            seed=args.seed,
            edge_label_mode=args.edge_label_mode,
            edge_label_type=args.edge_label_type,
            top_edge_labels=args.top_edge_labels,
            min_node_size=args.min_node_size,
            max_node_size=args.max_node_size,
            node_font_size=args.node_font_size,
            edge_font_size=args.edge_font_size,
            title_font_size=args.title_font_size,
            subtitle_font_size=args.subtitle_font_size,
            legend_font_size=args.legend_font_size,
        )
        created.append(out_png)
        print(f"Saved: {out_png}")

    create_complexity_summary(input_dir, output_dir)
    print(f"Saved complexity summary: {output_dir / 'graph_complexity_summary.csv'}")
    if created:
        print("Generated figures:")
        for p in created:
            print(f" - {p}")


if __name__ == "__main__":
    main()
