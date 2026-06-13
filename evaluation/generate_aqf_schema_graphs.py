#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, math, re, sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OPERATOR_WEIGHTS = {
    'is_known': 0.50, 'is_unknown': 0.50,
    'equals': 1.00, 'not_equals': 1.00,
    'contains': 1.25, 'in': 1.25,
    '>': 1.25, '<': 1.25,
    'before': 1.25, 'after': 1.25,
    'between': 1.50,
    'count': 2.00, 'sum': 2.00, 'avg': 2.00, 'min': 2.00, 'max': 2.00,
    'join': 3.00,
}


def load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as f:
        return json.load(f)


def write_json(obj: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        json.dump(obj, f, indent=2, ensure_ascii=False, sort_keys=True)


def safe_float(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        v = float(x)
        return default if math.isnan(v) else v
    except Exception:
        return default


def sanitize_id(text: Any) -> str:
    s = str(text or '').strip()
    s = re.sub(r'[^A-Za-z0-9_.:/-]+', '_', s)
    return s[:240]


def short_label(label: Any, limit: int = 42) -> str:
    text = str(label or '').strip()
    return text if len(text) <= limit else text[:limit-1] + '…'


def field_depth(field: Dict[str, Any]) -> int:
    path = str(field.get('canonical_path') or '')
    parts = [p for p in path.split('/') if p.strip()]
    return len(parts) if parts else 1


def infer_effective_diversity(field: Dict[str, Any]) -> float:
    known = safe_float(field.get('known_count')) or safe_float(field.get('occurrence_count'))
    distinct = safe_float(field.get('distinct_count'))
    if known > 0 and distinct > 0:
        raw = max(0.0, min(1.0, distinct / known))
    else:
        raw = safe_float(field.get('distinct_ratio'), 0.0)
    dv = ' '.join(map(str, field.get('observed_dv_types') or [])) + ' ' + str(field.get('dv_type') or field.get('primary_dv_type') or '')
    kind = str(field.get('kind') or '').lower()
    if 'DV_BOOLEAN' in dv or kind == 'boolean': return max(raw, 0.30)
    if 'DV_CODED_TEXT' in dv or kind == 'coded': return max(raw, 0.30)
    if 'DV_TEXT' in dv or kind == 'text': return min(max(raw, 0.50), 0.80)
    if 'DV_DATE' in dv or 'DV_DATE_TIME' in dv or kind == 'temporal': return max(raw, 0.25)
    if any(t in dv for t in ['DV_COUNT','DV_QUANTITY','DV_PROPORTION']) or kind == 'numeric': return max(raw, 0.30)
    return raw if raw > 0 else 0.30


def operator_list(field: Dict[str, Any]) -> List[str]:
    ops = field.get('operators')
    if isinstance(ops, list): return [str(o) for o in ops]
    dv_types = set(field.get('observed_dv_types') or [])
    for key in ['dv_type', 'primary_dv_type']:
        if field.get(key): dv_types.add(field[key])
    out = {'is_known', 'is_unknown'}
    if 'DV_CODED_TEXT' in dv_types: out |= {'equals','not_equals','in','contains'}
    elif 'DV_TEXT' in dv_types: out |= {'equals','contains'}
    elif 'DV_BOOLEAN' in dv_types: out |= {'equals'}
    elif 'DV_DATE' in dv_types or 'DV_DATE_TIME' in dv_types: out |= {'equals','before','after','between'}
    elif 'DV_COUNT' in dv_types or 'DV_QUANTITY' in dv_types or 'DV_PROPORTION' in dv_types: out |= {'equals','>','<','between'}
    else: out |= {'equals'}
    return sorted(out)


def field_weight(field: Dict[str, Any], mu: float = 0.25) -> Dict[str, float]:
    coverage = max(0.0, min(1.0, safe_float(field.get('coverage'))))
    diversity = infer_effective_diversity(field)
    local_utility = coverage * diversity
    depth = field_depth(field)
    specificity = min(1.0, depth / 8.0)
    aqf_weight = local_utility + mu * specificity
    ops = operator_list(field)
    return {
        'coverage': coverage,
        'effective_diversity': diversity,
        'local_utility': local_utility,
        'specificity': specificity,
        'aqf_visual_weight': aqf_weight,
        'base_queriability': aqf_weight,
        'operator_count': float(len(ops)),
        'weighted_operator_burden': float(sum(OPERATOR_WEIGHTS.get(op, 1.0) for op in ops)),
        'depth': float(depth),
    }


def iter_fields_from_forest(forest: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for family, tree in (forest.get('trees') or {}).items():
        for f in tree.get('fields', []) or []:
            x = dict(f)
            x.setdefault('record_family', family)
            yield x


def build_canonical_forest_from_data(data_dir: Path) -> Dict[str, Any]:
    from aqf_eval.openehr_utils import scan_json_folder
    from aqf_eval.canonical import build_canonical_forest
    return build_canonical_forest(scan_json_folder(data_dir))


def primary_tree_edges(G: nx.DiGraph) -> List[Tuple[str, str]]:
    return [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') != 'sibling_context']


def add_sibling_context_edges(G: nx.DiGraph) -> None:
    by_subgroup = defaultdict(list)
    for n, d in G.nodes(data=True):
        if d.get('node_type') == 'field':
            by_subgroup[(d.get('record_family'), d.get('form_group'), d.get('nested_subgroup'))].append(n)
    for nodes in by_subgroup.values():
        nodes = sorted(nodes, key=lambda n: G.nodes[n].get('aqf_visual_weight', 0), reverse=True)
        for a, b in zip(nodes, nodes[1:]):
            wa = safe_float(G.nodes[a].get('aqf_visual_weight'))
            wb = safe_float(G.nodes[b].get('aqf_visual_weight'))
            w = max(1e-9, (wa + wb) / 2.0)
            G.add_edge(a, b, edge_type='sibling_context', weight=w, relation_strength=0.5)
            G.add_edge(b, a, edge_type='sibling_context', weight=w, relation_strength=0.5)


def build_schema_graph(forest: Dict[str, Any], mu: float = 0.25) -> nx.DiGraph:
    G = nx.DiGraph(name='AQF Schema Graph')
    root_id = 'schema:root'
    G.add_node(root_id, node_type='root', label='EHR Schema', layer=0, base_queriability=0.0)
    for f in iter_fields_from_forest(forest):
        family = f.get('record_family') or 'composition'
        group = f.get('form_group') or 'Composition'
        subgroup = f.get('nested_subgroup') or 'Top-level fields'
        fid = str(f.get('field_id') or f.get('canonical_path') or f.get('label'))
        family_id = f'family:{sanitize_id(family)}'
        group_id = f'group:{sanitize_id(family)}::{sanitize_id(group)}'
        subgroup_id = f'subgroup:{sanitize_id(family)}::{sanitize_id(group)}::{sanitize_id(subgroup)}'
        leaf_id = f'field:{sanitize_id(fid)}'
        G.add_node(family_id, node_type='composition_family', label=str(family), layer=1, base_queriability=0.0)
        G.add_node(group_id, node_type='canonical_group', label=str(group), layer=2, base_queriability=0.0)
        G.add_node(subgroup_id, node_type='canonical_subgroup', label=str(subgroup), layer=3, base_queriability=0.0)
        weights = field_weight(f, mu=mu)
        G.add_node(
            leaf_id, node_type='field', label=str(f.get('label') or fid), field_id=fid,
            canonical_path=str(f.get('canonical_path') or ''), record_family=str(family),
            form_group=str(group), nested_subgroup=str(subgroup), kind=str(f.get('kind') or ''),
            dv_type=str(f.get('dv_type') or f.get('primary_dv_type') or ''), operators=';'.join(operator_list(f)),
            layer=4, **weights
        )
        for u, v, etype in [
            (root_id, family_id, 'root_to_family'),
            (family_id, group_id, 'family_to_group'),
            (group_id, subgroup_id, 'group_to_subgroup'),
            (subgroup_id, leaf_id, 'subgroup_to_field')]:
            if not G.has_edge(u, v):
                G.add_edge(u, v, edge_type=etype, weight=1.0, relation_strength=1.0)
            else:
                G[u][v]['relation_strength'] = safe_float(G[u][v].get('relation_strength')) + 1.0
    add_sibling_context_edges(G)
    compute_upward_schema_queriability(G)
    compute_pairwise_cartesian_queriability(G)
    assign_relative_queriability_edges(G, key='cartesian_queriability')
    return G


def compute_upward_schema_queriability(G: nx.DiGraph) -> None:
    children = defaultdict(list)
    for u, v in primary_tree_edges(G): children[u].append(v)
    def aggregate(n: str) -> float:
        if not children.get(n):
            q = safe_float(G.nodes[n].get('base_queriability'), safe_float(G.nodes[n].get('aqf_visual_weight'), 0.0))
            G.nodes[n]['upward_queriability'] = q
            return q
        q = sum(aggregate(c) for c in children[n])
        G.nodes[n]['upward_queriability'] = q
        return q
    root = 'schema:root' if 'schema:root' in G.nodes else list(G.nodes)[0]
    total = aggregate(root)
    for n in G.nodes:
        q = safe_float(G.nodes[n].get('upward_queriability'))
        G.nodes[n]['normalized_upward_queriability'] = q / total if total > 0 else 0.0


def _build_distance_graph(G: nx.DiGraph) -> nx.Graph:
    """Create undirected graph for all-pairs cartesian influence.

    Distances are inverse edge strengths. Containment and sibling-context links both
    participate, so every node can adjust every other node through shortest paths.
    """
    H = nx.Graph()
    for n in G.nodes: H.add_node(n)
    for u, v, d in G.edges(data=True):
        strength = safe_float(d.get('weight'), safe_float(d.get('relation_strength'), 1.0))
        if d.get('edge_type') == 'sibling_context':
            strength = max(strength, 0.25)
        distance = 1.0 / max(strength, 1e-6)
        if H.has_edge(u, v):
            H[u][v]['distance'] = min(H[u][v]['distance'], distance)
            H[u][v]['strength'] = max(H[u][v].get('strength', 0.0), strength)
        else:
            H.add_edge(u, v, distance=distance, strength=strength)
    return H


def compute_pairwise_cartesian_queriability(G: nx.DiGraph, decay: float = 0.62, include_schema_prior: float = 0.02, save_pairs_path: Path | None = None) -> pd.DataFrame:
    """Full cartesian-product queriability across all graph nodes.

    For every target node v and every source node u, compute an influence term:

        influence(u -> v) = base_Q(u) * exp(-decay * dist(u,v)) * type_affinity(u,v)

    where dist(u,v) is the shortest-path distance in a weighted undirected schema
    graph. This means every node is adjusted against every other node. The root
    node `EHR Schema` is anchored to exactly 1.0. Every other node is normalized
    below 1.0.
    """
    H = _build_distance_graph(G)
    nodes = list(G.nodes)
    root = 'schema:root' if 'schema:root' in G.nodes else nodes[0]

    base = {}
    for n, d in G.nodes(data=True):
        b = safe_float(d.get('base_queriability'), safe_float(d.get('aqf_visual_weight'), 0.0))
        if d.get('node_type') != 'field':
            b += include_schema_prior
        base[n] = max(0.0, b)

    lengths = dict(nx.all_pairs_dijkstra_path_length(H, weight='distance'))
    raw = {n: 0.0 for n in nodes}
    pair_rows = []

    def affinity(src: str, tgt: str) -> float:
        st = G.nodes[src].get('node_type')
        tt = G.nodes[tgt].get('node_type')
        if src == tgt: return 1.0
        if st == tt: return 0.95
        # field-to-ancestor and ancestor-to-field should remain strong
        if st == 'field' or tt == 'field': return 0.85
        return 0.80

    for tgt in nodes:
        dist_map = lengths.get(tgt, {})
        for src in nodes:
            d = dist_map.get(src, float('inf'))
            if not math.isfinite(d):
                infl = 0.0
            else:
                infl = base[src] * math.exp(-decay * d) * affinity(src, tgt)
            raw[tgt] += infl
            pair_rows.append({
                'source': src,
                'target': tgt,
                'source_label': G.nodes[src].get('label'),
                'target_label': G.nodes[tgt].get('label'),
                'source_type': G.nodes[src].get('node_type'),
                'target_type': G.nodes[tgt].get('node_type'),
                'distance': d if math.isfinite(d) else None,
                'source_base_queriability': base[src],
                'pairwise_influence': infl,
            })

    non_root_max = max([v for k, v in raw.items() if k != root] or [1.0])
    for n in nodes:
        G.nodes[n]['raw_cartesian_queriability'] = float(raw[n])
        if n == root:
            q = 1.0
        else:
            q = 0.999 * raw[n] / non_root_max if non_root_max > 0 else 0.0
            q = min(0.999, max(0.0, q))
        G.nodes[n]['cartesian_queriability'] = float(q)
        G.nodes[n]['normalized_cartesian_queriability'] = float(q)
        # Use this as the displayed graph-wide score.
        G.nodes[n]['queriability'] = float(q)
        G.nodes[n]['normalized_queriability'] = float(q)

    pair_df = pd.DataFrame(pair_rows)
    if save_pairs_path is not None:
        pair_df.to_csv(save_pairs_path, index=False)
    return pair_df


def add_explicit_cartesian_edges(
    G: nx.DiGraph,
    pair_df: pd.DataFrame,
    threshold: float = 0.05,
) -> None:
    """
    Materialize full Cartesian queriability as explicit graph edges.

    If threshold == 0.0:
        graph becomes fully connected (N×N)

    Otherwise:
        only stronger interactions are shown.
    """

    existing = set((u, v) for u, v in G.edges())

    for _, row in pair_df.iterrows():

        u = row['source']
        v = row['target']

        if u == v:
            continue

        influence = safe_float(row['pairwise_influence'])

        if influence < threshold:
            continue

        # preserve canonical hierarchy edges
        if (u, v) in existing:
            continue

        G.add_edge(
            u,
            v,
            edge_type='cartesian',
            weight=influence,
            relative_queriability=influence,
        )

def assign_relative_queriability_edges(G: nx.DiGraph, key: str = 'cartesian_queriability') -> None:
    children = defaultdict(list)
    for u, v in primary_tree_edges(G): children[u].append(v)
    for u, childs in children.items():
        denom = sum(safe_float(G.nodes[c].get(key)) for c in childs)
        for v in childs:
            rq = safe_float(G.nodes[v].get(key)) / denom if denom > 0 else 0.0
            G[u][v]['relative_queriability'] = rq
            G[u][v]['weight'] = rq
    for u, v, d in G.edges(data=True):
        if d.get('edge_type') == 'sibling_context':
            d['relative_queriability'] = safe_float(d.get('weight'), 0.0)


def weighted_graph_from_schema(G: nx.DiGraph, pairwise_csv: Path | None = None) -> nx.DiGraph:
    W = G.copy()
    W.graph['name'] = 'AQF Weighted Schema Graph'
    compute_upward_schema_queriability(W)
    pair_df = compute_pairwise_cartesian_queriability(
        W,
        save_pairs_path=pairwise_csv
    )

    # ✅ NEW
    add_explicit_cartesian_edges(
        W,
        pair_df,
        threshold=getattr(W.graph, 'cartesian_threshold', 0.05)
    )
    # compute_pairwise_cartesian_queriability(W, save_pairs_path=pairwise_csv)
    assign_relative_queriability_edges(W, key='cartesian_queriability')
    return W


def selected_field_ids_from_form(form_path: Path) -> set:
    if not form_path or not form_path.exists(): return set()
    obj = load_json(form_path)
    return {str(f.get('field_id')) for f in obj.get('fields', []) if f.get('field_id') is not None}


def reduced_graph_from_weighted(W: nx.DiGraph, selected_field_ids: set, top_k: int = 30, min_weight: float = 0.0, pairwise_csv: Path | None = None) -> nx.DiGraph:
    field_nodes = [(n, d) for n, d in W.nodes(data=True) if d.get('node_type') == 'field']
    if selected_field_ids:
        keep_fields = {n for n, d in field_nodes if str(d.get('field_id')) in selected_field_ids}
    else:
        ranked = sorted(field_nodes, key=lambda x: x[1].get('cartesian_queriability', x[1].get('aqf_visual_weight', 0.0)), reverse=True)
        keep_fields = {n for n, d in ranked[:top_k] if safe_float(d.get('aqf_visual_weight')) >= min_weight}
    keep_nodes = set(keep_fields)
    for f in list(keep_fields): keep_nodes.update(nx.ancestors(W, f))
    R = W.subgraph(keep_nodes).copy()
    R.graph['name'] = 'AQF Reduced Schema Graph'
    compute_upward_schema_queriability(R)
    # compute_pairwise_cartesian_queriability(R, save_pairs_path=pairwise_csv)
    pair_df = compute_pairwise_cartesian_queriability(
        R,
        save_pairs_path=pairwise_csv
    )

    # ✅ NEW
    add_explicit_cartesian_edges(
        R,
        pair_df,
        threshold=getattr(R.graph, 'cartesian_threshold', 0.05)
    )
    assign_relative_queriability_edges(R, key='cartesian_queriability')
    return R


def organic_tree_layout(G: nx.DiGraph, root: str = 'schema:root', radial_gap: float = 5.3) -> Dict[str, Tuple[float, float]]:
    tree_children = defaultdict(list)
    for u, v in primary_tree_edges(G): tree_children[u].append(v)
    for parent in tree_children: tree_children[parent].sort(key=lambda n: (G.nodes[n].get('node_type',''), G.nodes[n].get('label','')))
    pos = {root: (0.0, 0.0)}
    def leaf_count(n: str) -> int:
        kids = tree_children.get(n, [])
        return 1 if not kids else sum(leaf_count(c) for c in kids)
    def assign(n: str, a0: float, a1: float, radius: float):
        kids = tree_children.get(n, [])
        if not kids: return
        total = sum(leaf_count(c) for c in kids)
        cursor = a0
        for c in kids:
            span = (a1 - a0) * leaf_count(c) / max(total, 1)
            mid = cursor + span / 2.0
            wobble = ((abs(hash(c)) % 100) / 100.0 - 0.5) * min(span * 0.10, 0.07)
            angle = mid + wobble
            r = radius + ((abs(hash('r'+c)) % 100) / 100.0 - 0.5) * 0.55
            pos[c] = (r * math.cos(angle), r * math.sin(angle))
            assign(c, cursor, cursor + span, radius + radial_gap)
            cursor += span
    assign(root, 0, 2*math.pi, radial_gap)
    return pos


def node_display_label(d: Dict[str, Any], mode: str = 'schema') -> str:
    base = short_label(d.get('label'), 42)
    if mode == 'schema': return base
    cq = safe_float(d.get('cartesian_queriability'))
    uq = safe_float(d.get('normalized_upward_queriability'))
    if d.get('node_type') == 'field':
        return f"{base}\nCQ={cq:.3f}, UQ={uq:.3f}\nw={safe_float(d.get('aqf_visual_weight')):.2f}"
    return f"{base}\nCQ={cq:.3f}, UQ={uq:.3f}"


def draw_graph(G: nx.DiGraph, path: Path, title: str, mode: str = 'schema', max_field_labels: int = 180, fig_width: float = 44, fig_height: float = 34, font_size: int = 14, node_scale: float = 2.4) -> None:
    plt.figure(figsize=(fig_width, fig_height))
    root = 'schema:root' if 'schema:root' in G.nodes else list(G.nodes)[0]
    pos = organic_tree_layout(G, root=root, radial_gap=5.3)
    node_types = nx.get_node_attributes(G, 'node_type')
    color_map = {'root':'#d9d9d9','composition_family':'#8ecae6','canonical_group':'#ffdd99','canonical_subgroup':'#b7e4c7','field':'#ffffff'}
    node_colors = [color_map.get(node_types.get(n), '#ffffff') for n in G.nodes]
    node_sizes = []
    for n in G.nodes:
        ntype = node_types.get(n)
        q = safe_float(G.nodes[n].get('cartesian_queriability'), 0.0)
        if ntype == 'root': size = 7000
        elif ntype == 'composition_family': size = 5200 + 16000*q
        elif ntype == 'canonical_group': size = 4400 + 14500*q
        elif ntype == 'canonical_subgroup': size = 3600 + 12500*q
        else: size = 2500 + 9500*min(1.0, max(q, safe_float(G.nodes[n].get('aqf_visual_weight'), 0.1)))
        node_sizes.append(size * node_scale)
    # containment = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') != 'sibling_context']
    # sibling = [(u, v) for u, v, d in G.edges(data=True) if d.get('edge_type') == 'sibling_context']
    containment = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get('edge_type') not in {'sibling_context', 'cartesian'}
    ]

    sibling = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get('edge_type') == 'sibling_context'
    ]

    # ✅ NEW
    cartesian = [
        (u, v)
        for u, v, d in G.edges(data=True)
        if d.get('edge_type') == 'cartesian'
    ]
    cont_widths = [1.5 + 10.0*safe_float(G[u][v].get('relative_queriability'), G[u][v].get('weight', 0.1)) for u, v in containment]
    # -------------------------------------------------
    # ✅ Cartesian edges
    # -------------------------------------------------

    if cartesian:

        cart_widths = []

        for u, v in cartesian:

            w = safe_float(
                G[u][v].get('weight'),
                0.01
            )

            cart_widths.append(
                max(0.15, min(1.5, w * 3.0))
            )

        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=cartesian,
            width=cart_widths,
            alpha=0.04,   # faint web
            arrows=False,
            edge_color='#888888',
        )
    nx.draw_networkx_edges(G, pos, edgelist=containment, width=cont_widths, alpha=0.55, arrows=True, arrowsize=24, edge_color='#4a4a4a')
    if sibling:
        sib_widths = [max(0.8, min(4.2, safe_float(G[u][v].get('weight'), 0.5) * 3.5)) for u, v in sibling]
        nx.draw_networkx_edges(G, pos, edgelist=sibling, width=sib_widths, alpha=0.16, arrows=False, edge_color='#999999', style='dashed')
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, edgecolors='black', linewidths=1.15)
    field_nodes = [(n, G.nodes[n]) for n in G.nodes if G.nodes[n].get('node_type') == 'field']
    top_fields = {n for n, _ in sorted(field_nodes, key=lambda x: x[1].get('cartesian_queriability', x[1].get('aqf_visual_weight', 0)), reverse=True)[:max_field_labels]}
    labels = {}
    for n, d in G.nodes(data=True):
        if d.get('node_type') != 'field' or n in top_fields: labels[n] = node_display_label(d, mode=mode)
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=font_size)
    if mode in {'weighted','reduced'}:
        edge_labels = {}
        for u, v, d in G.edges(data=True):
            if d.get('edge_type') != 'sibling_context' and safe_float(d.get('relative_queriability')) > 0:
                if G.nodes[v].get('node_type') != 'field' or v in top_fields:
                    edge_labels[(u, v)] = f"rq={safe_float(d.get('relative_queriability')):.2f}"
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=max(9, font_size-3), label_pos=0.55)
    plt.title(title, fontsize=font_size+12)
    plt.axis('off'); plt.tight_layout(); plt.savefig(path, dpi=260); plt.close()


