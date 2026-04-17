"""Reusable UI helper components for AQF Streamlit screens."""

from __future__ import annotations

from html import escape
from typing import Optional

import streamlit as st

from styles.design_tokens import COLOR_PALETTE
from utils.theme_manager import css_class, unsafe_markdown, with_opacity


_STATUS_TONE = {
    "success": "aqf-badge--success",
    "warning": "aqf-badge--warning",
    "danger": "aqf-badge--danger",
    "info": "aqf-badge--info",
}


def status_badge(text: str, tone: str = "info", icon: str = ""):
    """Render a styled status badge."""
    badge_class = css_class("aqf-badge", _STATUS_TONE.get(tone, "aqf-badge--info"))
    prefix = f"{escape(icon)} " if icon else ""
    unsafe_markdown(f'<span class="{badge_class}">{prefix}{escape(text)}</span>')


def metric_card(title: str, value: str, subtitle: Optional[str] = None, tone: str = "primary"):
    """Render a metric card with optional subtitle."""
    color = COLOR_PALETTE.get(tone, COLOR_PALETTE["primary"])
    border = with_opacity(color, 0.3)
    html = f"""
    <div class="aqf-card aqf-animate-in" style="border-left:4px solid {color}; border-color:{border};">
      <div style="font-size:12px; color:var(--aqf-color-text-muted);">{escape(title)}</div>
      <div style="font-size:24px; font-weight:700; margin-top:4px;">{escape(str(value))}</div>
      {f'<div style="font-size:12px; margin-top:4px; color:var(--aqf-color-text-muted);">{escape(subtitle)}</div>' if subtitle else ''}
    </div>
    """
    unsafe_markdown(html)


def loading_indicator(label: str = "Loading..."):
    """Render lightweight animated loading indicator."""
    unsafe_markdown(
        f'<div class="aqf-loading" style="font-weight:600;">⏳ {escape(label)}</div>'
    )


def alert_box(message: str, tone: str = "info", title: Optional[str] = None):
    """Render a styled alert box."""
    tone_color = {
        "success": COLOR_PALETTE["success"],
        "warning": COLOR_PALETTE["warning"],
        "danger": COLOR_PALETTE["danger"],
        "info": COLOR_PALETTE["primary"],
    }.get(tone, COLOR_PALETTE["primary"])

    heading = f"<strong>{escape(title)}</strong><br>" if title else ""
    unsafe_markdown(
        f'<div class="aqf-alert" style="border-left-color:{tone_color};">{heading}{escape(message)}</div>'
    )


def sidebar_badge(text: str, tone: str = "info"):
    """Render a compact badge in sidebar."""
    badge_class = css_class("aqf-badge", _STATUS_TONE.get(tone, "aqf-badge--info"))
    st.sidebar.markdown(f'<span class="{badge_class}">{escape(text)}</span>', unsafe_allow_html=True)


def chip(label: str):
    """Render chip/tag component."""
    unsafe_markdown(f'<span class="aqf-chip">{escape(label)}</span>')


def status_indicator(text: str, status: str = "info"):
    """Render semantic status indicator with icon and badge styling."""
    icons = {
        "success": "✅",
        "warning": "⚠️",
        "danger": "❌",
        "info": "ℹ️",
    }
    status_badge(text=text, tone=status, icon=icons.get(status, "ℹ️"))
