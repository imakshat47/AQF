#!/usr/bin/env python3
"""
aqf_schema_graph.py

Folder-based AQF schema graph generator for openEHR / ORBDA JSON compositions.

Generates:
  1. schema_graph.json
  2. weighted_schema_graph.json
  3. reduced_schema_graph.json
  4. weighted_nodes.csv / weighted_edges.csv
  5. reduced_nodes.csv / reduced_edges.csv

The implementation follows AQF-style ideas:
  - schema graph G = <V, E, tau, Phi>
  - containment edges from openEHR hierarchy
  - co-occurrence edges from composition-level co-presence
  - node queriability using coverage, diversity, local utility, and neighborhood reinforcement
  - reduced graph generation by theta * max(Q) with ancestor preservation
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, DefaultDict, Dict, Iterable, List, Optional, Set, Tuple


# ============================================================
# Data Classes
# ============================================================

@dataclass
class SchemaNode:
    node_id: str
    name: str
    rm_type: str
    aqf_type: str
    archetype_node_id: Optional[str]
    archetype_id: Optional[str]
    template_id: Optional[str]
    path: str
    datatype: Optional[str] = None

    records_present: Set[str] = field(default_factory=set)
    values: List[Any] = field(default_factory=list)

    coverage: float = 0.0
    sparsity: float = 0.0
    diversity: float = 0.0
    local_utility: float = 0.0
    queriability: float = 0.0


@dataclass
class SchemaEdge:
    source: str
    target: str
    edge_type: str

    records_present: Set[str] = field(default_factory=set)

    containment_connectivity: float = 0.0
    cooccurrence_connectivity: float = 0.0
    structural_connectivity: float = 0.0
    weight: float = 0.0


@dataclass
class SchemaGraph:
    nodes: Dict[str, SchemaNode] = field(default_factory=dict)
    edges: Dict[Tuple[str, str, str], SchemaEdge] = field(default_factory=dict)

    parent: Dict[str, Optional[str]] = field(default_factory=dict)
    children: DefaultDict[str, List[str]] = field(default_factory=lambda: defaultdict(list))

    def add_node(self, node: SchemaNode) -> None:
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node

    def add_edge(
        self,
        source: str,
        target: str,
        edge_type: str,
        record_id: Optional[str] = None,
    ) -> None:
        key = (source, target, edge_type)

        if key not in self.edges:
            self.edges[key] = SchemaEdge(source=source, target=target, edge_type=edge_type)

        if record_id is not None:
            self.edges[key].records_present.add(record_id)

        if edge_type == "containment":
            self.parent[target] = source
            if target not in self.children[source]:
                self.children[source].append(target)


# ============================================================
# AQF Schema Graph Builder
# ============================================================

class AQFEHRSchemaGraphBuilder:
    """
    Folder-based AQF schema graph builder for openEHR / ORBDA JSON compositions.

    Processing assumption:
      - each JSON file is treated as one composition instance / repository record
      - schema nodes are merged across files using structural path identity
      - composition UID and file name are NOT included in node identity
    """

    STRUCTURAL_TYPES: Dict[str, str] = {
        "COMPOSITION": "section",
        "SECTION": "section",

        "ADMIN_ENTRY": "substructure",
        "OBSERVATION": "substructure",
        "EVALUATION": "substructure",
        "ACTION": "substructure",
        "INSTRUCTION": "substructure",

        "ITEM_TREE": "substructure",
        "ITEM_LIST": "substructure",
        "ITEM_SINGLE": "substructure",
        "ITEM_TABLE": "substructure",
        "CLUSTER": "substructure",

        "ELEMENT": "leaf",
    }

    def __init__(
        self,
        lambda_cc: float = 0.7,
        mu: float = 0.5,
        theta: float = 0.25,
        edge_threshold: float = 0.3,
        cooccurrence_scope: str = "all",
    ) -> None:
        """
        Parameters
        ----------
        lambda_cc:
            Weight of containment connectivity in SC(u,v).
        mu:
            Neighborhood reinforcement factor in Q(v).
        theta:
            Reduced graph pruning threshold. Keep Q(v) >= theta * max(Q).
        edge_threshold:
            Minimum SC required to retain co-occurrence edges in reduced graph.
        cooccurrence_scope:
            "all"   -> create co-occurrence among all schema nodes in a composition.
            "leaf"  -> create co-occurrence only among ELEMENT nodes.
            "none"  -> disable co-occurrence edges.
        """
        if not 0.0 <= lambda_cc <= 1.0:
            raise ValueError("lambda_cc must be in [0, 1]")
        if mu < 0.0:
            raise ValueError("mu must be non-negative")
        if theta < 0.0:
            raise ValueError("theta must be non-negative")
        if edge_threshold < 0.0:
            raise ValueError("edge_threshold must be non-negative")
        if cooccurrence_scope not in {"all", "leaf", "none"}:
            raise ValueError("cooccurrence_scope must be one of: all, leaf, none")

        self.lambda_cc = lambda_cc
        self.mu = mu
        self.theta = theta
        self.edge_threshold = edge_threshold
        self.cooccurrence_scope = cooccurrence_scope

        self.graph = SchemaGraph()

        self.total_records = 0
        self.valid_record_ids: Set[str] = set()
        self.record_node_presence: DefaultDict[str, Set[str]] = defaultdict(set)

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    def build_from_folder(self, input_folder: str | Path) -> SchemaGraph:
        """Build unweighted schema graph from every .json file under input_folder."""
        input_path = Path(input_folder)
        json_files = sorted(input_path.rglob("*.json"))

        if not json_files:
            raise FileNotFoundError(f"No JSON files found in folder: {input_folder}")

        for file_path in json_files:
            record_id = self._make_record_id(file_path)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    document = json.load(f)
            except Exception as exc:
                print(f"[WARN] Skipping invalid JSON file: {file_path} -> {exc}")
                continue

            composition = self._find_composition_root(document)

            if composition is None:
                print(f"[WARN] No COMPOSITION found in: {file_path}")
                continue

            self.valid_record_ids.add(record_id)

            self._traverse_node(
                obj=composition,
                record_id=record_id,
                parent_id=None,
                path_parts=[],
                inherited_archetype_id=None,
                inherited_template_id=None,
            )

        self.total_records = len(self.valid_record_ids)
        return self.graph

    def build_weighted_schema_graph(self) -> SchemaGraph:
        """Annotate graph with statistics, edge weights, and node queriability."""
        self._compute_node_statistics()
        self._compute_containment_connectivity()
        self._compute_cooccurrence_edges()
        self._compute_structural_connectivity()
        self._compute_node_queriability()
        return self.graph

    def build_reduced_schema_graph(self) -> SchemaGraph:
        """Prune low-queriability nodes while preserving containment ancestors."""
        if not self.graph.nodes:
            return SchemaGraph()

        max_q = max(node.queriability for node in self.graph.nodes.values())
        if max_q <= 0:
            return self.graph

        threshold = self.theta * max_q

        retained_nodes = {
            node_id
            for node_id, node in self.graph.nodes.items()
            if node.queriability >= threshold
        }

        # Preserve containment context so retained leaf nodes are not orphaned.
        retained_with_ancestors = set(retained_nodes)
        for node_id in list(retained_nodes):
            current = node_id
            while current in self.graph.parent:
                parent = self.graph.parent.get(current)
                if parent is None:
                    break
                retained_with_ancestors.add(parent)
                current = parent

        reduced = SchemaGraph()

        for node_id in retained_with_ancestors:
            reduced.nodes[node_id] = self.graph.nodes[node_id]

        for key, edge in self.graph.edges.items():
            if edge.source not in retained_with_ancestors or edge.target not in retained_with_ancestors:
                continue

            keep_edge = edge.edge_type == "containment" or edge.structural_connectivity >= self.edge_threshold
            if keep_edge:
                reduced.edges[key] = edge

                if edge.edge_type == "containment":
                    reduced.parent[edge.target] = edge.source
                    if edge.target not in reduced.children[edge.source]:
                        reduced.children[edge.source].append(edge.target)

        return reduced

    # --------------------------------------------------------
    # Root detection
    # --------------------------------------------------------

    def _find_composition_root(self, document: Any) -> Optional[Dict[str, Any]]:
        """
        Supports both:
          1. direct COMPOSITION JSON
          2. versioned openEHR JSON: document["versions"]["data"]
        """
        if isinstance(document, dict):
            if document.get("type") == "COMPOSITION":
                return document

            archetype_node_id = str(document.get("archetype_node_id", ""))
            if archetype_node_id.startswith("openEHR-EHR-COMPOSITION"):
                return document

            version_data = document.get("versions", {}).get("data")
            if isinstance(version_data, dict) and version_data.get("type") == "COMPOSITION":
                return version_data

            for value in document.values():
                found = self._find_composition_root(value)
                if found is not None:
                    return found

        elif isinstance(document, list):
            for item in document:
                found = self._find_composition_root(item)
                if found is not None:
                    return found

        return None

    # --------------------------------------------------------
    # Traversal
    # --------------------------------------------------------

    def _traverse_node(
        self,
        obj: Any,
        record_id: str,
        parent_id: Optional[str],
        path_parts: List[str],
        inherited_archetype_id: Optional[str],
        inherited_template_id: Optional[str],
    ) -> None:
        if isinstance(obj, dict):
            rm_type = obj.get("type")

            if rm_type is None and self._looks_like_composition(obj):
                rm_type = "COMPOSITION"

            archetype_id, template_id = self._extract_archetype_template(
                obj=obj,
                inherited_archetype_id=inherited_archetype_id,
                inherited_template_id=inherited_template_id,
            )

            if self._is_schema_node(obj, rm_type):
                name = self._extract_name(obj)
                archetype_node_id = obj.get("archetype_node_id")
                datatype = self._extract_datatype(obj)

                current_part = self._make_path_part(
                    rm_type=rm_type,
                    name=name,
                    archetype_node_id=archetype_node_id,
                    archetype_id=archetype_id,
                )

                current_path_parts = path_parts + [current_part]
                path = "/" + "/".join(current_path_parts)
                node_id = self._make_schema_node_id(path)

                aqf_type = self.STRUCTURAL_TYPES.get(rm_type or "", "substructure")

                node = SchemaNode(
                    node_id=node_id,
                    name=name,
                    rm_type=rm_type or "UNKNOWN",
                    aqf_type=aqf_type,
                    archetype_node_id=archetype_node_id,
                    archetype_id=archetype_id,
                    template_id=template_id,
                    path=path,
                    datatype=datatype,
                )

                self.graph.add_node(node)
                self.graph.nodes[node_id].records_present.add(record_id)
                self.record_node_presence[record_id].add(node_id)

                atomic_value = self._extract_atomic_value(obj)
                if atomic_value is not None:
                    self.graph.nodes[node_id].values.append(atomic_value)

                if parent_id is not None:
                    self.graph.add_edge(
                        source=parent_id,
                        target=node_id,
                        edge_type="containment",
                        record_id=record_id,
                    )

                parent_id = node_id
                path_parts = current_path_parts

            for value in obj.values():
                self._traverse_node(
                    obj=value,
                    record_id=record_id,
                    parent_id=parent_id,
                    path_parts=path_parts,
                    inherited_archetype_id=archetype_id,
                    inherited_template_id=template_id,
                )

        elif isinstance(obj, list):
            for item in obj:
                self._traverse_node(
                    obj=item,
                    record_id=record_id,
                    parent_id=parent_id,
                    path_parts=path_parts,
                    inherited_archetype_id=inherited_archetype_id,
                    inherited_template_id=inherited_template_id,
                )

    def _looks_like_composition(self, obj: Dict[str, Any]) -> bool:
        archetype_node_id = str(obj.get("archetype_node_id", ""))
        return archetype_node_id.startswith("openEHR-EHR-COMPOSITION")

    def _is_schema_node(self, obj: Dict[str, Any], rm_type: Optional[str]) -> bool:
        if rm_type in self.STRUCTURAL_TYPES:
            return True
        if "archetype_node_id" in obj and "name" in obj:
            return True
        return False

    # --------------------------------------------------------
    # Metadata extraction
    # --------------------------------------------------------

    def _extract_name(self, obj: Dict[str, Any]) -> str:
        name = obj.get("name")

        if isinstance(name, dict):
            return str(name.get("value", "unnamed"))
        if isinstance(name, str):
            return name
        return str(obj.get("archetype_node_id", "unnamed"))

    def _extract_archetype_template(
        self,
        obj: Dict[str, Any],
        inherited_archetype_id: Optional[str],
        inherited_template_id: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        archetype_id = inherited_archetype_id
        template_id = inherited_template_id

        details = obj.get("archetype_details")
        if isinstance(details, dict):
            aid = details.get("archetype_id", {})
            tid = details.get("template_id", {})

            if isinstance(aid, dict):
                archetype_id = aid.get("value", archetype_id)
            if isinstance(tid, dict):
                template_id = tid.get("value", template_id)

        return archetype_id, template_id

    def _extract_datatype(self, obj: Dict[str, Any]) -> Optional[str]:
        value = obj.get("value")
        if isinstance(value, dict):
            return value.get("type")
        return None

    def _extract_atomic_value(self, obj: Dict[str, Any]) -> Optional[Any]:
        """
        Extract only actual data values.
        Null-flavour nodes are kept structurally but not counted for diversity.
        """
        value = obj.get("value")
        if not isinstance(value, dict):
            return None

        if "value" in value:
            return value["value"]
        if "magnitude" in value:
            return value["magnitude"]
        return None

    # --------------------------------------------------------
    # ID construction
    # --------------------------------------------------------

    def _make_record_id(self, file_path: Path) -> str:
        # Relative or stem-based IDs are enough for record-level counting.
        return file_path.stem

    def _normalize(self, text: Optional[str]) -> str:
        if text is None:
            return "none"

        value = str(text).strip().lower()
        for old, new in [
            (" ", "_"),
            ("/", "_"),
            ("\\", "_"),
            (":", "_"),
            ("|", "_"),
            ("\n", "_"),
            ("\t", "_"),
        ]:
            value = value.replace(old, new)
        return value

    def _make_path_part(
        self,
        rm_type: Optional[str],
        name: str,
        archetype_node_id: Optional[str],
        archetype_id: Optional[str],
    ) -> str:
        return "|".join(
            [
                self._normalize(rm_type),
                self._normalize(name),
                self._normalize(archetype_node_id),
                self._normalize(archetype_id),
            ]
        )

    def _make_schema_node_id(self, path: str) -> str:
        """
        Repository-level schema node identity.

        Important:
          - do NOT use composition UID
          - do NOT use file name
          - same schema element across multiple records should merge
        """
        return path

    # --------------------------------------------------------
    # Statistics
    # --------------------------------------------------------

    def _compute_node_statistics(self) -> None:
        for node in self.graph.nodes.values():
            present_count = len(node.records_present)

            node.coverage = present_count / self.total_records if self.total_records else 0.0
            node.sparsity = 1.0 - node.coverage

            distinct_values = {str(v) for v in node.values}
            node.diversity = len(distinct_values) / present_count if present_count else 0.0
            node.local_utility = node.coverage * node.diversity

    def _compute_containment_connectivity(self) -> None:
        for edge in self.graph.edges.values():
            if edge.edge_type != "containment":
                continue

            source_depth = self._depth(edge.source)
            target_depth = self._depth(edge.target)
            distance = max(abs(target_depth - source_depth), 1)
            edge.containment_connectivity = 1.0 / distance

    def _compute_cooccurrence_edges(self) -> None:
        if self.cooccurrence_scope == "none":
            return

        pair_records: Dict[Tuple[str, str], Set[str]] = defaultdict(set)

        for record_id, node_ids in self.record_node_presence.items():
            filtered_nodes = self._filter_nodes_for_cooccurrence(node_ids)
            sorted_nodes = sorted(filtered_nodes)

            for u, v in combinations(sorted_nodes, 2):
                pair_records[(u, v)].add(record_id)

        for (u, v), records in pair_records.items():
            support = len(records) / self.total_records if self.total_records else 0.0

            self.graph.add_edge(u, v, "cooccurrence")
            self.graph.add_edge(v, u, "cooccurrence")

            self.graph.edges[(u, v, "cooccurrence")].records_present = set(records)
            self.graph.edges[(v, u, "cooccurrence")].records_present = set(records)

            self.graph.edges[(u, v, "cooccurrence")].cooccurrence_connectivity = support
            self.graph.edges[(v, u, "cooccurrence")].cooccurrence_connectivity = support

    def _filter_nodes_for_cooccurrence(self, node_ids: Iterable[str]) -> List[str]:
        if self.cooccurrence_scope == "all":
            return list(node_ids)
        if self.cooccurrence_scope == "leaf":
            return [node_id for node_id in node_ids if self.graph.nodes[node_id].aqf_type == "leaf"]
        return []

    def _compute_structural_connectivity(self) -> None:
        for edge in self.graph.edges.values():
            cc = edge.containment_connectivity
            co = edge.cooccurrence_connectivity

            if edge.edge_type == "cooccurrence":
                cc = self._path_affinity(edge.source, edge.target)
                edge.containment_connectivity = cc

            edge.structural_connectivity = self.lambda_cc * cc + (1.0 - self.lambda_cc) * co
            edge.weight = edge.structural_connectivity

    def _compute_node_queriability(self) -> None:
        """
        AQF-style node queriability:
          Q(v) = LU(v) + mu * sum_{u in N(v)} SC(u,v) * LU(u)
        """
        incoming: DefaultDict[str, List[Tuple[str, float]]] = defaultdict(list)

        for edge in self.graph.edges.values():
            if edge.structural_connectivity > 0:
                incoming[edge.target].append((edge.source, edge.structural_connectivity))

        for node_id, node in self.graph.nodes.items():
            reinforcement = 0.0

            for neighbor_id, sc in incoming[node_id]:
                neighbor = self.graph.nodes.get(neighbor_id)
                if neighbor is not None:
                    reinforcement += sc * neighbor.local_utility

            node.queriability = node.local_utility + self.mu * reinforcement

    # --------------------------------------------------------
    # Utility functions
    # --------------------------------------------------------

    def _depth(self, node_id: str) -> int:
        return len(node_id.strip("/").split("/")) if node_id else 0

    def _path_affinity(self, u: str, v: str) -> float:
        u_parts = u.strip("/").split("/")
        v_parts = v.strip("/").split("/")

        shared = 0
        for a, b in zip(u_parts, v_parts):
            if a == b:
                shared += 1
            else:
                break

        return shared / max(len(u_parts), len(v_parts), 1)

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    def graph_to_dict(self, graph: SchemaGraph) -> Dict[str, Any]:
        nodes = []
        edges = []

        for node in graph.nodes.values():
            item = asdict(node)
            item["records_present"] = sorted(list(node.records_present))
            nodes.append(item)

        for edge in graph.edges.values():
            item = asdict(edge)
            item["records_present"] = sorted(list(edge.records_present))
            edges.append(item)

        return {
            "metadata": {
                "total_records": self.total_records,
                "lambda_cc": self.lambda_cc,
                "mu": self.mu,
                "theta": self.theta,
                "edge_threshold": self.edge_threshold,
                "cooccurrence_scope": self.cooccurrence_scope,
                "node_count": len(nodes),
                "edge_count": len(edges),
            },
            "nodes": nodes,
            "edges": edges,
        }

    def save_graph_json(self, graph: SchemaGraph, output_file: str | Path) -> None:
        payload = self.graph_to_dict(graph)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def save_nodes_csv(self, graph: SchemaGraph, output_file: str | Path) -> None:
        columns = [
            "node_id",
            "name",
            "rm_type",
            "aqf_type",
            "archetype_node_id",
            "archetype_id",
            "template_id",
            "path",
            "datatype",
            "coverage",
            "sparsity",
            "diversity",
            "local_utility",
            "queriability",
            "records_present_count",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for node in graph.nodes.values():
                writer.writerow(
                    {
                        "node_id": node.node_id,
                        "name": node.name,
                        "rm_type": node.rm_type,
                        "aqf_type": node.aqf_type,
                        "archetype_node_id": node.archetype_node_id,
                        "archetype_id": node.archetype_id,
                        "template_id": node.template_id,
                        "path": node.path,
                        "datatype": node.datatype,
                        "coverage": node.coverage,
                        "sparsity": node.sparsity,
                        "diversity": node.diversity,
                        "local_utility": node.local_utility,
                        "queriability": node.queriability,
                        "records_present_count": len(node.records_present),
                    }
                )

    def save_edges_csv(self, graph: SchemaGraph, output_file: str | Path) -> None:
        columns = [
            "source",
            "target",
            "edge_type",
            "containment_connectivity",
            "cooccurrence_connectivity",
            "structural_connectivity",
            "weight",
            "records_present_count",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=columns)
            writer.writeheader()

            for edge in graph.edges.values():
                writer.writerow(
                    {
                        "source": edge.source,
                        "target": edge.target,
                        "edge_type": edge.edge_type,
                        "containment_connectivity": edge.containment_connectivity,
                        "cooccurrence_connectivity": edge.cooccurrence_connectivity,
                        "structural_connectivity": edge.structural_connectivity,
                        "weight": edge.weight,
                        "records_present_count": len(edge.records_present),
                    }
                )


# ============================================================
# Runner
# ============================================================

def generate_graphs_from_folder(
    input_folder: str | Path,
    output_folder: str | Path,
    lambda_cc: float = 0.7,
    mu: float = 0.5,
    theta: float = 0.25,
    edge_threshold: float = 0.3,
    cooccurrence_scope: str = "all",
) -> Tuple[AQFEHRSchemaGraphBuilder, SchemaGraph, SchemaGraph, SchemaGraph]:
    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)

    builder = AQFEHRSchemaGraphBuilder(
        lambda_cc=lambda_cc,
        mu=mu,
        theta=theta,
        edge_threshold=edge_threshold,
        cooccurrence_scope=cooccurrence_scope,
    )

    schema_graph = builder.build_from_folder(input_folder)
    weighted_graph = builder.build_weighted_schema_graph()
    reduced_graph = builder.build_reduced_schema_graph()

    builder.save_graph_json(schema_graph, output_path / "schema_graph.json")
    builder.save_graph_json(weighted_graph, output_path / "weighted_schema_graph.json")
    builder.save_graph_json(reduced_graph, output_path / "reduced_schema_graph.json")

    builder.save_nodes_csv(weighted_graph, output_path / "weighted_nodes.csv")
    builder.save_edges_csv(weighted_graph, output_path / "weighted_edges.csv")

    builder.save_nodes_csv(reduced_graph, output_path / "reduced_nodes.csv")
    builder.save_edges_csv(reduced_graph, output_path / "reduced_edges.csv")

    print("AQF schema graph generation complete.")
    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")
    print(f"Total valid compositions processed: {builder.total_records}")
    print(f"Schema graph nodes: {len(schema_graph.nodes)}")
    print(f"Schema graph edges: {len(schema_graph.edges)}")
    print(f"Reduced graph nodes: {len(reduced_graph.nodes)}")
    print(f"Reduced graph edges: {len(reduced_graph.edges)}")

    return builder, schema_graph, weighted_graph, reduced_graph


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate AQF schema graph, weighted schema graph, and reduced schema graph from an openEHR JSON folder."
    )

    parser.add_argument("--input", required=True, help="Input folder containing openEHR JSON composition files.")
    parser.add_argument("--output", default="output", help="Output folder for generated graph files.")
    parser.add_argument("--lambda_cc", type=float, default=0.7, help="Weight of containment connectivity.")
    parser.add_argument("--mu", type=float, default=0.5, help="Neighborhood reinforcement factor.")
    parser.add_argument("--theta", type=float, default=0.25, help="Reduced graph pruning threshold.")
    parser.add_argument("--edge_threshold", type=float, default=0.3, help="Minimum SC for retaining co-occurrence edges.")
    parser.add_argument(
        "--cooccurrence_scope",
        choices=["all", "leaf", "none"],
        default="all",
        help="Co-occurrence edge generation scope. Use 'leaf' for large repositories.",
    )

    args = parser.parse_args()

    generate_graphs_from_folder(
        input_folder=args.input,
        output_folder=args.output,
        lambda_cc=args.lambda_cc,
        mu=args.mu,
        theta=args.theta,
        edge_threshold=args.edge_threshold,
        cooccurrence_scope=args.cooccurrence_scope,
    )


if __name__ == "__main__":
    main()