def graph_to_tables(G: nx.DiGraph) -> Tuple[pd.DataFrame, pd.DataFrame]:
    return pd.DataFrame([{'node_id': n, **d} for n, d in G.nodes(data=True)]), pd.DataFrame([{'source': u, 'target': v, **d} for u, v, d in G.edges(data=True)])


def save_graph_json(G: nx.DiGraph, path: Path) -> None:
    write_json({'directed': True, 'name': G.graph.get('name', ''), 'nodes': [{'id': n, **d} for n, d in G.nodes(data=True)], 'edges': [{'source': u, 'target': v, **d} for u, v, d in G.edges(data=True)]}, path)


def save_dot(G: nx.DiGraph, path: Path) -> None:
    def esc(s): return str(s).replace('"', '\\"')
    lines = ['digraph G {', '  graph [rankdir=LR];', '  node [shape=box, style=rounded];']
    for n, d in G.nodes(data=True):
        label = esc(f"{d.get('label') or n}\\nCQ={safe_float(d.get('cartesian_queriability')):.3f}")
        lines.append(f'  "{esc(n)}" [label="{label}"];')
    for u, v, d in G.edges(data=True):
        rq = safe_float(d.get('relative_queriability'), safe_float(d.get('weight'), 0.0))
        lines.append(f'  "{esc(u)}" -> "{esc(v)}" [label="rq={rq:.2f}", penwidth={max(1.0, min(8.0, 1+rq*7)):.2f}];')
    lines.append('}')
    path.write_text('\n'.join(lines), encoding='utf-8')


