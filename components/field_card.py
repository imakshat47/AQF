from __future__ import annotations

import streamlit as st


def render_field_card(field: dict) -> None:
    label = field.get("label") or field.get("element_name") or "Field"
    dv_type = field.get("dv_type", "unknown")
    cluster = field.get("cluster_path_str") or "Top-level"
    suggestions = field.get("suggested_values", [])

    st.markdown("<div class='aqf-card'>", unsafe_allow_html=True)
    st.markdown(f"**{label}** · `{dv_type}`")
    st.caption(cluster)
    if suggestions:
        st.caption("Suggestions: " + ", ".join(str(s) for s in suggestions[:5]))
    st.markdown("</div>", unsafe_allow_html=True)
