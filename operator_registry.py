# operator_registry.py

from __future__ import annotations

def operators_for_dv_type(dv_type: str, has_null_flavour: bool = False):
    """
    Friendly operator registry.
    This is the appropriate place for light hardcoding:
    operators and human-friendly phrases are not present in the JSON itself.
    """
    if dv_type in ("DV_CODED_TEXT", "DV_TEXT"):
        ops = [
            {"op": "=", "phrase": "is"},
            {"op": "!=", "phrase": "is not"},
            {"op": "contains", "phrase": "contains"},
        ]
    elif dv_type in ("DV_DATE", "DV_DATE_TIME"):
        ops = [
            {"op": "=", "phrase": "is on"},
            {"op": "<", "phrase": "is before"},
            {"op": ">", "phrase": "is after"},
            {"op": "between", "phrase": "is between"},
        ]
    elif dv_type in ("DV_COUNT", "DV_QUANTITY"):
        ops = [
            {"op": "=", "phrase": "equals"},
            {"op": "!=", "phrase": "does not equal"},
            {"op": ">", "phrase": "is greater than"},
            {"op": "<", "phrase": "is less than"},
            {"op": "between", "phrase": "is between"},
        ]
    elif dv_type == "DV_BOOLEAN":
        ops = [
            {"op": "=", "phrase": "is"}
        ]
    else:
        ops = [
            {"op": "=", "phrase": "is"},
            {"op": "contains", "phrase": "contains"},
        ]

    if has_null_flavour:
        ops.extend([
            {"op": "is_known", "phrase": "is known"},
            {"op": "is_unknown", "phrase": "is unknown"}
        ])

    return ops
