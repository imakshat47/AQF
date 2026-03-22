# schema_diagram.py

from __future__ import annotations

from graphviz import Digraph


def display_cluster_label(cluster_path_str: str) -> str:
    """
    User-friendly label for subgroup / cluster path.
    """
    if not cluster_path_str or cluster_path_str == "(no cluster)":
        return "Top-level fields"
    return cluster_path_str


def _field_count_for_subgroup(subgroup: dict) -> int:
    return len(subgroup.get("fields", {}))


def build_schema_flow_dot(
    union: dict,
    max_depth: int = 4,
    direction: str = "LR",
    leaf_limit: int = 5
):
    """
    Build a schema structure overview diagram.

    Depth semantics:
        1 = composition only
        2 = composition -> entry groups
        3 = composition -> entry groups -> subgroup paths
        4 = composition -> entry groups -> subgroup paths -> leaf elements

    If max_depth < 4:
        subgroup nodes will display leaf counts instead of leaf nodes.

    Parameters
    ----------
    union : dict
        Schema union object.
    max_depth : int
        Tree height (1..4).
    direction : str
        Graphviz direction:
        - "LR" = horizontal
        - "TB" = vertical
    leaf_limit : int
        Maximum number of leaf nodes to show per subgroup when max_depth >= 4.
    """
    dot = Digraph()
    dot.attr(rankdir=direction, fontsize="10")

    comp_label = union.get("composition_label", union.get("composition_archetype", "Composition"))
    comp_node = "composition_root"

    dot.node(
        comp_node,
        comp_label,
        shape="box",
        style="rounded,filled",
        fillcolor="#DFF6DD"
    )

    if max_depth <= 1:
        return dot

    groups = union.get("groups", {})

    for entry_arch, group in groups.items():
        entry_name = group.get("entry_name", entry_arch)
        subgroups = group.get("subgroups", {})
        total_leafs = sum(_field_count_for_subgroup(sg) for sg in subgroups.values())

        entry_label = entry_name
        if max_depth < 3:
            entry_label = f"{entry_name}\\n({len(subgroups)} groups, {total_leafs} fields)"

        entry_node = f"entry_{abs(hash(entry_arch))}"
        dot.node(
            entry_node,
            entry_label,
            shape="box",
            style="rounded,filled",
            fillcolor="#FFF4CC"
        )
        dot.edge(comp_node, entry_node)

        if max_depth <= 2:
            continue

        for subgroup_key, subgroup in subgroups.items():
            subgroup_label = display_cluster_label(subgroup_key)
            field_count = _field_count_for_subgroup(subgroup)

            subgroup_node = f"{entry_node}_{abs(hash(subgroup_key))}"

            if max_depth < 4:
                subgroup_label = f"{subgroup_label}\\n({field_count} fields)"

            dot.node(
                subgroup_node,
                subgroup_label,
                shape="ellipse",
                style="filled",
                fillcolor="#E8F0FE"
            )
            dot.edge(entry_node, subgroup_node)

            if max_depth < 4:
                continue

            fields = subgroup.get("fields", {})
            shown = 0

            for _, field in fields.items():
                if shown >= leaf_limit:
                    more_node = f"{subgroup_node}_more"
                    remaining = max(0, len(fields) - leaf_limit)
                    more_label = f"... (+{remaining} more)" if remaining > 0 else "..."
                    dot.node(more_node, more_label, shape="plaintext")
                    dot.edge(subgroup_node, more_node)
                    break

                field_label = field.get("element_name", "(field)")
                dv_type = field.get("dv_type", "")
                leaf_node = f"{subgroup_node}_{shown}"

                dot.node(
                    leaf_node,
                    f"{field_label}\\n[{dv_type}]",
                    shape="note",
                    style="filled",
                    fillcolor="#FCE8E6"
                )
                dot.edge(subgroup_node, leaf_node)
                shown += 1

    return dot


def build_touched_query_dot(
    criteria=None,
    outputs=None,
    sort_state=None,
    advanced=None,
    mode: str = "all",
    direction: str = "LR"
):
    """
    Build a touched-schema lineage diagram for the active query state.

    mode:
        - "all"      -> filters + outputs + sort + advanced execution settings
        - "criteria" -> filters only
        - "output"   -> outputs + sort
        - "advanced" -> sort + execution settings
    """
    criteria = criteria or []
    outputs = outputs or []
    advanced = advanced or {}

    dot = Digraph()
    dot.attr(rankdir=direction, fontsize="10")

    root_label = {
        "all": "Active query",
        "criteria": "Active filters",
        "output": "Active outputs",
        "advanced": "Advanced settings"
    }.get(mode, "Active query")

    root = "query_root"
    dot.node(
        root,
        root_label,
        shape="box",
        style="rounded,filled",
        fillcolor="#DFF6DD"
    )

    groups = {}

    def add_item(kind, item):
        entry = item.get("entry_name", "Unknown section")
        cluster = display_cluster_label(item.get("cluster_path_str", "(no cluster)"))
        field = item.get("element_name", item.get("name", "Field"))
        groups.setdefault(entry, {}).setdefault(cluster, []).append((kind, field, item))

    if mode in ("all", "criteria"):
        for c in criteria:
            add_item("filter", c)

    if mode in ("all", "output"):
        for o in outputs:
            add_item("output", o)

    if mode in ("all", "output", "advanced") and sort_state:
        add_item("sort", sort_state)

    for entry_name, clusters in groups.items():
        entry_node = f"entry_{abs(hash(entry_name))}"
        dot.node(
            entry_node,
            entry_name,
            shape="box",
            style="rounded,filled",
            fillcolor="#FFF4CC"
        )
        dot.edge(root, entry_node)

        for cluster_label, items in clusters.items():
            cluster_node = f"{entry_node}_{abs(hash(cluster_label))}"
            dot.node(
                cluster_node,
                cluster_label,
                shape="ellipse",
                style="filled",
                fillcolor="#E8F0FE"
            )
            dot.edge(entry_node, cluster_node)

            for idx, (kind, field, item) in enumerate(items):
                leaf_node = f"{cluster_node}_{idx}"

                if kind == "filter":
                    op = item.get("operator", "")
                    val = item.get("value", "")
                    if op in ("is_known", "is_unknown"):
                        label = f"{field}\\n[{op}]"
                    else:
                        label = f"{field}\\n[{op}] {val}"
                    color = "#FCE8E6"

                elif kind == "output":
                    label = f"{field}\\n[output]"
                    color = "#E6F4EA"

                else:
                    label = f"{field}\\n[sort: {item.get('direction', 'asc')}]"
                    color = "#EDE7F6"

                dot.node(
                    leaf_node,
                    label,
                    shape="note",
                    style="filled",
                    fillcolor=color
                )
                dot.edge(cluster_node, leaf_node)

    # Advanced execution settings block
    if mode in ("all", "advanced"):
        exec_lines = []
        if advanced:
            exec_lines.append(f"Occurrence semantics: {advanced.get('occurrence_semantics', 'ALL')}")
            exec_lines.append(f"Include unknown: {'Yes' if advanced.get('include_unknown', False) else 'No'}")
            exec_lines.append(f"Slice size: {advanced.get('slice_size', '')}")
            exec_lines.append(f"Result limit: {advanced.get('result_limit', '')}")

        if exec_lines:
            exec_node = "execution_settings"
            dot.node(
                exec_node,
                "\\n".join(exec_lines),
                shape="box",
                style="rounded,filled",
                fillcolor="#F3E5F5"
            )
            dot.edge(root, exec_node)

    return dot