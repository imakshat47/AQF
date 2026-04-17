from __future__ import annotations

import pandas as pd
import streamlit as st

from components.metric_card import render_metric_card
from components.funnel_chart import render_funnel_chart
from components.results_table import render_results_table
from styles.design_tokens import COLORS


def calculate_match_percentage(matched: int, scanned: int) -> float:
    if scanned <= 0:
        return 0.0
    return 100.0 * matched / scanned


def render_results_dashboard(out: dict, display_df: pd.DataFrame | None) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Scanned", str(out.get("scanned", 0)), icon="🔍", color="#0066CC")
    with c2:
        render_metric_card("Matched", str(out.get("matched", 0)), icon="✅", color="#10B981")
    with c3:
        pct = calculate_match_percentage(out.get("matched", 0), out.get("scanned", 0))
        render_metric_card("Match %", f"{pct:.1f}%", icon="📈", color="#7C3AED")
    with c4:
        render_metric_card("Sec / doc", f"{out.get('sec_per_doc', 0.0):.6f}", icon="⏱️", color=COLORS["warning"])

    st.markdown("### Execution Funnel")
    render_funnel_chart(out.get("funnel", []))

    st.markdown("### Results Table")
    if display_df is not None:
        render_results_table(display_df)
