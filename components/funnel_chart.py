from __future__ import annotations

import pandas as pd
import streamlit as st


def render_funnel_chart(funnel):
    if not funnel:
        st.caption("No funnel data available.")
        return

    df = pd.DataFrame(funnel)
    st.bar_chart(df.set_index(df.columns[0]))
    st.dataframe(df, use_container_width=True)
