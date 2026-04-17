from __future__ import annotations

import streamlit as st

from ui_utils.ui_helpers import metric_card_html


def render_metric_card(label: str, value: str, icon: str = "📊", color: str = "#0066CC") -> None:
    st.markdown(metric_card_html(label, value, icon=icon, color=color), unsafe_allow_html=True)
