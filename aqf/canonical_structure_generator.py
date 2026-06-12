#!/usr/bin/env python3
"""
canonical_structure_generator.py

Generate AQF Canonical Tree and Canonical Form structures from a reduced or weighted
AQF schema graph JSON.

Input:
  - output/reduced_schema_graph.json  OR output/weighted_schema_graph.json

Outputs:
  - canonical_tree.json
  - canonical_forms.json
  - canonical_nodes.csv
  - canonical_edges.csv
  - canonical_form_summary.csv

AQF mapping:
  section      -> form_group
  substructure -> form_subgroup
  leaf         -> form_element

Canonical Form:
  CF = <IT, OT, RT>
  IT: input tree candidates for filtering/query specification
  OT: output tree candidates for projection/result display
  RT: relationship tree preserving containment/co-occurrence lineage
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================
# Data Classes
# ============================================================

@dataclass
class CanonicalNode:
    canonical_id: str
    source_node_id: str
    name: str
    canonical_type: str
    rm_type: str
    aqf_type: str
    datatype: Optional[str]
    archetype_node_id: Optional[str]
    archetype_id: Optional[str]
    template_id: Optional[str]
    path: str
    parent: Optional[str] = None
    children: List[str] = field(default_factory=list)

    coverage: float = 0.0
    sparsity: float = 0.0
    diversity: float = 0.0
    local_utility: float = 0.0
    queriability: float = 0.0

    depth: int = 0
    lineage: List[str] = field(default_factory=list)


@dataclass
class CanonicalEdge:
    source: str
    target: str
    edge_type: str
    source_schema_edge_type: str
    weight: float = 0.0
    structural_connectivity: float = 0.0
    containment_connectivity: float = 0.0
    cooccurrence_connectivity: float = 0.0


@dataclass
class CanonicalTree:
    tree_id: str
    root: str
    nodes: Dict[str, CanonicalNode] = field(default_factory=dict)
    edges: List[CanonicalEdge] = field(default_factory=list)
    total_queriability: float = 0.0
    max_depth: int = 0


@dataclass
class CanonicalForm:
    canonical_form_id: str
    source_tree_id: str
    form_group: str
    root_canonical_id: str

    input_tree: List[str] = field(default_factory=list)
    output_tree: List[str] = field(default_factory=list)
    relationship_tree: List[Dict[str, Any]] = field(default_factory=list)

    form_queriability: float = 0.0
    element_count: int = 0
    subgroup_count: int = 0
    max_depth: int = 0


# ============================================================
# Generator
# ============================================================

class AQFCanonicalStructureGenerator:
    CANONICAL_TYPE_MAP = {
        "section": "form_group",
        "substructure": "form_subgroup",
        "leaf": "form_element",
    }

    def __init__(
        self,
        input_weight_threshold: float = 0.0,
        output_weight_threshold: float = 0.0,
        include_cooccurrence_in_rt: bool = True,
        max_forms: Optional[int] = None,
    ) -> None:
        self.input_weight_threshold = input_weight_threshold
        self.output_weight_threshold = output_weight_threshold
        self.include_cooccurrence_in_rt = include_cooccurrence_in_rt
        self.max_forms = max_forms

        self.schema_nodes: Dict[str, Dict[str, Any]] = {}
        self.schema_edges: List[Dict[str, Any]] = []

        self.canonical_nodes: Dict[str, CanonicalNode] = {}
        self.canonical_edges: List[CanonicalEdge] = []
        self.schema_to_canonical: Dict[str, str] = {}

        self.children: Dict[str, List[str]] = defaultdict(list)
        self.parent: Dict[str, str] = {}
        self.roots: List[str] = []

        self.canonical_trees: Dict[str, CanonicalTree] = {}
        self.canonical_forms: Dict[str, CanonicalForm] = {}

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def load_schema_graph(self, graph_json: str | Path) -> None:
        with open(graph_json, "r", encoding="utf-8") as f:
            payload = json.load(f)

        self.schema_nodes = {node["node_id"]: node for node in payload.get("nodes", [])}
        self.schema_edges = payload.get("edges", [])

        if not self.schema_nodes:
            raise ValueError("Input graph contains no nodes.")

    def generate(self) -> Tuple[Dict[str, CanonicalTree], Dict[str, CanonicalForm]]:
        self._create_canonical_nodes()
        self._create_canonical_edges()
        self._assign_depth_and_lineage()
        self._build_canonical_trees()
        self._build_canonical_forms()
        return self.canonical_trees, self.canonical_forms

    # --------------------------------------------------------
    # Canonical Nodes / Edges
    # --------------------------------------------------------

    def _create_canonical_nodes(self) -> None:
        for source_node_id, source in self.schema_nodes.items():
            aqf_type = source.get("aqf_type", "substructure")
            canonical_type = self.CANONICAL_TYPE_MAP.get(aqf_type, "form_subgroup")
            canonical_id = self._make_canonical_id(source_node_id, canonical_type, source.get("name"))

            self.schema_to_canonical[source_node_id] = canonical_id

            node = CanonicalNode(
                canonical_id=canonical_id,
                source_node_id=source_node_id,
                name=source.get("name", "unnamed"),
                canonical_type=canonical_type,
                rm_type=source.get("rm_type", "UNKNOWN"),
                aqf_type=aqf_type,
                datatype=source.get("datatype"),
                archetype_node_id=source.get("archetype_node_id"),
                archetype_id=source.get("archetype_id"),
                template_id=source.get("template_id"),
                path=source.get("path", source_node_id),
                coverage=float(source.get("coverage") or 0.0),
                sparsity=float(source.get("sparsity") or 0.0),
                diversity=float(source.get("diversity") or 0.0),
                local_utility=float(source.get("local_utility") or 0.0),
                queriability=float(source.get("queriability") or 0.0),
            )
            self.canonical_nodes[canonical_id] = node

    def _create_canonical_edges(self) -> None:
        for edge in self.schema_edges:
            source_schema = edge.get("source")
            target_schema = edge.get("target")
            if source_schema not in self.schema_to_canonical or target_schema not in self.schema_to_canonical:
                continue

            source = self.schema_to_canonical[source_schema]
            target = self.schema_to_canonical[target_schema]
            schema_edge_type = edge.get("edge_type", "unknown")

            if schema_edge_type == "containment":
                canonical_edge_type = "canonical_containment"
                self.parent[target] = source
                if target not in self.children[source]:
                    self.children[source].append(target)
                self.canonical_nodes[target].parent = source
                if target not in self.canonical_nodes[source].children:
                    self.canonical_nodes[source].children.append(target)
            elif schema_edge_type == "cooccurrence":
                if not self.include_cooccurrence_in_rt:
                    continue
                canonical_edge_type = "canonical_association"
            else:
                canonical_edge_type = "canonical_association"

            self.canonical_edges.append(
                CanonicalEdge(
                    source=source,
                    target=target,
                    edge_type=canonical_edge_type,
                    source_schema_edge_type=schema_edge_type,
                    weight=float(edge.get("weight") or 0.0),
                    structural_connectivity=float(edge.get("structural_connectivity") or 0.0),
                    containment_connectivity=float(edge.get("containment_connectivity") or 0.0),
                    cooccurrence_connectivity=float(edge.get("cooccurrence_connectivity") or 0.0),
                )
            )

        all_nodes = set(self.canonical_nodes)
        child_nodes = set(self.parent)
        self.roots = sorted(list(all_nodes - child_nodes))

        # Prefer explicit form groups as roots.
        section_roots = [r for r in self.roots if self.canonical_nodes[r].canonical_type == "form_group"]
        if section_roots:
            self.roots = section_roots

    def _assign_depth_and_lineage(self) -> None:
        queue = deque()
        for root in self.roots:
            self.canonical_nodes[root].depth = 0
            self.canonical_nodes[root].lineage = [root]
            queue.append(root)

        visited = set(self.roots)
        while queue:
            current = queue.popleft()
            for child in self.children.get(current, []):
                if child in visited:
                    continue
                visited.add(child)
                self.canonical_nodes[child].depth = self.canonical_nodes[current].depth + 1
                self.canonical_nodes[child].lineage = self.canonical_nodes[current].lineage + [child]
                queue.append(child)

        # Handle disconnected nodes, if any.
        for node_id, node in self.canonical_nodes.items():
            if node_id not in visited:
                node.depth = 0
                node.lineage = [node_id]

    # --------------------------------------------------------
    # Canonical Trees
    # --------------------------------------------------------

    def _build_canonical_trees(self) -> None:
        for root in self.roots:
            tree_id = f"ct_{self._slug(self.canonical_nodes[root].name)}_{abs(hash(root)) % 100000}"
            subtree_nodes = self._collect_subtree_nodes(root)
            subtree_edges = [
                edge for edge in self.canonical_edges
                if edge.source in subtree_nodes and edge.target in subtree_nodes
            ]

            tree_nodes = {node_id: self.canonical_nodes[node_id] for node_id in subtree_nodes}
            total_q = sum(node.queriability for node in tree_nodes.values())
            max_depth = max((node.depth for node in tree_nodes.values()), default=0)

            self.canonical_trees[tree_id] = CanonicalTree(
                tree_id=tree_id,
                root=root,
                nodes=tree_nodes,
                edges=subtree_edges,
                total_queriability=total_q,
                max_depth=max_depth,
            )

    def _collect_subtree_nodes(self, root: str) -> Set[str]:
        result = set()
        stack = [root]
        while stack:
            current = stack.pop()
            if current in result:
                continue
            result.add(current)
            stack.extend(self.children.get(current, []))
        return result

    # --------------------------------------------------------
    # Canonical Forms
    # --------------------------------------------------------

    def _build_canonical_forms(self) -> None:
        ranked_trees = sorted(
            self.canonical_trees.values(),
            key=lambda tree: tree.total_queriability,
            reverse=True,
        )
        if self.max_forms is not None:
            ranked_trees = ranked_trees[: self.max_forms]

        for tree in ranked_trees:
            root_node = self.canonical_nodes[tree.root]
            form_id = f"cf_{self._slug(root_node.name)}_{abs(hash(tree.tree_id)) % 100000}"

            form_elements = [
                node for node in tree.nodes.values()
                if node.canonical_type == "form_element"
            ]
            form_subgroups = [
                node for node in tree.nodes.values()
                if node.canonical_type == "form_subgroup"
            ]

            input_tree = [
                node.canonical_id for node in form_elements
                if self._is_input_candidate(node)
            ]
            output_tree = [
                node.canonical_id for node in form_elements
                if self._is_output_candidate(node)
            ]

            # If thresholds remove all fields, keep top queriable elements to avoid empty forms.
            if not input_tree:
                input_tree = [n.canonical_id for n in sorted(form_elements, key=lambda x: x.queriability, reverse=True)[:10]]
            if not output_tree:
                output_tree = [n.canonical_id for n in sorted(form_elements, key=lambda x: x.queriability, reverse=True)[:10]]

            relationship_tree = []
            for edge in tree.edges:
                relationship_tree.append(
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "edge_type": edge.edge_type,
                        "source_schema_edge_type": edge.source_schema_edge_type,
                        "weight": edge.weight,
                        "structural_connectivity": edge.structural_connectivity,
                        "containment_connectivity": edge.containment_connectivity,
                        "cooccurrence_connectivity": edge.cooccurrence_connectivity,
                    }
                )

            self.canonical_forms[form_id] = CanonicalForm(
                canonical_form_id=form_id,
                source_tree_id=tree.tree_id,
                form_group=root_node.name,
                root_canonical_id=tree.root,
                input_tree=input_tree,
                output_tree=output_tree,
                relationship_tree=relationship_tree,
                form_queriability=sum(self.canonical_nodes[n].queriability for n in set(input_tree + output_tree)),
                element_count=len(form_elements),
                subgroup_count=len(form_subgroups),
                max_depth=tree.max_depth,
            )

    def _is_input_candidate(self, node: CanonicalNode) -> bool:
        if node.canonical_type != "form_element":
            return False
        if node.queriability < self.input_weight_threshold:
            return False
        # Datatype-aware filtering suitability is refined in the next operator-aware module.
        return True

    def _is_output_candidate(self, node: CanonicalNode) -> bool:
        if node.canonical_type != "form_element":
            return False
        if node.queriability < self.output_weight_threshold:
            return False
        return True

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    def save_outputs(self, output_dir: str | Path) -> None:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        self._save_canonical_tree_json(output_path / "canonical_tree.json")
        self._save_canonical_forms_json(output_path / "canonical_forms.json")
        self._save_canonical_nodes_csv(output_path / "canonical_nodes.csv")
        self._save_canonical_edges_csv(output_path / "canonical_edges.csv")
        self._save_canonical_form_summary_csv(output_path / "canonical_form_summary.csv")

    def _save_canonical_tree_json(self, path: Path) -> None:
        payload = {
            "metadata": {
                "tree_count": len(self.canonical_trees),
                "canonical_node_count": len(self.canonical_nodes),
                "canonical_edge_count": len(self.canonical_edges),
                "include_cooccurrence_in_rt": self.include_cooccurrence_in_rt,
            },
            "trees": [],
        }
        for tree in self.canonical_trees.values():
            payload["trees"].append(
                {
                    "tree_id": tree.tree_id,
                    "root": tree.root,
                    "root_name": self.canonical_nodes[tree.root].name,
                    "total_queriability": tree.total_queriability,
                    "max_depth": tree.max_depth,
                    "nodes": [self._canonical_node_to_dict(node) for node in tree.nodes.values()],
                    "edges": [asdict(edge) for edge in tree.edges],
                }
            )
        self._write_json(path, payload)

    def _save_canonical_forms_json(self, path: Path) -> None:
        payload = {
            "metadata": {
                "canonical_form_count": len(self.canonical_forms),
                "input_weight_threshold": self.input_weight_threshold,
                "output_weight_threshold": self.output_weight_threshold,
            },
            "canonical_forms": [],
        }
        for form in self.canonical_forms.values():
            item = asdict(form)
            item["input_tree_nodes"] = [self._canonical_node_to_dict(self.canonical_nodes[n]) for n in form.input_tree]
            item["output_tree_nodes"] = [self._canonical_node_to_dict(self.canonical_nodes[n]) for n in form.output_tree]
            payload["canonical_forms"].append(item)
        self._write_json(path, payload)

    def _save_canonical_nodes_csv(self, path: Path) -> None:
        columns = [
            "canonical_id", "source_node_id", "name", "canonical_type", "rm_type", "aqf_type",
            "datatype", "archetype_node_id", "archetype_id", "template_id", "path", "parent",
            "depth", "coverage", "sparsity", "diversity", "local_utility", "queriability", "lineage"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for node in self.canonical_nodes.values():
                writer.writerow({
                    "canonical_id": node.canonical_id,
                    "source_node_id": node.source_node_id,
                    "name": node.name,
                    "canonical_type": node.canonical_type,
                    "rm_type": node.rm_type,
                    "aqf_type": node.aqf_type,
                    "datatype": node.datatype,
                    "archetype_node_id": node.archetype_node_id,
                    "archetype_id": node.archetype_id,
                    "template_id": node.template_id,
                    "path": node.path,
                    "parent": node.parent,
                    "depth": node.depth,
                    "coverage": node.coverage,
                    "sparsity": node.sparsity,
                    "diversity": node.diversity,
                    "local_utility": node.local_utility,
                    "queriability": node.queriability,
                    "lineage": " > ".join(node.lineage),
                })

    def _save_canonical_edges_csv(self, path: Path) -> None:
        columns = [
            "source", "target", "edge_type", "source_schema_edge_type", "weight",
            "structural_connectivity", "containment_connectivity", "cooccurrence_connectivity"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for edge in self.canonical_edges:
                writer.writerow(asdict(edge))

    def _save_canonical_form_summary_csv(self, path: Path) -> None:
        columns = [
            "canonical_form_id", "source_tree_id", "form_group", "root_canonical_id",
            "form_queriability", "element_count", "subgroup_count", "max_depth",
            "input_field_count", "output_field_count", "relationship_count"
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()
            for form in self.canonical_forms.values():
                writer.writerow({
                    "canonical_form_id": form.canonical_form_id,
                    "source_tree_id": form.source_tree_id,
                    "form_group": form.form_group,
                    "root_canonical_id": form.root_canonical_id,
                    "form_queriability": form.form_queriability,
                    "element_count": form.element_count,
                    "subgroup_count": form.subgroup_count,
                    "max_depth": form.max_depth,
                    "input_field_count": len(form.input_tree),
                    "output_field_count": len(form.output_tree),
                    "relationship_count": len(form.relationship_tree),
                })

    def _canonical_node_to_dict(self, node: CanonicalNode) -> Dict[str, Any]:
        return asdict(node)

    def _write_json(self, path: Path, payload: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _make_canonical_id(self, source_node_id: str, canonical_type: str, name: Optional[str]) -> str:
        suffix = abs(hash(source_node_id)) % 100000000
        return f"{canonical_type}_{self._slug(name or 'node')}_{suffix}"

    def _slug(self, text: str) -> str:
        text = str(text).strip().lower()
        text = re.sub(r"[^a-z0-9]+", "_", text)
        text = re.sub(r"_+", "_", text).strip("_")
        return text or "unnamed"


# ============================================================
# CLI
# ============================================================

def generate_canonical_structures(
    graph_json: str | Path,
    output_dir: str | Path,
    input_weight_threshold: float = 0.0,
    output_weight_threshold: float = 0.0,
    include_cooccurrence_in_rt: bool = True,
    max_forms: Optional[int] = None,
) -> AQFCanonicalStructureGenerator:
    generator = AQFCanonicalStructureGenerator(
        input_weight_threshold=input_weight_threshold,
        output_weight_threshold=output_weight_threshold,
        include_cooccurrence_in_rt=include_cooccurrence_in_rt,
        max_forms=max_forms,
    )
    generator.load_schema_graph(graph_json)
    generator.generate()
    generator.save_outputs(output_dir)

    print("Canonical structure generation complete.")
    print(f"Input graph: {graph_json}")
    print(f"Output folder: {output_dir}")
    print(f"Canonical trees: {len(generator.canonical_trees)}")
    print(f"Canonical forms: {len(generator.canonical_forms)}")
    print(f"Canonical nodes: {len(generator.canonical_nodes)}")
    print(f"Canonical edges: {len(generator.canonical_edges)}")

    return generator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AQF canonical tree and canonical form structures from reduced/weighted schema graph JSON."
    )
    parser.add_argument("--graph_json", required=True, help="Path to reduced_schema_graph.json or weighted_schema_graph.json")
    parser.add_argument("--output_dir", required=True, help="Output folder for canonical structure files")
    parser.add_argument("--input_weight_threshold", type=float, default=0.0, help="Minimum queriability for input tree fields")
    parser.add_argument("--output_weight_threshold", type=float, default=0.0, help="Minimum queriability for output tree fields")
    parser.add_argument("--exclude_cooccurrence", action="store_true", help="Exclude co-occurrence associations from relationship tree")
    parser.add_argument("--max_forms", type=int, default=None, help="Maximum canonical forms to generate, ranked by tree queriability")

    args = parser.parse_args()

    generate_canonical_structures(
        graph_json=args.graph_json,
        output_dir=args.output_dir,
        input_weight_threshold=args.input_weight_threshold,
        output_weight_threshold=args.output_weight_threshold,
        include_cooccurrence_in_rt=not args.exclude_cooccurrence,
        max_forms=args.max_forms,
    )


if __name__ == "__main__":
    main()
