from __future__ import annotations

import streamlit as st


def render_metric_card(title: str, value, icon: str = "📊", tone: str = "neutral", caption: str | None = None):
    st.markdown(
        f"""
        <div class=\"aqf-metric-card aqf-metric-{tone}\">
          <div class=\"aqf-metric-icon\">{icon}</div>
          <div class=\"aqf-metric-title\">{title}</div>
          <div class=\"aqf-metric-value\">{value}</div>
          <div class=\"aqf-metric-caption\">{caption or ''}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
