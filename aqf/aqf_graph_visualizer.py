#!/usr/bin/env python3
"""Visualize schema/reduced graph for selected sweep or source graph."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
import matplotlib.pyplot as plt
import networkx as nx


def load(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def label(n): return str(n.get('name') or n.get('node_id',''))[:28]


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--graph_json', required=True)
    ap.add_argument('--output_png', required=True)
    ap.add_argument('--max_nodes', type=int, default=80)
    args=ap.parse_args()
    payload=load(args.graph_json)
    nodes=payload.get('nodes',[])[:args.max_nodes]
    node_ids={n.get('node_id') for n in nodes}
    G=nx.DiGraph()
    for n in nodes:
        G.add_node(n.get('node_id'), label=label(n), aqf_type=n.get('aqf_type'), rm_type=n.get('rm_type'))
    for e in payload.get('edges',[]):
        if e.get('source') in node_ids and e.get('target') in node_ids:
            G.add_edge(e.get('source'),e.get('target'),weight=float(e.get('weight') or 0.1))
    plt.figure(figsize=(14,10))
    pos=nx.spring_layout(G, seed=42, k=0.7)
    colors=[]
    for n in G.nodes:
        t=G.nodes[n].get('aqf_type') or G.nodes[n].get('rm_type')
        colors.append({'root':'tab:red','leaf':'tab:blue','DEMOGRAPHIC_ROOT':'tab:purple','DEMOGRAPHIC_FIELD':'tab:green'}.get(t,'tab:gray'))
    nx.draw_networkx_edges(G,pos,alpha=0.25,width=0.7,arrows=False)
    nx.draw_networkx_nodes(G,pos,node_size=180,node_color=colors,alpha=0.9)
    nx.draw_networkx_labels(G,pos,{n:G.nodes[n]['label'] for n in G.nodes},font_size=6)
    plt.axis('off'); plt.title('AQF schema graph visualization')
    Path(args.output_png).parent.mkdir(parents=True,exist_ok=True)
    plt.tight_layout(); plt.savefig(args.output_png,dpi=220); plt.close()
    print('Graph visualization saved to', args.output_png)
if __name__=='__main__': main()
