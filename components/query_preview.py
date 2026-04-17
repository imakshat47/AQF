from __future__ import annotations

import streamlit as st

from ui_utils.ui_helpers import render_html, filter_chip_html


def render_query_preview(criteria: list[dict], outputs: list[dict], sort_state: dict | None, schema_stats: dict, estimated_records: int | None = None) -> None:
    st.markdown("<div class='aqf-card'>", unsafe_allow_html=True)
    st.markdown("<div class='aqf-panel-title'>Live Query Preview</div>", unsafe_allow_html=True)

    if criteria:
        render_html("".join(filter_chip_html(f"{c.get('element_name', 'Field')} {c.get('operator', '')} {c.get('value', '')}") for c in criteria[:8]))
    else:
        st.caption("No active filters")

    st.markdown(f"**Selected outputs:** {len(outputs)}")
    st.markdown(f"**Sort:** {(sort_state or {}).get('element_name', '(none)')} {(sort_state or {}).get('direction', '')}")
    st.markdown(
        f"**Schema:** {schema_stats.get('groups', 0)} groups · {schema_stats.get('subgroups', 0)} clusters · {schema_stats.get('fields', 0)} fields"
    )
    if estimated_records is not None:
        st.markdown(f"**Estimated matches:** {estimated_records}")

    completion = min(100, (30 if criteria else 0) + (30 if outputs else 0) + (20 if sort_state else 0) + 20)
    st.progress(completion / 100.0, text=f"Query completeness: {completion}%")
    st.markdown("</div>", unsafe_allow_html=True)
