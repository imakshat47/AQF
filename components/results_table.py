from __future__ import annotations

import json
import pandas as pd
import streamlit as st


def render_results_table(display_df: pd.DataFrame, key_prefix: str = "results"):
    if display_df.empty:
        st.info("No rows to display.")
        return

    page_size = st.selectbox("Rows per page", [10, 25, 50, 100], index=1, key=f"{key_prefix}_page_size")
    total_rows = len(display_df)
    max_page = max(1, (total_rows - 1) // page_size + 1)
    page_key = f"{key_prefix}_page"
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    if st.session_state[page_key] > max_page:
        st.session_state[page_key] = max_page
    page = st.number_input("Page", min_value=1, max_value=max_page, step=1, key=page_key)

    start = (page - 1) * page_size
    end = min(start + page_size, total_rows)

    st.dataframe(display_df.iloc[start:end], use_container_width=True)

    csv_data = display_df.to_csv(index=False).encode("utf-8")
    json_data = json.dumps(display_df.to_dict(orient="records"), ensure_ascii=False, indent=2).encode("utf-8")

    c1, c2 = st.columns(2)
    c1.download_button("Export CSV", data=csv_data, file_name="aqf_results.csv", mime="text/csv")
    c2.download_button("Export JSON", data=json_data, file_name="aqf_results.json", mime="application/json")
