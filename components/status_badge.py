from __future__ import annotations

import streamlit as st

_STATUS_CLASS = {
    "ready": "aqf-badge-ready",
    "processing": "aqf-badge-processing",
    "error": "aqf-badge-error",
    "outdated": "aqf-badge-outdated",
    "neutral": "aqf-badge-neutral",
}


def render_status_badge(label: str, status: str = "neutral"):
    css_class = _STATUS_CLASS.get(status, _STATUS_CLASS["neutral"])
    st.markdown(
        f'<span class="aqf-badge {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )
