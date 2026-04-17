"""Example usage patterns for AQF design system in Streamlit."""

from __future__ import annotations

import streamlit as st

from config import CUSTOM_CSS_FILE
from styles.design_tokens import COLOR_PALETTE, SPACING, TYPOGRAPHY
from utils.theme_manager import initialize_theme, inject_custom_css, inject_fonts, toggle_theme
from utils.ui_helpers import alert_box, chip, loading_indicator, metric_card, status_badge


def run_example_page():
    """Render a copy/paste-ready design-system demo."""
    st.set_page_config(page_title="AQF Design System Demo", layout="wide")

    initialize_theme()
    inject_fonts()
    inject_custom_css(CUSTOM_CSS_FILE)

    st.title("AQF Design System Example")
    st.caption("Use this page as a reference for consistent UI composition.")

    if st.button("Toggle theme"):
        toggle_theme()
        st.rerun()

    st.subheader("Design Tokens")
    st.code(
        f"Primary: {COLOR_PALETTE['primary']} | Base font size: {TYPOGRAPHY['font_sizes']['base']} | Space-4: {SPACING['4']}"
    )

    st.subheader("Common Components")
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("Scanned Records", "10,000", "Last run")
    with col2:
        status_badge("Ready", tone="success", icon="✅")
    with col3:
        chip("Age ≥ 65")

    alert_box("Schema cache is older than the current dataset.", tone="warning", title="Attention")
    loading_indicator("Building schema from dataset...")


if __name__ == "__main__":
    run_example_page()
