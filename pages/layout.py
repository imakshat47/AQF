from __future__ import annotations

from pathlib import Path

import streamlit as st

DESIGN_TOKENS = {
    "radius": "12px",
    "space_sm": "8px",
    "space_md": "16px",
    "space_lg": "24px",
    "shadow": "0 6px 18px rgba(0, 0, 0, 0.08)",
    "primary": "#2563eb",
    "success": "#16a34a",
    "warning": "#d97706",
    "error": "#dc2626",
}


def initialize_theme_manager():
    if "aqf_theme_mode" not in st.session_state:
        st.session_state.aqf_theme_mode = "auto"


def apply_design_system():
    st.session_state["aqf_design_tokens"] = DESIGN_TOKENS
    css = f"""
    <style>
    .stApp {{ padding-top: 0.5rem; }}
    .aqf-sticky-header {{
        position: sticky;
        top: 0;
        z-index: 100;
        background: var(--background-color);
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: {DESIGN_TOKENS['radius']};
        padding: {DESIGN_TOKENS['space_md']};
        margin-bottom: {DESIGN_TOKENS['space_lg']};
        box-shadow: {DESIGN_TOKENS['shadow']};
    }}
    .aqf-section {{
        border: 1px solid rgba(128,128,128,0.2);
        border-radius: {DESIGN_TOKENS['radius']};
        padding: {DESIGN_TOKENS['space_md']};
        margin-bottom: {DESIGN_TOKENS['space_md']};
        background: #f8fbff;
        background: color-mix(in srgb, var(--background-color) 94%, var(--primary-color) 6%);
    }}
    .aqf-badge {{
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 600;
        margin-bottom: 6px;
    }}
    .aqf-badge-ready {{ background: #dcfce7; color: #166534; }}
    .aqf-badge-processing {{ background: #dbeafe; color: #1d4ed8; }}
    .aqf-badge-error {{ background: #fee2e2; color: #991b1b; }}
    .aqf-badge-outdated {{ background: #fef3c7; color: #92400e; }}
    .aqf-badge-neutral {{ background: #e5e7eb; color: #374151; }}
    .aqf-chip-wrap {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; }}
    .aqf-chip {{
        background: #dbeafe;
        color: #1e3a8a;
        border-radius: 999px;
        padding: 4px 10px;
        font-size: 12px;
        border: 1px solid #bfdbfe;
    }}
    .aqf-alert {{ border-radius: 10px; padding: 10px 12px; margin: 8px 0; border: 1px solid transparent; }}
    .aqf-alert-info {{ background: #eff6ff; border-color: #bfdbfe; }}
    .aqf-alert-success {{ background: #ecfdf5; border-color: #86efac; }}
    .aqf-alert-warning {{ background: #fffbeb; border-color: #fcd34d; }}
    .aqf-alert-error {{ background: #fef2f2; border-color: #fca5a5; }}
    .aqf-metric-card {{
      border: 1px solid rgba(128,128,128,0.2);
      border-radius: 12px;
      padding: 12px;
      margin-bottom: 10px;
      background: var(--background-color);
    }}
    .aqf-metric-title {{ font-size: 13px; opacity: 0.8; }}
    .aqf-metric-value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
    .aqf-metric-icon {{ font-size: 18px; }}
    .aqf-field-card {{ border: 1px solid rgba(128,128,128,0.25); border-radius: 10px; padding: 10px; margin: 8px 0; }}
    .aqf-field-title {{ font-weight: 700; }}
    .aqf-field-type {{ opacity: 0.7; font-weight: 500; }}
    .aqf-field-path, .aqf-field-meta {{ font-size: 12px; opacity: 0.8; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def section_open(title: str):
    st.markdown("<div class='aqf-section'>", unsafe_allow_html=True)
    st.markdown(f"### {title}")


def section_close():
    st.markdown("</div>", unsafe_allow_html=True)
