import math


def safe(x, d=0.0):
    try:
        return float(x)
    except:
        return d


def field_weight(field, mu=0.25):

    coverage = safe(field.get("coverage"))
    diversity = safe(field.get("distinct_ratio"), 0.3)

    path = field.get("canonical_path") or ""
    depth = len([p for p in path.split("/") if p.strip()])

    local = coverage * diversity
    specificity = min(1.0, depth / 8.0)

    return local + mu * specificity


def compute_node_queriability(G):

    # leaf fields already have base weight

    # upward aggregation
    def dfs(n):
        children = list(G.successors(n))

        if not children:
            q = safe(G.nodes[n].get("base_Q"))
            G.nodes[n]["Q"] = q
            return q

        total = sum(dfs(c) for c in children)
        G.nodes[n]["Q"] = total
        return total

    # root
    root = "schema:root"
    dfs(root)

    root_val = safe(G.nodes[root].get("Q"), 0.0)

    # ✅ CRITICAL FIX
    if root_val == 0:
        root_val = 1.0   # avoid crash, fallback normalization

    for n in G.nodes:
        G.nodes[n]["Q_norm"] = safe(G.nodes[n].get("Q")) / root_val

    # # normalize so root = 1
    # root_val = safe(G.nodes[root]["Q"], 1.0)

    # for n in G.nodes:
    #     G.nodes[n]["Q_norm"] = G.nodes[n]["Q"] / root_val
