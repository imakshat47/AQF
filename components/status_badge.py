from __future__ import annotations

import streamlit as st

from ui_utils.ui_helpers import status_badge_html


def render_status_badge(status: str, label: str | None = None) -> None:
    st.markdown(status_badge_html(status, label), unsafe_allow_html=True)
