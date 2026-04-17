from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from components.status_badge import render_status_badge


def render_header(dataset_folder: str, composition_archetype: str, built_at: str | None, record_count: int, on_refresh: Callable[[], None], on_reset_filters: Callable[[], None], on_reset_outputs: Callable[[], None], on_toggle_theme: Callable[[], None]) -> None:
    st.markdown("<div class='aqf-header'>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns([2.6, 1.4, 1.2, 1.2])

    with c1:
        st.markdown("## 🏥 AQF Query Builder")
        st.caption("Professional healthcare query composition interface")
        st.caption(f"Dataset: `{dataset_folder}`")
        st.caption(f"Composition: `{composition_archetype}`")

    with c2:
        render_status_badge("ready", "Schema ready" if built_at else "Schema pending")
        if built_at:
            st.caption(f"Built: {built_at}")
        st.caption(f"Records: {record_count}")

    with c3:
        if st.button("🔄 Refresh", key="header_refresh"):
            on_refresh()
        if st.button("🧹 Reset Filters", key="header_reset_filters"):
            on_reset_filters()

    with c4:
        if st.button("↺ Reset Output", key="header_reset_outputs"):
            on_reset_outputs()
        if st.button("🌓 Theme", key="header_theme"):
            on_toggle_theme()

    st.markdown("<small>Home / Query Builder / Results</small>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
