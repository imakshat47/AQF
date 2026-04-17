"""Theme management helpers for AQF Streamlit UI."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from styles.design_tokens import css_variables


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def rgba(hex_color: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(hex_color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def initialize_theme_state(default_mode: str = "light") -> str:
    if "theme_mode" not in st.session_state:
        st.session_state.theme_mode = default_mode
    return st.session_state.theme_mode


def toggle_theme() -> str:
    initialize_theme_state()
    st.session_state.theme_mode = "dark" if st.session_state.theme_mode == "light" else "light"
    return st.session_state.theme_mode


def css_class(*class_names: str) -> str:
    return " ".join(c for c in class_names if c)


def inject_design_system(css_path: str | Path = "styles/custom.css") -> None:
    mode = initialize_theme_state()
    vars_map = css_variables(mode)
    var_block = ":root{" + "".join(f"{k}:{v};" for k, v in vars_map.items()) + "}"

    css_text = Path(css_path).read_text(encoding="utf-8")
    st.markdown(f"<style>{var_block}\n{css_text}</style>", unsafe_allow_html=True)


def safe_html(html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)
