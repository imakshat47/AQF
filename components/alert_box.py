from __future__ import annotations

import streamlit as st

_ICONS = {
    "info": "ℹ️",
    "success": "✅",
    "warning": "⚠️",
    "error": "⛔",
}


def render_alert_box(message: str, kind: str = "info"):
    icon = _ICONS.get(kind, _ICONS["info"])
    st.markdown(
        f"<div class='aqf-alert aqf-alert-{kind}'>{icon} {message}</div>",
        unsafe_allow_html=True,
    )
