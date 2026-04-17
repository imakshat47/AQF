"""Theme management helpers for AQF Streamlit UI."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Tuple

import streamlit as st

from styles.design_tokens import THEME_COLORS, as_css_variables


THEME_STATE_KEY = "aqf_theme_mode"


def initialize_theme(default_theme: str = "light") -> str:
    """Initialize theme state and return active mode."""
    if default_theme not in THEME_COLORS:
        default_theme = "light"
    if THEME_STATE_KEY not in st.session_state:
        st.session_state[THEME_STATE_KEY] = default_theme
    return st.session_state[THEME_STATE_KEY]


def get_theme() -> str:
    """Return current theme mode."""
    return st.session_state.get(THEME_STATE_KEY, "light")


def set_theme(theme: str) -> str:
    """Set and return a valid theme mode."""
    selected = theme if theme in THEME_COLORS else "light"
    st.session_state[THEME_STATE_KEY] = selected
    return selected


def toggle_theme() -> str:
    """Toggle between light and dark themes."""
    current = get_theme()
    return set_theme("dark" if current == "light" else "light")


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert #RRGGBB or #RGB hex into RGB tuple."""
    value = hex_color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return red, green, blue


def with_opacity(hex_color: str, alpha: float) -> str:
    """Convert hex + alpha to rgba() string."""
    alpha_clamped = max(0.0, min(1.0, alpha))
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha_clamped:.3f})"


def css_class(*parts: str) -> str:
    """Join non-empty CSS class name parts."""
    return " ".join(part.strip() for part in parts if part and part.strip())


def inject_theme_variables(theme: str | None = None):
    """Inject runtime CSS variables for the selected theme."""
    selected = theme or get_theme()
    style = f"<style>:root {{{as_css_variables(selected)}}}</style>"
    st.markdown(style, unsafe_allow_html=True)


def inject_fonts():
    """Inject web font links for design system typography."""
    st.markdown(
        """
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Poppins:wght@500;600;700&family=Roboto:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )


def inject_custom_css(css_path: str | Path):
    """Load and inject CSS file into Streamlit app."""
    css_file = Path(css_path)
    if not css_file.exists():
        return
    st.markdown(f"<style>{css_file.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def initialize_ui(css_path: str | Path):
    """Initialize theme, fonts, and styles in one call."""
    initialize_theme()
    inject_theme_variables()
    inject_fonts()
    inject_custom_css(css_path)


def safe_html(content: str) -> str:
    """Escape potentially unsafe HTML content."""
    return escape(content, quote=True)


def unsafe_markdown(content: str):
    """Render explicitly trusted HTML content."""
    st.markdown(content, unsafe_allow_html=True)
