# query_summary.py

from __future__ import annotations
from typing import Dict, List, Optional

OPERATOR_PHRASES = {
    "=": "is",
    "!=": "is not",
    "contains": "contains",
    ">": "is greater than",
    "<": "is less than",
    "between": "is between",
    "is_known": "is known",
    "is_unknown": "is unknown"
}

def field_path_text(item: Dict) -> str:
    """
    Human-readable path like:
    HCPA → General data → State
    """
    entry = item.get("entry_name", "Unknown entry")
    cluster = item.get("cluster_path_str", "(no cluster)")
    element = item.get("element_name", item.get("name", "Field"))

    if cluster and cluster != "(no cluster)":
        return f"{entry} → {cluster} → {element}"
    return f"{entry} → {element}"

def predicate_to_text(pred: Dict) -> str:
    """
    Convert one active criterion to plain English.
    """
    field_text = field_path_text(pred)
    op = pred.get("operator", "")
    phrase = OPERATOR_PHRASES.get(op, op)
    value = pred.get("value")

    if op in ("is_known", "is_unknown"):
        return f"**{field_text}** {phrase}"

    if op == "between" and isinstance(value, (list, tuple)) and len(value) == 2:
        return f"**{field_text}** {phrase} `{value[0]}` and `{value[1]}`"

    return f"**{field_text}** {phrase} `{value}`"

def outputs_to_text(outputs: List[Dict]) -> str:
    """
    Convert selected outputs to plain-English list.
    """
    if not outputs:
        return "_No output fields selected._"

    labels = []
    for o in outputs:
        labels.append(f"`{o.get('element_name', o.get('name', 'Field'))}`")
    return ", ".join(labels)

def sort_to_text(sort_state: Optional[Dict]) -> str:
    if not sort_state:
        return "_No sorting applied._"

    field_text = field_path_text(sort_state)
    direction = sort_state.get("direction", "asc")
    direction_phrase = "ascending" if direction == "asc" else "descending"
    return f"**{field_text}** ({direction_phrase})"

def advanced_to_text(advanced: Dict) -> str:
    if not advanced:
        return "_Default execution settings._"

    occ = advanced.get("occurrence_semantics", "ALL")
    include_unknown = advanced.get("include_unknown", False)
    slice_size = advanced.get("slice_size")
    result_limit = advanced.get("result_limit")

    parts = [
        f"Repeated occurrence semantics: **{occ}**",
        f"Include unknown values: **{'Yes' if include_unknown else 'No'}**"
    ]

    if slice_size is not None:
        parts.append(f"Slice size: **{slice_size}**")
    if result_limit is not None:
        parts.append(f"Result limit: **{result_limit}**")

    return "  \n".join(parts)

def build_query_summary_markdown(
    criteria: List[Dict],
    outputs: List[Dict],
    sort_state: Optional[Dict],
    advanced: Optional[Dict] = None
) -> str:
    """
    Build a readable Markdown summary of the active query.
    """
    lines = []

    # Criteria
    lines.append("### Plain-English Query Summary")
    lines.append("")
    if criteria:
        lines.append("**Find records where:**")
        for idx, c in enumerate(criteria):
            prefix = "- " if idx == 0 else "- and "
            lines.append(f"{prefix}{predicate_to_text(c)}")
    else:
        lines.append("**Find records where:** _No filters applied_")

    lines.append("")
    lines.append("**Show fields:**")
    lines.append(outputs_to_text(outputs))

    lines.append("")
    lines.append("**Sort by:**")
    lines.append(sort_to_text(sort_state))

    if advanced:
        lines.append("")
        lines.append("**Execution settings:**")
        lines.append(advanced_to_text(advanced))

    return "  \n".join(lines)
