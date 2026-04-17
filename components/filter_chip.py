from __future__ import annotations

import streamlit as st


def render_filter_chip(label: str):
    st.markdown(f"<span class='aqf-chip'>{label}</span>", unsafe_allow_html=True)


def render_filter_chips(criteria, outputs, sort_state):
    chips = []
    for c in criteria[:6]:
        chips.append(f"{c.get('element_name', 'Field')} {c.get('operator', '')} {c.get('value', '')}")
    for o in outputs[:6]:
        chips.append(f"Output: {o.get('element_name', o.get('name', 'Field'))}")
    if sort_state:
        chips.append(f"Sort: {sort_state.get('element_name', 'Field')} ({sort_state.get('direction', 'asc')})")

    if not chips:
        st.caption("No active query settings yet.")
        return

    html = "".join([f"<span class='aqf-chip'>{chip}</span>" for chip in chips])
    st.markdown(f"<div class='aqf-chip-wrap'>{html}</div>", unsafe_allow_html=True)
