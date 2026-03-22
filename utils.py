# utils.py

from __future__ import annotations
from typing import Any, List

def safe_get(d: Any, path: List[str], default=None):
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur

def ensure_list(x):
    """
    Normalize openEHR structures where 'items' or 'description.items'
    may be either a dict or a list. This is required because your attached
    composition files contain both variants. [1](https://stmicroelectronics-my.sharepoint.com/personal/akshat_kumar03_st_com/Documents/Microsoft%20Copilot%20Chat%20Files/1.2.2.489752100565248525010.049995050100494850555.510157981014898535356.559949102494855495598.101102481005156554948.json)[1](https://stmicroelectronics-my.sharepoint.com/personal/akshat_kumar03_st_com/Documents/Microsoft%20Copilot%20Chat%20Files/1.2.2.489752100565248525010.049995050100494850555.510157981014898535356.559949102494855495598.101102481005156554948.json)[2](https://stmicroelectronics-my.sharepoint.com/personal/akshat_kumar03_st_com/Documents/Microsoft%20Copilot%20Chat%20Files/1.2.1.48545410099491024998.10250574910157545151.97100574853569797505.44849575598561015210.156985356102495398559857.json)
    """
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return [x]
    return []

def title_fallback(s: str) -> str:
    if not s:
        return "(unnamed)"
    return s.replace("_", " ").strip().title()