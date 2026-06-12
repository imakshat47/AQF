import math


def compute_pairwise_matrix(G, decay=0.6):

    nodes = list(G.nodes)

    # shortest path distance
    dist = dict()

    import networkx as nx
    H = nx.Graph()
    H.add_edges_from(G.edges())

    lengths = dict(nx.all_pairs_shortest_path_length(H))

    Qpair = {}

    for u in nodes:
        for v in nodes:
            if u == v:
                continue

            d = lengths.get(u, {}).get(v, 10)

            base = G.nodes[u].get("Q_norm", 0.01)

            q = base * math.exp(-decay * d)

            Qpair[(u, v)] = q

    return Qpair
