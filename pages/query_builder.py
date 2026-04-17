from __future__ import annotations

import streamlit as st

from components.field_card import render_field_card
from components.filter_chip import render_filter_chips
from components.query_preview import render_query_preview


def render_query_builder_header(criteria, outputs, sort_state):
    st.markdown("#### Active Query")
    render_filter_chips(criteria, outputs, sort_state)


def render_criteria_controls(form: dict):
    st.markdown("#### Filters")
    st.caption("Search and apply filter conditions with operators and value suggestions.")
    return st.text_input("Search fields by name or cluster", key="criteria_search")


def render_field_cards_for_subgroup(subgroup: dict, search: str):
    visible_fields = []
    subgroup_label = subgroup["label"] if subgroup["label"] != "(no cluster)" else "Top-level fields"
    st.markdown(f"**{subgroup_label}**")
    for fld in subgroup["fields"]:
        hay = f"{fld['full_label']} {fld['label']} {subgroup['label']}".lower()
        if search and search.lower() not in hay:
            continue
        render_field_card(fld)
        visible_fields.append(fld)
    return visible_fields


def render_output_controls(output_defs, selected_labels):
    st.markdown("#### Output Selection")
    chosen = st.multiselect(
        "Choose output columns",
        [f["label"] for f in output_defs],
        default=selected_labels,
        help="Select output columns and reorder by reselecting in preferred sequence.",
    )
    sort_choices = {f["label"]: f["field_key"] for f in output_defs}
    sort_label = st.selectbox("Sort by", ["(none)"] + list(sort_choices.keys()), index=0)
    sort_dir = st.selectbox("Direction", ["asc", "desc"], index=0)
    return chosen, sort_label, sort_dir, sort_choices


def render_advanced_controls(current_advanced, default_semantics, default_slice, default_limit):
    st.markdown("#### Advanced Settings")
    st.caption("Tune execution behavior and matching semantics.")
    semantics = st.selectbox(
        "Repeated occurrence semantics",
        ["ALL", "ANY"],
        index=0 if current_advanced.get("occurrence_semantics", default_semantics) == "ALL" else 1,
        help="ALL = all occurrences must match, ANY = at least one occurrence must match.",
    )
    include_unknown = st.checkbox(
        "Include unknown (null_flavour) values",
        value=current_advanced.get("include_unknown", False),
        help="Include explicit unknown/null_flavour values in matches.",
    )
    slice_size = st.slider(
        "Slice size",
        min_value=10,
        max_value=10000,
        value=int(current_advanced.get("slice_size", default_slice)),
        step=10,
    )
    result_limit = st.slider(
        "Result limit",
        min_value=10,
        max_value=5000,
        value=int(current_advanced.get("result_limit", default_limit)),
        step=10,
    )
    return semantics, include_unknown, slice_size, result_limit


def render_preview_panel(criteria, outputs, sort_state, union, catalog, last_run_result):
    render_query_preview(criteria, outputs, sort_state, union, catalog, last_run_result)
