import networkx as nx
import networkx as nx


def build_graph_from_dataset(fields):

    G = nx.DiGraph()

    root = "schema:root"
    G.add_node(root, label="EHR Schema", node_type="root", base_Q=0)

    for f in fields:

        leaf = "field:" + f["field_id"]
        group = "group:all_fields"

        if not G.has_node(group):
            G.add_node(group,
                       label="All Fields",
                       node_type="group",
                       base_Q=0)

        G.add_node(
            leaf,
            label=f["label"],
            node_type="field",
            base_Q=f["base_Q"]
        )

        G.add_edge(root, group)
        G.add_edge(group, leaf)

    return G

def build_graph_from_forest(forest, field_weight_func):

    G = nx.DiGraph()

    root = "schema:root"
    G.add_node(root, label="EHR Schema", node_type="root", base_Q=0)

    for fam, tree in forest["trees"].items():
        for f in tree["fields"]:

            leaf = "field:" + str(f.get("field_id"))
            group = "group:" + str(f.get("form_group"))

            if not G.has_node(group):
                G.add_node(group, label=f.get("form_group"), node_type="group", base_Q=0)

            G.add_node(
                leaf,
                label=f.get("label"),
                node_type="field",
                base_Q=field_weight_func(f),
            )

            G.add_edge(root, group)
            G.add_edge(group, leaf)

    return G


def add_pairwise_edges(G, Qpair, threshold):

    for (u, v), w in Qpair.items():

        if w < threshold:
            continue

        # don't overwrite tree edges
        if G.has_edge(u, v):
            continue

        G.add_edge(
            u,
            v,
            edge_type="pairwise",
            weight=w,
        )