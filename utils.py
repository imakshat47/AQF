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
    composition files contain both variants. [1]
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
