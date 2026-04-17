"""AQF utility package.

Keeps legacy helper functions available via `from utils import ...` while
adding design-system helpers under `utils.theme_manager` and `utils.ui_helpers`.
"""

from __future__ import annotations

from typing import Any, List


def safe_get(d: Any, path: List[str], default=None):
    """Safely walk nested dictionaries using a path list."""
    cur = d
    for p in path:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def ensure_list(x):
    """Normalize values to a list for mixed dict/list JSON fields."""
    if x is None:
        return []
    if isinstance(x, list):
        return x
    if isinstance(x, dict):
        return [x]
    return []


def title_fallback(s: str) -> str:
    """Title-case string with a safe unnamed fallback."""
    if not s:
        return "(unnamed)"
    return s.replace("_", " ").strip().title()
