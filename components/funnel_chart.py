from __future__ import annotations

import pandas as pd
import streamlit as st


def render_funnel_chart(funnel: list[dict]) -> None:
    if not funnel:
        st.caption("No funnel data available.")
        return

    df = pd.DataFrame(funnel)
    show_chart = False
    if {"step", "remaining"}.issubset(df.columns):
        if df["step"].duplicated().any():
            st.caption("Funnel step labels are not unique; showing table view only.")
        else:
            st.bar_chart(df.set_index("step")["remaining"])
            show_chart = True
    elif len(df.columns) >= 2:
        index_col = df.columns[0]
        value_col = df.columns[1]
        if df[index_col].duplicated().any():
            st.caption("Funnel labels are not unique; showing table view only.")
        else:
            st.bar_chart(df.set_index(index_col)[value_col])
            show_chart = True
    else:
        st.caption("Funnel data format not supported.")

    if show_chart:
        st.caption("Funnel progression")
    st.dataframe(df, use_container_width=True)
