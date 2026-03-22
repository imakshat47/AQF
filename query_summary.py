# query_summary.py

from __future__ import annotations


def _display_cluster_label(cluster_path_str: str) -> str:
    """
    Friendly label for subgroup / cluster path.
    """
    if not cluster_path_str or cluster_path_str == "(no cluster)":
        return "Top-level fields"
    return cluster_path_str


def _field_phrase(item: dict) -> str:
    """
    Human-readable field phrase:
    patient age (HCPA → General data → patient age)
    """
    entry = item.get("entry_name", "Section")
    cluster = _display_cluster_label(item.get("cluster_path_str", "(no cluster)"))
    field = item.get("element_name", item.get("name", "Field"))
    return f"{field} ({entry} → {cluster} → {field})"


def _operator_phrase(op: str, value) -> str:
    """
    Translate AQF operator into plain English.
    """
    op_map = {
        "=": "is",
        "==": "is",
        "!=": "is not",
        ">": "is greater than",
        ">=": "is greater than or equal to",
        "<": "is less than",
        "<=": "is less than or equal to",
        "contains": "contains",
        "starts_with": "starts with",
        "ends_with": "ends with",
        "is_known": "is known",
        "is_unknown": "is unknown"
    }

    phrase = op_map.get(op, op)

    if op in ("is_known", "is_unknown"):
        return phrase

    return f"{phrase} {value}"


def build_query_summary_markdown(criteria, outputs, sort_state, advanced):
    """
    Build a flowing plain-English summary instead of a bulleted summary.

    Returns markdown blockquote text.
    """
    parts = []

    # -------------------------------------------------
    # Find records where ...
    # -------------------------------------------------
    if criteria:
        crit_phrases = []
        for c in criteria:
            field_phrase = _field_phrase(c)
            op_phrase = _operator_phrase(c.get("operator", ""), c.get("value", ""))
            crit_phrases.append(f"{field_phrase} {op_phrase}")
        find_clause = "Find records where " + " and ".join(crit_phrases) + "."
    else:
        find_clause = "Find records from the current record family."

    parts.append(find_clause)

    # -------------------------------------------------
    # Show ...
    # -------------------------------------------------
    if outputs:
        out_names = [o.get("element_name", o.get("name", "Field")) for o in outputs]

        if len(out_names) == 1:
            show_clause = f"Show {out_names[0]}."
        elif len(out_names) == 2:
            show_clause = f"Show {out_names[0]} and {out_names[1]}."
        else:
            show_clause = "Show " + ", ".join(out_names[:-1]) + f", and {out_names[-1]}."
    else:
        show_clause = "Show the default result fields."

    parts.append(show_clause)

    # -------------------------------------------------
    # Sort ...
    # -------------------------------------------------
    if sort_state:
        sort_field = _field_phrase(sort_state)
        direction = sort_state.get("direction", "asc")
        direction_phrase = "ascending order" if direction == "asc" else "descending order"
        sort_clause = f"Return the results sorted by {sort_field} in {direction_phrase}."
        parts.append(sort_clause)

    # -------------------------------------------------
    # Advanced execution details
    # -------------------------------------------------
    if advanced:
        occ = advanced.get("occurrence_semantics", "ALL")
        include_unknown = advanced.get("include_unknown", False)
        slice_size = advanced.get("slice_size", "")
        result_limit = advanced.get("result_limit", "")

        adv_clause = (
            f"Execution uses {occ} occurrence semantics, "
            f"{'includes' if include_unknown else 'excludes'} unknown values, "
            f"scans up to {slice_size} records, and returns up to {result_limit} matches."
        )
        parts.append(adv_clause)

    text = " ".join(parts)
    return f"> **Query summary.** {text}"