def save_all_graph_outputs(G: nx.DiGraph, out_dir: Path, prefix: str, draw: bool, mode: str, fig_width: float, fig_height: float, font_size: int, max_field_labels: int, node_scale: float) -> None:
    nodes, edges = graph_to_tables(G)
    nodes.to_csv(out_dir / f'{prefix}_nodes.csv', index=False)
    edges.to_csv(out_dir / f'{prefix}_edges.csv', index=False)
    save_graph_json(G, out_dir / f'{prefix}.json')
    save_dot(G, out_dir / f'{prefix}.dot')
    try:
        nx.write_graphml(G, out_dir / f'{prefix}.graphml')
    except Exception:
        H = nx.DiGraph()
        for n, d in G.nodes(data=True): H.add_node(n, **{k: '' if v is None else str(v) for k, v in d.items()})
        for u, v, d in G.edges(data=True): H.add_edge(u, v, **{k: '' if val is None else str(val) for k, val in d.items()})
        nx.write_graphml(H, out_dir / f'{prefix}.graphml')
    if draw: draw_graph(G, out_dir / f'{prefix}.png', G.graph.get('name', prefix), mode=mode, max_field_labels=max_field_labels, fig_width=fig_width, fig_height=fig_height, font_size=font_size, node_scale=node_scale)


