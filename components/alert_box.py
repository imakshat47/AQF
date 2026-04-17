from __future__ import annotations

import streamlit as st

from ui_utils.ui_helpers import alert_box_html


def render_alert_box(message: str, alert_type: str = "info") -> None:
    st.markdown(alert_box_html(message, alert_type=alert_type), unsafe_allow_html=True)
