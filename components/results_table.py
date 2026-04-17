from __future__ import annotations

import streamlit as st
import pandas as pd


def render_results_table(df: pd.DataFrame, key_prefix: str = "results") -> None:
    if df.empty:
        st.info("No matches found.")
        return

    with st.expander("Table options", expanded=False):
        page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1, key=f"{key_prefix}_page_size")
        show_source = st.checkbox("Show source mapping", value=False, key=f"{key_prefix}_source")

    start = st.number_input("Start row", min_value=0, max_value=max(len(df) - 1, 0), value=0, step=page_size, key=f"{key_prefix}_start")
    page_df = df.iloc[int(start): int(start) + int(page_size)]

    st.dataframe(page_df, use_container_width=True)
    if show_source and "_source_file" in df.columns:
        st.dataframe(df[[c for c in ["Record", "_source_file"] if c in df.columns]], use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.download_button("Export CSV", data=df.to_csv(index=False), file_name="aqf_results.csv", mime="text/csv")
    with c2:
        st.download_button("Export JSON", data=df.to_json(orient="records", indent=2), file_name="aqf_results.json", mime="application/json")
