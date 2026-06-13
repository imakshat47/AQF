import matplotlib.pyplot as plt
import networkx as nx


def draw_graph(G, path):

    plt.figure(figsize=(40, 30))

    pos = nx.spring_layout(G, k=0.9, seed=42)

    # node sizes
    sizes = [
        5000 + 20000 * G.nodes[n].get("Q_norm", 0)
        for n in G.nodes
    ]

    nx.draw_networkx_nodes(
        G,
        pos,
        node_size=sizes,
        node_color="#d0e6ff",
        edgecolors="black"
    )

    # edges
    pair_edges = [(u, v) for u, v, d in G.edges(data=True)
                  if d.get("edge_type") == "pairwise"]

    tree_edges = [(u, v) for u, v, d in G.edges(data=True)
                  if d.get("edge_type") != "pairwise"]

    # faint dense web
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=pair_edges,
        alpha=0.03,
        width=0.5,
        edge_color="gray"
    )

    # structure edges
    nx.draw_networkx_edges(
        G,
        pos,
        edgelist=tree_edges,
        width=3,
        edge_color="black"
    )

    labels = {
        n: f"{G.nodes[n].get('label')}\nQ={G.nodes[n].get('Q_norm',0):.2f}"
        for n in G.nodes
    }

    nx.draw_networkx_labels(G, pos, labels, font_size=10)

    plt.axis("off")
    plt.savefig(path, dpi=250)
    plt.close()