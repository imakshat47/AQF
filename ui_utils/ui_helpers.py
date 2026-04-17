"""Reusable UI helper primitives for AQF components."""

from __future__ import annotations

from html import escape

import streamlit as st

STATUS_STYLES = {
    "ready": ("✅", "#10B981"),
    "loading": ("⏳", "#0066CC"),
    "error": ("❌", "#EF4444"),
    "outdated": ("⚠️", "#F59E0B"),
}


def join_classes(*names: str) -> str:
    return " ".join(n for n in names if n)


def status_badge_html(status: str, label: str | None = None) -> str:
    icon, color = STATUS_STYLES.get(status, ("ℹ️", "#6B7280"))
    text = label or status.title()
    return (
        f"<span class='aqf-badge' style='background:{color}1A;border-color:{color}66;'>"
        f"<span>{icon}</span><span>{escape(text)}</span></span>"
    )


def metric_card_html(label: str, value: str, icon: str = "📊", color: str = "#0066CC") -> str:
    return (
        f"<div class='aqf-metric' style='border-left:4px solid {color};'>"
        f"<div style='font-size:12px;color:var(--aqf-muted-text)'>{escape(icon)} {escape(label)}</div>"
        f"<div style='font-size:28px;font-weight:700'>{escape(str(value))}</div></div>"
    )


def alert_box_html(message: str, alert_type: str = "info") -> str:
    color = {
        "info": "#0066CC",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
    }.get(alert_type, "#0066CC")
    return f"<div class='aqf-alert' style='border-left-color:{color}'>{escape(message)}</div>"


def filter_chip_html(label: str) -> str:
    return f"<span class='aqf-chip'>{escape(label)}</span>"


def loading_spinner(text: str = "Loading...") -> None:
    with st.spinner(text):
        st.write("")


def render_html(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)
