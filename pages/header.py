from __future__ import annotations

import streamlit as st

from components.status_badge import render_status_badge


def render_header(dataset_folder: str, comp_arch: str, record_count: int, built_at: str | None):
    st.markdown("<div class='aqf-sticky-header'>", unsafe_allow_html=True)

    left, middle, right = st.columns([3, 5, 3])
    with left:
        st.markdown("## 🏥 AQF - openEHR Query Studio")

    with middle:
        st.caption(f"Dataset: `{dataset_folder}`")
        st.caption(f"Composition: `{comp_arch}` | Records: **{record_count}**")

    with right:
        if built_at:
            render_status_badge(f"Schema ready ({built_at})", "ready")
        else:
            render_status_badge("Schema state unknown", "outdated")

    st.markdown("</div>", unsafe_allow_html=True)
