from __future__ import annotations

import pandas as pd
import streamlit as st

from components.funnel_chart import render_funnel_chart
from components.metric_card import render_metric_card
from components.results_table import render_results_table


def render_results_dashboard(out: dict, query_summary_markdown: str, display_df: pd.DataFrame | None, source_df: pd.DataFrame | None):
    st.markdown("### Results Dashboard")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_metric_card("Scanned", out.get("scanned", 0), icon="🔎", tone="neutral")
    with m2:
        render_metric_card("Matched", out.get("matched", 0), icon="✅", tone="neutral")
    with m3:
        pct = 0.0
        if out.get("scanned", 0):
            pct = (out.get("matched", 0) / out.get("scanned", 1)) * 100
        render_metric_card("Match %", f"{pct:.2f}%", icon="📈", tone="neutral")
    with m4:
        render_metric_card("Sec / doc", f"{out.get('sec_per_doc', 0.0):.6f}", icon="⏱️", tone="neutral")

    st.markdown("#### Query Summary")
    st.markdown(query_summary_markdown)

    st.markdown("#### Execution Funnel")
    render_funnel_chart(out.get("funnel", []))

    st.markdown("#### Results Table")
    if display_df is not None and not display_df.empty:
        render_results_table(display_df)
    else:
        st.info("No matches found.")

    if source_df is not None and not source_df.empty:
        with st.expander("Source file mapping", expanded=False):
            st.dataframe(source_df, use_container_width=True)
