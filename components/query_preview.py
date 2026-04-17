from __future__ import annotations

import streamlit as st


def render_query_preview(criteria, outputs, sort_state, union, catalog, last_run_result=None):
    st.markdown("### Live Preview")
    st.markdown(f"- Active filters: **{len(criteria)}**")
    st.markdown(f"- Selected output fields: **{len(outputs)}**")
    st.markdown(f"- Sort: **{sort_state.get('element_name', 'None') if sort_state else 'None'}**")
    st.markdown(f"- Entry groups: **{len(union.get('groups', {}))}**")
    st.markdown(f"- Catalog fields: **{len(catalog)}**")

    if criteria:
        st.markdown("**Filters:**")
        for c in criteria[:8]:
            st.write(f"• {c.get('element_name', 'Field')} [{c.get('operator', '')}] {c.get('value', '')}")

    if last_run_result:
        st.metric("Estimated records matching", last_run_result.get("matched", 0))
    else:
        st.caption("Run query to see match estimates.")
