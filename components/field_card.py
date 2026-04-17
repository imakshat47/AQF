from __future__ import annotations

import streamlit as st


def render_field_card(field: dict):
    st.markdown(
        f"""
        <div class='aqf-field-card'>
          <div class='aqf-field-title'>{field.get('label', 'Field')} <span class='aqf-field-type'>({field.get('dv_type', 'UNKNOWN')})</span></div>
          <div class='aqf-field-path'>{field.get('full_label', '')}</div>
          <div class='aqf-field-meta'>Coverage: {field.get('coverage_ratio', 0):.1%} | Null %: {field.get('null_ratio', 0):.1%}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
