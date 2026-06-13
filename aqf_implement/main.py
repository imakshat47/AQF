import argparse
from pathlib import Path

from aqf_nodes import field_weight, compute_node_queriability
from aqf_pairwise import compute_pairwise_matrix
from aqf_graph import build_graph_from_dataset, add_pairwise_edges
from aqf_visualize import draw_graph

from aqf_dataset import load_dataset, extract_field_stats


def main():

    p = argparse.ArgumentParser()

    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--threshold", type=float, default=0.05)

    args = p.parse_args()

    print("[1] Loading dataset...")
    records = load_dataset(args.data)

    print("[2] Extracting fields...")
    fields = extract_field_stats(records)

    print("[3] Computing AQF weights...")
    for f in fields:
        f["base_Q"] = field_weight(f)

    print("[4] Building graph...")
    G = build_graph_from_dataset(fields)

    print("[5] Node queriability...")
    compute_node_queriability(G)

    print("[6] Pairwise queriability...")
    Qpair = compute_pairwise_matrix(G)

    print("[7] Adding edges...")
    add_pairwise_edges(G, Qpair, args.threshold)

    Path(args.out).mkdir(parents=True, exist_ok=True)

    print("[8] Drawing...")
    draw_graph(G, f"{args.out}/aqf_graph.png")

    print("[OK] DONE")


if __name__ == "__main__":
    main()

# import json
# import argparse
# from pathlib import Path

# from aqf_nodes import field_weight, compute_node_queriability
# from aqf_pairwise import compute_pairwise_matrix
# from aqf_graph import build_graph_from_forest, add_pairwise_edges
# from aqf_visualize import draw_graph


# def main():
#     p = argparse.ArgumentParser()

#     p.add_argument("--forest", required=True)
#     p.add_argument("--out", required=True)

#     p.add_argument("--threshold", type=float, default=0.05)

#     args = p.parse_args()

#     forest = json.load(open(args.forest))

#     # build graph
#     G = build_graph_from_forest(forest, field_weight)

#     # node queriability
#     compute_node_queriability(G)

#     # pairwise
#     Qpair = compute_pairwise_matrix(G)

#     # edges
#     add_pairwise_edges(G, Qpair, args.threshold)

#     Path(args.out).mkdir(parents=True, exist_ok=True)

#     draw_graph(G, f"{args.out}/aqf_cartesian_graph.png")

#     print("[OK] DONE")


# if __name__ == "__main__":
#     main()