def graph_stats(G: nx.DiGraph, name: str) -> Dict[str, Any]:
    fields = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'field']
    return {
        'graph': name, 'node_count': G.number_of_nodes(), 'edge_count': G.number_of_edges(), 'field_node_count': len(fields),
        'max_depth': max([safe_float(G.nodes[n].get('depth')) for n in fields] or [0]),
        'root_cartesian_queriability': safe_float(G.nodes['schema:root'].get('cartesian_queriability')) if 'schema:root' in G.nodes else 0.0,
        'operator_count': sum(safe_float(G.nodes[n].get('operator_count')) for n in fields),
        'cartesian_edge_count': sum(
            1
            for _, _, d in G.edges(data=True)
            if d.get('edge_type') == 'cartesian'
        ),
        'weighted_operator_burden': sum(safe_float(G.nodes[n].get('weighted_operator_burden')) for n in fields),
    }


def main():
    p = argparse.ArgumentParser(description='Generate AQF schema graphs with full cartesian-product queriability and larger nodes.')
    p.add_argument('--data-dir', default=None)
    p.add_argument('--canonical-forest', default=None)
    p.add_argument('--results-dir', default=None)
    p.add_argument('--forms-json', default=None)
    p.add_argument('--out-dir', required=True)
    p.add_argument('--mu', type=float, default=0.25)
    p.add_argument('--top-k', type=int, default=30)
    p.add_argument('--min-weight', type=float, default=0.0)
    p.add_argument('--fig-width', type=float, default=44.0)
    p.add_argument('--fig-height', type=float, default=34.0)
    p.add_argument('--font-size', type=int, default=14)
    p.add_argument('--max-field-labels', type=int, default=180)
    p.add_argument('--node-scale', type=float, default=2.4)

    # ✅ NEW
    p.add_argument(
    '--cartesian-threshold',
    type=float,
    default=0.05,
    help='Threshold for explicit Cartesian edges. '
         '0.0 => full N×N graph'
)

    # ✅ NEW
    p.add_argument(
    '--cartesian-alpha',
    type=float,
    default=0.04,
    help='Transparency for Cartesian edges'
)

    p.add_argument('--no-draw', action='store_true')
    args = p.parse_args()
    out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    if args.canonical_forest:
        forest = load_json(Path(args.canonical_forest))
    elif args.data_dir:
        forest = build_canonical_forest_from_data(Path(args.data_dir))
        write_json(forest, out / 'canonical_forest_used.json')
    else:
        raise SystemExit('Provide either --canonical-forest or --data-dir')
    schema = build_schema_graph(forest, mu=args.mu)
    schema.graph['cartesian_threshold'] = args.cartesian_threshold
    weighted_pairwise_csv = out / 'weighted_schema_graph_pairwise_cartesian_queriability.csv'
    weighted = weighted_graph_from_schema(schema, pairwise_csv=weighted_pairwise_csv)
    forms_path = Path(args.forms_json) if args.forms_json else (Path(args.results_dir) / 'generated_forms' / 'aqf_full' / 'forms.json' if args.results_dir else None)
    selected = selected_field_ids_from_form(forms_path) if forms_path else set()
    reduced_pairwise_csv = out / 'reduced_schema_graph_pairwise_cartesian_queriability.csv'
    reduced = reduced_graph_from_weighted(weighted, selected, top_k=args.top_k, min_weight=args.min_weight, pairwise_csv=reduced_pairwise_csv)
    for prefix, graph, mode in [('schema_graph', schema, 'schema'), ('weighted_schema_graph', weighted, 'weighted'), ('reduced_schema_graph', reduced, 'reduced')]:
        save_all_graph_outputs(graph, out, prefix, not args.no_draw, mode, args.fig_width, args.fig_height, args.font_size, args.max_field_labels, args.node_scale)
    stats = pd.DataFrame([graph_stats(schema,'Schema Graph'), graph_stats(weighted,'Weighted Schema Graph'), graph_stats(reduced,'Reduced Schema Graph')])
    stats.to_csv(out / 'schema_graph_summary.csv', index=False)
    readme = [
        '# AQF Schema Graph Artifacts', '',
        'This version computes cartesian-product queriability across all node pairs.',
        'The root node `EHR Schema` is anchored at CQ=1.000. All other nodes are normalized below 1.000.', '',
        'Node labels:',
        '- `CQ`: full cartesian-product queriability adjusted against all nodes.',
        '- `UQ`: upward containment queriability.',
        '- `w`: initial AQF field weight for field nodes.', '',
        'Edge labels:',
        '- `rq`: relative child contribution to the parent based on CQ.', '',
        'Pairwise influence CSVs:',
        '- `weighted_schema_graph_pairwise_cartesian_queriability.csv`',
        '- `reduced_schema_graph_pairwise_cartesian_queriability.csv`', '',
        f'Selected fields source: `{forms_path if forms_path else "top-k fallback"}`'
    ]
    (out / 'README_schema_graphs.md').write_text('\n'.join(readme), encoding='utf-8')
    print('[OK] AQF graph generation complete:', out)
    print(stats.to_string(index=False))

if __name__ == '__main__':
    main()
