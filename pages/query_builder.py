from __future__ import annotations

import streamlit as st

from components.query_preview import render_query_preview


def render_query_builder_preview(criteria: list[dict], outputs: list[dict], sort_state: dict | None, groups_count: int, subgroups_count: int, fields_count: int, estimated_records: int | None = None) -> None:
    render_query_preview(
        criteria=criteria,
        outputs=outputs,
        sort_state=sort_state,
        schema_stats={"groups": groups_count, "subgroups": subgroups_count, "fields": fields_count},
        estimated_records=estimated_records,
    )


def render_query_builder_help() -> None:
    with st.expander("Query builder help", expanded=False):
        st.markdown("- Add filters in **Criteria**\n- Pick outputs and sort in **Output**\n- Configure semantics and limits in **Advanced**")
