from __future__ import annotations

import streamlit as st

from ui_utils.ui_helpers import filter_chip_html


def render_filter_chip(label: str) -> None:
    st.markdown(filter_chip_html(label), unsafe_allow_html=True)
