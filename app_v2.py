# app_v2.py
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

import config as app_config

from composition_loader import group_docs_by_composition_archetype
from schema_union_builder import build_union_schema
from field_catalog import build_field_catalog
from form_definition_builder import build_form_definition
from query_compiler import compile_query
from query_executor import run_query
from result_formatter import format_results_for_display
from schema_diagram import build_schema_flow_dot, build_touched_query_dot
from query_summary import build_query_summary_markdown

# ============================================================
# Config with safe fallbacks
# ============================================================
DATA_DIR = getattr(app_config, "DATA_DIR", Path("data"))
CACHE_DIR = getattr(app_config, "CACHE_DIR", Path(".cache"))
SCHEMA_UNION_FILE = getattr(app_config, "SCHEMA_UNION_FILE", CACHE_DIR / "schema_union.json")
FIELDS_FILE = getattr(app_config, "FIELDS_FILE", CACHE_DIR / "fields.json")

DEFAULT_SLICE_SIZE = getattr(app_config, "DEFAULT_SLICE_SIZE", 200)
DEFAULT_RESULT_LIMIT = getattr(app_config, "DEFAULT_RESULT_LIMIT", 100)
DEFAULT_OCCURRENCE_SEMANTICS = getattr(app_config, "DEFAULT_OCCURRENCE_SEMANTICS", "ALL")

SCHEMA_OVERVIEW_MAX_DEPTH = getattr(app_config, "SCHEMA_OVERVIEW_MAX_DEPTH", 4)
SCHEMA_GRAPH_DIRECTION = getattr(app_config, "SCHEMA_GRAPH_DIRECTION", "LR")
SCHEMA_LEAF_LIMIT = getattr(app_config, "SCHEMA_LEAF_LIMIT", 5)

st.set_page_config(page_title="AQF", layout="wide")

SCHEMA_META_FILE = CACHE_DIR / "schema_metadata.json"

# ============================================================
# Minimal AQF product styling
# ============================================================
AQF_CSS = """
<style>
:root{
  --bg:#F8FAFC;
  --surface:#FFFFFF;
  --panel:#F1F5F9;
  --border:#E2E8F0;

  --text:#0F172A;
  --soft:#334155;
  --muted:#64748B;

  --blue:#2563EB;
  --blue-soft:#DBEAFE;

  --green-soft:#DCFCE7;
  --amber-soft:#FEF3C7;
  --red-soft:#FEE2E2;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg);
  color: var(--text);
}

[data-testid="stHeader"] {
  background: transparent;
}

[data-testid="stSidebar"] {
  background: var(--surface);
  border-right: 1px solid var(--border);
}

.aqf-card,
.aqf-warning,
.aqf-empty,
.aqf-success,
.aqf-record,
.aqf-summary {
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 12px;
  background: var(--surface);
}

.aqf-warning {
  background: var(--amber-soft);
  border-color: #FCD34D;
}

.aqf-empty {
  background: var(--red-soft);
  border-color: #FCA5A5;
}

.aqf-success {
  background: var(--green-soft);
  border-color: #86EFAC;
}

.aqf-sticky-summary {
  position: sticky;
  top: 0.5rem;
  z-index: 999;
  background: rgba(248, 250, 252, 0.94);
  backdrop-filter: blur(6px);
  padding-top: 4px;
  padding-bottom: 6px;
}

.aqf-summary {
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.aqf-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
}

.aqf-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.aqf-value {
  font-size: 14px;
  color: var(--soft);
}

.aqf-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--blue-soft);
  border: 1px solid #BFDBFE;
  color: #1D4ED8;
  font-size: 12px;
  font-weight: 600;
  margin: 4px 6px 0 0;
}

.aqf-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 999px;
  background: var(--green-soft);
  color: #166534;
  border: 1px solid #86EFAC;
}

.aqf-record-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-baseweb="textarea"] > div {
  border-radius: 10px !important;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: 14px;
  overflow: hidden;
}
</style>
"""
st.markdown(AQF_CSS, unsafe_allow_html=True)

# ============================================================
# Generic helpers
# ============================================================
def save_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def do_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

def dataset_signature(folder: str) -> str:
    p = Path(folder)
    if not p.exists():
        return ""
    parts = []
    for fp in sorted([x for x in p.iterdir() if x.suffix.lower() == ".json"]):
        stat = fp.stat()
        parts.append(f"{fp.name}|{stat.st_size}|{int(stat.st_mtime)}")
    return hashlib.md5("\n".join(parts).encode("utf-8")).hexdigest()

def save_schema_metadata(dataset_folder: str, comp_arch: str, built_at: str):
    save_json(
        {
            "dataset_folder": dataset_folder,
            "dataset_signature": dataset_signature(dataset_folder),
            "composition_archetype": comp_arch,
            "built_at": built_at,
        },
        SCHEMA_META_FILE,
    )

def load_schema_metadata():
    return load_json(SCHEMA_META_FILE) if SCHEMA_META_FILE.exists() else None

def normalize_graph_direction(direction: str) -> str:
    return direction if direction in {"LR", "TB", "RL", "BT"} else "LR"

def display_cluster_label(cluster_path_str: str) -> str:
    return "Top-level fields" if not cluster_path_str or cluster_path_str == "(no cluster)" else cluster_path_str

def signature_of_state(criteria, output_fields, sort_state, advanced):
    raw = json.dumps(
        {
            "criteria": criteria,
            "output_fields": output_fields,
            "sort": sort_state,
            "advanced": advanced,
        },
        sort_keys=True,
        ensure_ascii=False,
        default=str,
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def count_summary(union, catalog):
    groups = len(union.get("groups", {}))
    subgroups = sum(len(g["subgroups"]) for g in union.get("groups", {}).values())
    fields = len(catalog)
    suggestion_fields = sum(1 for f in catalog if f.get("suggested_values"))
    null_fields = sum(1 for f in catalog if f.get("has_null_flavour"))
    return groups, subgroups, fields, suggestion_fields, null_fields

# ============================================================
# UI helpers
# ============================================================
def render_brand():
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
            <div style="
                width:36px;height:36px;border-radius:10px;
                background:#DBEAFE;display:flex;align-items:center;justify-content:center;
                color:#1D4ED8;font-weight:700;">AQ</div>
            <div>
                <div style="font-size:20px;font-weight:700;color:#0F172A;">AQF</div>
                <div style="font-size:12px;color:#64748B;">Adaptive Query Forms</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def clean_query_summary(summary_md: str) -> str:
    text = summary_md.strip()
    if text.startswith(">"):
        text = text[1:].strip()
    text = text.replace("**Query summary.**", "Query summary.")
    text = text.replace("**Query summary:**", "Query summary:")
    text = text.replace("**", "")
    text = " ".join(text.split())
    return text

def render_summary(summary_md: str):
    text = clean_query_summary(summary_md)
    st.markdown(
        f"""
        <div class="aqf-sticky-summary">
            <div class="aqf-summary">
                <div class="aqf-label">Current search</div>
                <div class="aqf-value" style="margin-top:6px;">{text}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_quick_chips(items: list[str]):
    if not items:
        return
    st.markdown(
        "".join(f'<span class="aqf-chip">{item}</span>' for item in items),
        unsafe_allow_html=True,
    )

def card(title: str, body: str, tone: str = "default"):
    cls = {
        "default": "aqf-card",
        "warning": "aqf-warning",
        "empty": "aqf-empty",
        "success": "aqf-success",
    }.get(tone, "aqf-card")
    st.markdown(
        f"""
        <div class="{cls}">
            <div class="aqf-title">{title}</div>
            <div class="aqf-value">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def result_card(title: str, key_fields: list[tuple[str, str]], why: list[str] | None = None):
    fields_html = "".join(
        f"""
        <div style="margin-bottom:10px;">
            <div class="aqf-label">{k}</div>
            <div class="aqf-value">{v}</div>
        </div>
        """
        for k, v in key_fields
    )
    why_html = ""
    if why:
        why_html = """
        <div style="margin-top:12px;">
            <div class="aqf-label">Why this matched</div>
            <ul style="margin-top:6px;padding-left:18px;color:#334155;">
        """ + "".join(f"<li>{x}</li>" for x in why) + "</ul></div>"

    st.markdown(
        f"""
        <div class="aqf-record">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <div class="aqf-record-title">{title}</div>
                <span class="aqf-badge">Matched</span>
            </div>
            {fields_html}
            {why_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# Session state
# ============================================================
def initialize_state():
    defaults = {
        "schema_build_token": 0,
        "cached_schema_bundle": None,
        "dataset_folder_input": str(DATA_DIR),
        "cache_auto_load_attempted": False,

        "active_criteria": [],
        "active_output": [],
        "active_advanced": {
            "occurrence_semantics": DEFAULT_OCCURRENCE_SEMANTICS,
            "include_unknown": False,
            "slice_size": DEFAULT_SLICE_SIZE,
            "result_limit": DEFAULT_RESULT_LIMIT,
        },
        "sort_state": None,
        "active_query_plan": None,

        "full_result": None,
        "last_run_signature": None,

        "result_view_mode": "Cards",
        "card_offset": 0,
        "table_limit": 25,

        "expert_mode": False,
        "show_funnel_panel": False,
        "show_explain_panel": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

initialize_state()

# ============================================================
# Widget sync helpers
# ============================================================
def sync_result_view_from_sidebar():
    st.session_state.result_view_mode = st.session_state.sidebar_result_view_mode
    if "results_result_view_mode" in st.session_state:
        st.session_state.results_result_view_mode = st.session_state.sidebar_result_view_mode

def sync_result_view_from_results():
    st.session_state.result_view_mode = st.session_state.results_result_view_mode
    if "sidebar_result_view_mode" in st.session_state:
        st.session_state.sidebar_result_view_mode = st.session_state.results_result_view_mode

# ============================================================
# Schema/cache handling
# ============================================================
def load_cached_schema_bundle():
    if not SCHEMA_UNION_FILE.exists() or not FIELDS_FILE.exists():
        return None, False

    try:
        union = load_json(SCHEMA_UNION_FILE)
        catalog = load_json(FIELDS_FILE)
        form = build_form_definition(union, catalog)
    except Exception:
        return None, False

    meta = load_schema_metadata()
    built_at = meta.get("built_at") if meta else None
    comp_arch = union.get("composition_archetype", "UNKNOWN_COMPOSITION")

    validated = False
    if meta and meta.get("dataset_folder") == st.session_state.dataset_folder_input.strip():
        validated = meta.get("dataset_signature") == dataset_signature(st.session_state.dataset_folder_input.strip())

    return {
        "composition_archetype": comp_arch,
        "union": union,
        "catalog": catalog,
        "form": form,
        "built_at": built_at,
    }, validated

@st.cache_data(show_spinner=False)
def cached_build_from_dataset(data_dir: str, schema_build_token: int):
    valid_groups, skipped = group_docs_by_composition_archetype(Path(data_dir))
    if not valid_groups:
        return None, skipped, []

    comp_arch = max(valid_groups.items(), key=lambda item: len(item[1]))[0]
    docs_only = [d for _, d in valid_groups[comp_arch]]

    union = build_union_schema(docs_only)
    catalog = build_field_catalog(union)
    form = build_form_definition(union, catalog)

    return {
        "composition_archetype": comp_arch,
        "union": union,
        "catalog": catalog,
        "form": form,
    }, skipped, list(valid_groups.keys())

def build_or_refresh_schema():
    built, skipped, _ = cached_build_from_dataset(
        st.session_state.dataset_folder_input.strip(),
        st.session_state.schema_build_token,
    )
    if not built:
        st.error("No valid composition files found in the dataset folder.")
        return

    save_json(built["union"], SCHEMA_UNION_FILE)
    save_json(built["catalog"], FIELDS_FILE)

    built_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_schema_metadata(
        st.session_state.dataset_folder_input.strip(),
        built["composition_archetype"],
        built_at,
    )

    st.session_state.cached_schema_bundle = {**built, "built_at": built_at}

def resolve_runtime_files_for_query(dataset_folder: str, composition_archetype: str):
    valid_groups, skipped = group_docs_by_composition_archetype(Path(dataset_folder))
    return [p for p, _ in valid_groups.get(composition_archetype, [])], skipped, valid_groups

# ============================================================
# AQF form/query helpers
# ============================================================
def get_field_by_key(catalog, field_key: str):
    return next((f for f in catalog if f["field_key"] == field_key), None)

def enrich_criteria(items, catalog):
    out = []
    for c in items:
        f = get_field_by_key(catalog, c["field_key"])
        if f:
            out.append({
                **c,
                "entry_name": f["entry_name"],
                "cluster_path_str": f["cluster_path_str"],
                "element_name": f["element_name"],
                "dv_type": f["dv_type"],
            })
        else:
            out.append(c)
    return out

def enrich_outputs(items, catalog):
    out = []
    for o in items:
        f = get_field_by_key(catalog, o["field_key"])
        if f:
            out.append({
                **o,
                "entry_name": f["entry_name"],
                "cluster_path_str": f["cluster_path_str"],
                "element_name": f["element_name"],
                "name": f["label"],
                "dv_type": f["dv_type"],
            })
        else:
            out.append(o)
    return out

def enrich_sort(sort_state, catalog):
    if not sort_state:
        return None
    f = get_field_by_key(catalog, sort_state["field_key"])
    if f:
        return {
            **sort_state,
            "entry_name": f["entry_name"],
            "cluster_path_str": f["cluster_path_str"],
            "element_name": f["element_name"],
        }
    return sort_state

def build_form_state():
    return {
        "criteria": st.session_state.active_criteria,
        "output_fields": st.session_state.active_output,
        "sort": st.session_state.sort_state,
        "advanced": st.session_state.active_advanced,
    }

def run_full_search(prepared):
    files, _, _ = resolve_runtime_files_for_query(
        st.session_state.dataset_folder_input.strip(),
        prepared["composition_archetype"],
    )
    if not files:
        st.error("No composition files matching the active schema were found.")
        return

    form_state = build_form_state()
    plan = compile_query(form_state)
    st.session_state.active_query_plan = plan

    out = run_query(
        files[: int(form_state["advanced"].get("slice_size", DEFAULT_SLICE_SIZE))],
        plan,
        occurrence_semantics=form_state["advanced"].get("occurrence_semantics", DEFAULT_OCCURRENCE_SEMANTICS),
        limit=int(form_state["advanced"].get("result_limit", DEFAULT_RESULT_LIMIT)),
    )

    if plan.get("sort") and out.get("rows"):
        sort_fk = plan["sort"]["field_key"]
        reverse = plan["sort"].get("direction") == "desc"
        out["rows"] = sorted(
            out["rows"],
            key=lambda r: (r.get(sort_fk) is None, r.get(sort_fk)),
            reverse=reverse,
        )

    st.session_state.full_result = out
    st.session_state.card_offset = 0
    st.session_state.table_limit = 25

def reset_query_state():
    st.session_state.active_criteria = []
    st.session_state.active_output = []
    st.session_state.sort_state = None
    st.session_state.active_advanced = {
        "occurrence_semantics": DEFAULT_OCCURRENCE_SEMANTICS,
        "include_unknown": False,
        "slice_size": DEFAULT_SLICE_SIZE,
        "result_limit": DEFAULT_RESULT_LIMIT,
    }
    st.session_state.full_result = None
    st.session_state.active_query_plan = None
    st.session_state.card_offset = 0
    st.session_state.table_limit = 25
    st.session_state.show_funnel_panel = False
    st.session_state.show_explain_panel = False

def most_restrictive_funnel_stage(funnel_rows):
    if not funnel_rows or len(funnel_rows) < 2:
        return None
    best = None
    biggest_drop = -1
    for i in range(1, len(funnel_rows)):
        drop = funnel_rows[i - 1].get("remaining", 0) - funnel_rows[i].get("remaining", 0)
        if drop > biggest_drop:
            biggest_drop = drop
            best = funnel_rows[i]
    return best

def render_result_cards(display_df, active_criteria, batch_size=10):
    start = st.session_state.card_offset
    end = min(start + batch_size, len(display_df))
    subset = display_df.iloc[start:end]
    st.caption(f"Showing cards {start + 1}–{end} of {len(display_df)}")

    query_fields = [c.get("element_name", "") for c in active_criteria]

    for i, row in subset.iterrows():
        title = row.get("Record", f"Record {i + 1}")
        ordered_cols = (
            ["Record"]
            + [c for c in display_df.columns if c in query_fields]
            + [c for c in display_df.columns if c not in query_fields and c not in {"Record", "_source_file"}]
        )

        key_fields = []
        why = []
        for col in ordered_cols:
            if col == "_source_file":
                continue
            val = row.get(col)
            if pd.isna(val):
                continue
            if len(key_fields) < 6:
                key_fields.append((col, val))
            if col in query_fields:
                why.append(f"{col}: {val}")

        result_card(title, key_fields, why[:4] if why else None)

        with st.expander("View full record details", expanded=False):
            detail_cols = [c for c in display_df.columns if c != "_source_file"]
            st.dataframe(pd.DataFrame([row[detail_cols]]), use_container_width=True)

    if end < len(display_df):
        if st.button("Load more results", key="load_more_cards"):
            st.session_state.card_offset += batch_size
            do_rerun()

def render_table_results(display_df):
    limit = st.session_state.table_limit
    st.caption(f"Showing {min(limit, len(display_df))} of {len(display_df)} rows")
    st.dataframe(display_df.iloc[:limit], use_container_width=True)
    if limit < len(display_df):
        if st.button("Show more rows", key="show_more_rows"):
            st.session_state.table_limit += 25
            do_rerun()

# ============================================================
# Dismissible chip renderers
# ============================================================
def render_active_filter_chips():
    if not st.session_state.active_criteria:
        st.caption("No active filters yet.")
        return

    st.markdown("### Active filters")
    for i, c in enumerate(st.session_state.active_criteria):
        field = c.get("element_name", "Field")
        op = c.get("operator", "")
        val = c.get("value", "")
        chip_text = f"{field} [{op}]" if op in ("is_known", "is_unknown") else f"{field} {op} {val}"

        cols = st.columns([10, 1])
        cols[0].markdown(f'<span class="aqf-chip">{chip_text}</span>', unsafe_allow_html=True)
        if cols[1].button("✕", key=f"remove_filter_chip_{i}"):
            field_key = c.get("field_key")
            use_key = f"use_{field_key}"
            if use_key in st.session_state:
                st.session_state[use_key] = False
            st.session_state.active_criteria.pop(i)
            st.session_state.full_result = None
            do_rerun()

def render_active_output_chips():
    if not st.session_state.active_output:
        st.caption("No result fields selected yet.")
        return

    st.markdown("### Selected result fields")
    for i, o in enumerate(st.session_state.active_output):
        label = o.get("element_name", o.get("name", "Field"))
        cols = st.columns([10, 1])
        cols[0].markdown(f'<span class="aqf-chip">{label}</span>', unsafe_allow_html=True)
        if cols[1].button("✕", key=f"remove_output_chip_{i}"):
            st.session_state.active_output.pop(i)
            if "output_multiselect" in st.session_state:
                remaining = [x.get("name", x.get("element_name", "Field")) for x in st.session_state.active_output]
                st.session_state.output_multiselect = remaining
            st.session_state.full_result = None
            do_rerun()

def render_sort_chip():
    if not st.session_state.sort_state:
        return

    s = st.session_state.sort_state
    label = f"Sort: {s.get('element_name', 'Field')} ({s.get('direction', 'asc')})"

    st.markdown("### Sort")
    cols = st.columns([10, 1])
    cols[0].markdown(f'<span class="aqf-chip">{label}</span>', unsafe_allow_html=True)
    if cols[1].button("✕", key="remove_sort_chip"):
        st.session_state.sort_state = None
        if "sort_by_ui" in st.session_state:
            st.session_state.sort_by_ui = "(none)"
        st.session_state.full_result = None
        do_rerun()

# ============================================================
# Bootstrap
# ============================================================
if not st.session_state.cached_schema_bundle and not st.session_state.cache_auto_load_attempted:
    st.session_state.cache_auto_load_attempted = True
    cached_bundle, _ = load_cached_schema_bundle()
    if cached_bundle:
        st.session_state.cached_schema_bundle = cached_bundle
    elif Path(st.session_state.dataset_folder_input).exists():
        build_or_refresh_schema()

prepared = st.session_state.cached_schema_bundle

render_brand()
st.title("AQF")
st.caption("A generated query form over hierarchical healthcare records, redesigned for easier end-user interaction.")

with st.sidebar:
    st.markdown("## Workspace")
    st.text_input("Dataset folder path", key="dataset_folder_input")
    st.toggle("Expert mode", key="expert_mode")

    if "sidebar_result_view_mode" not in st.session_state:
        st.session_state.sidebar_result_view_mode = st.session_state.result_view_mode

    st.radio(
        "Results view",
        ["Cards", "Table"],
        key="sidebar_result_view_mode",
        on_change=sync_result_view_from_sidebar,
    )

    st.markdown("---")
    if st.button("Build / Refresh Schema"):
        st.session_state.schema_build_token += 1
        build_or_refresh_schema()
        do_rerun()

    if st.button("↺ Reset query", key="reset_sidebar"):
        reset_query_state()
        do_rerun()

if prepared is None:
    st.warning("No schema is loaded yet. Select a valid dataset folder and click **Build / Refresh Schema**.")
    st.stop()

union = prepared["union"]
catalog = prepared["catalog"]
form = prepared["form"]

g1, g2, g3, g4, g5 = count_summary(union, catalog)

# ============================================================
# Sticky summary area
# ============================================================
summary_md = build_query_summary_markdown(
    st.session_state.active_criteria,
    st.session_state.active_output,
    st.session_state.sort_state,
    st.session_state.active_advanced,
)
render_summary(summary_md)

quick_chips = []
for c in st.session_state.active_criteria[:4]:
    field = c.get("element_name", "Field")
    op = c.get("operator", "")
    val = c.get("value", "")
    quick_chips.append(f"{field} [{op}]" if op in ("is_known", "is_unknown") else f"{field} {op} {val}")

for o in st.session_state.active_output[:3]:
    quick_chips.append(f"Show: {o.get('element_name', o.get('name', 'Field'))}")

if st.session_state.sort_state:
    quick_chips.append(f"Sort: {st.session_state.sort_state.get('element_name', 'Field')}")

render_quick_chips(quick_chips)

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Sections", g1)
m2.metric("Subgroups", g2)
m3.metric("Leaf fields", g3)
m4.metric("Suggested fields", g4)
m5.metric("Unknown-capable", g5)

with st.expander("How this search is organized", expanded=False):
    try:
        dot = build_schema_flow_dot(
            union,
            max_depth=SCHEMA_OVERVIEW_MAX_DEPTH,
            direction=normalize_graph_direction(SCHEMA_GRAPH_DIRECTION),
            leaf_limit=SCHEMA_LEAF_LIMIT,
        )
    except TypeError:
        dot = build_schema_flow_dot(union)
    st.graphviz_chart(dot)

# ============================================================
# Filters (collapsible)
# ============================================================
# with st.expander("Filters", expanded=True):
with st.form("generated_filters_form"):
    search = st.text_input("Search filters by name or section", key="criteria_search")
    widget_meta = []
    for group in form.get("criteria_groups", []):
        # st.markdown(f"### {group.get('group_label', 'Section')}")
        with st.expander(
            group.get("group_label", "Section"),
            expanded=(group.get("group_label") in ["HCPA"])
        ):
            for subgroup in group.get("subgroups", []):
                subgroup_label = display_cluster_label(subgroup.get("label", "(no cluster)"))
                st.markdown(f"**{subgroup_label}**")
                for fld in subgroup.get("fields", []):
                    hay = f"{fld.get('full_label', '')} {fld.get('label', '')} {subgroup.get('label', '')}".lower()
                    if search and search.lower() not in hay:
                        continue
                    st.markdown("---")
                    cols = st.columns([2, 4, 4])
                    use_key = f"use_{fld['field_key']}"
                    op_key = f"op_{fld['field_key']}"
                    val_key = f"val_{fld['field_key']}"
                    suggest_key = f"suggest_{fld['field_key']}"
                    # Column 1: Use checkbox
                    with cols[0]:
                        fld["label"]
                        st.checkbox("Use", key=use_key)
                    # Column 2: Operator
                    with cols[1]:
                        op_options = fld.get("operators", [])
                        op_labels = [f"{o['phrase']} ({o['op']})" for o in op_options] if op_options else ["equals (=)"]                        
                        st.selectbox("Condition", op_labels, key=op_key)
                    # Column 3: Value
                    with cols[2]:
                        mode = fld.get("suggestion_mode", "none")
                        suggestions = fld.get("suggested_values", [])
                        if mode in ("categorical", "boolean") and suggestions:
                            st.selectbox(
                                "Values",
                                ["<Enter custom value>"] + suggestions,
                                key=suggest_key,
                                help=fld.get("tooltip", ""),
                            )
                            st.text_input("Custom value (optional)", key=val_key)
                        else:
                            st.text_input(
                                "Values",
                                key=val_key,
                                help=fld.get("tooltip", ""),
                            )
                    # Column 4: Helper text
                    # with cols[3]:
                    #     if fld.get("suggested_values"):
                    #         st.caption("Common values: " + ", ".join(fld["suggested_values"][:5]))
                    #     else:
                    #         st.caption("No cached suggestions yet.")
                    widget_meta.append((group, subgroup, fld))
    apply_filters = st.form_submit_button("Apply filters")
    if apply_filters:
        new_criteria = []
        for group, subgroup, fld in widget_meta:
            use_key = f"use_{fld['field_key']}"
            op_key = f"op_{fld['field_key']}"
            val_key = f"val_{fld['field_key']}"
            suggest_key = f"suggest_{fld['field_key']}"
            if not st.session_state.get(use_key, False):
                continue
            op_choice = st.session_state.get(op_key)
            op_obj = next(
                (o for o in fld.get("operators", []) if f"{o['phrase']} ({o['op']})" == op_choice),
                None,
            )
            if not op_obj:
                continue
            mode = fld.get("suggestion_mode", "none")
            suggestions = fld.get("suggested_values", [])
            value = None
            if mode in ("categorical", "boolean") and suggestions:
                selected = st.session_state.get(suggest_key)
                custom = st.session_state.get(val_key)
                value = custom if selected == "<Enter custom value>" else (selected if selected else custom)
            else:
                value = st.session_state.get(val_key)
            if op_obj["op"] not in ("is_known", "is_unknown") and (value is None or str(value).strip() == ""):
                continue
            new_criteria.append(
                {
                    "field_key": fld["field_key"],
                    "operator": op_obj["op"],
                    "value": None if op_obj["op"] in ("is_known", "is_unknown") else value,
                }
            )
        st.session_state.active_criteria = enrich_criteria(new_criteria, catalog)
        st.session_state.full_result = None
        st.success("Filters applied.")
render_active_filter_chips()

# ============================================================
# Results to show (collapsible)
# ============================================================
with st.expander("Results to show", expanded=(len(st.session_state.active_output) == 0)):
    output_defs = form.get("output_fields", [])

    default_output_labels = (
        [x["name"] for x in st.session_state.active_output]
        if st.session_state.active_output
        else [f["label"] for f in output_defs[:4]]
    )

    selected_labels = st.multiselect(
        "Choose result fields",
        [f["label"] for f in output_defs],
        default=default_output_labels,
        key="output_multiselect",
    )

    sort_choices = {f["label"]: f["field_key"] for f in output_defs}
    sort_label = st.selectbox(
        "Sort by",
        ["(none)"] + list(sort_choices.keys()),
        key="sort_by_ui",
    )
    sort_dir = st.selectbox(
        "Direction",
        ["desc", "asc"],
        index=0,
        key="sort_dir_ui",
    )

    if st.button("Apply result settings", key="apply_output_settings"):
        selected_outputs = []
        for lbl in selected_labels:
            f = next((x for x in output_defs if x["label"] == lbl), None)
            if f:
                selected_outputs.append(
                    {
                        "field_key": f["field_key"],
                        "name": f["label"],
                        "dv_type": f.get("dv_type", ""),
                    }
                )

        st.session_state.active_output = enrich_outputs(selected_outputs, catalog)

        if sort_label != "(none)":
            raw_sort = {
                "field_key": sort_choices[sort_label],
                "direction": sort_dir,
            }
            st.session_state.sort_state = enrich_sort(raw_sort, catalog)
        else:
            st.session_state.sort_state = None

        st.session_state.full_result = None
        st.success("Result settings applied.")

    render_active_output_chips()
    render_sort_chip()

# ============================================================
# More options (collapsible)
# ============================================================
with st.expander("More options", expanded=False):
    semantics = st.selectbox(
        "Repeated occurrence semantics",
        ["ALL", "ANY"],
        index=0 if st.session_state.active_advanced.get("occurrence_semantics", "ALL") == "ALL" else 1,
    )
    include_unknown = st.checkbox(
        "Include unknown values",
        value=st.session_state.active_advanced.get("include_unknown", False),
    )
    slice_size = st.number_input(
        "Slice size",
        min_value=10,
        max_value=10000,
        value=int(st.session_state.active_advanced.get("slice_size", DEFAULT_SLICE_SIZE)),
        step=10,
    )
    result_limit = st.number_input(
        "Result limit",
        min_value=10,
        max_value=5000,
        value=int(st.session_state.active_advanced.get("result_limit", DEFAULT_RESULT_LIMIT)),
        step=10,
    )

    st.session_state.active_advanced = {
        "occurrence_semantics": semantics,
        "include_unknown": include_unknown,
        "slice_size": slice_size,
        "result_limit": result_limit,
    }

# ============================================================
# Search actions
# ============================================================
st.markdown("## Search actions")
action_cols = st.columns([1, 1, 1, 1])

if action_cols[0].button("Search", key="apply_search_main", use_container_width=True):
    run_full_search(prepared)
    do_rerun()

if action_cols[1].button("Show / Hide funnel", key="toggle_funnel_main", use_container_width=True):
    st.session_state.show_funnel_panel = not st.session_state.show_funnel_panel
    do_rerun()

if action_cols[2].button("Explain this search", key="toggle_explain", use_container_width=True):
    st.session_state.show_explain_panel = not st.session_state.show_explain_panel
    do_rerun()

if action_cols[3].button("Reset query", key="reset_query_main", use_container_width=True):
    reset_query_state()
    do_rerun()

# ============================================================
# Results area
# ============================================================
st.markdown("---")
st.markdown("## Results")

result = st.session_state.full_result
if not result:
    st.info("Apply your generated AQF form above, then click **Search** to run the query.")
else:
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Scanned", result.get("scanned", 0))
    r2.metric("Matched", result.get("matched", 0))
    r3.metric("Sec / doc", f"{result.get('sec_per_doc', 0.0):.6f}")
    r4.metric("Current view", st.session_state.result_view_mode)

    restrictive = most_restrictive_funnel_stage(result.get("funnel", []))
    if restrictive and result.get("matched", 0) == 0:
        card(
            "No matching records found",
            f"The strongest narrowing happened at: {restrictive.get('label', 'unknown stage')}. Try removing or relaxing this condition.",
            tone="empty",
        )
    elif restrictive:
        card(
            "Most restrictive condition",
            f"{restrictive.get('label', 'unknown stage')}. This stage narrowed the result set the most.",
            tone="warning",
        )
    else:
        card("Search complete", "AQF found matching records for the current search.", tone="success")

    display_df = format_results_for_display(
        result.get("rows", []),
        st.session_state.active_output,
    ) if result.get("rows") else pd.DataFrame()

    if "results_result_view_mode" not in st.session_state:
        st.session_state.results_result_view_mode = st.session_state.result_view_mode

    st.radio(
        "View results as",
        ["Cards", "Table"],
        horizontal=True,
        key="results_result_view_mode",
        on_change=sync_result_view_from_results,
    )

    if display_df.empty:
        st.info("No result rows to display.")
    elif st.session_state.result_view_mode == "Cards":
        render_result_cards(display_df, st.session_state.active_criteria)
    else:
        render_table_results(display_df)

    if st.session_state.show_funnel_panel and result.get("funnel"):
        st.markdown("### Query funnel")
        st.dataframe(pd.DataFrame(result["funnel"]), use_container_width=True)

    if st.session_state.show_explain_panel:
        st.markdown("### Explainability")
        try:
            touched_dot = build_touched_query_dot(
                criteria=st.session_state.active_criteria,
                outputs=st.session_state.active_output,
                sort_state=st.session_state.sort_state,
                advanced=st.session_state.active_advanced,
                mode="all",
                direction=normalize_graph_direction(SCHEMA_GRAPH_DIRECTION),
            )
        except TypeError:
            touched_dot = build_touched_query_dot(
                st.session_state.active_criteria,
                st.session_state.active_output,
                st.session_state.sort_state,
            )
        st.graphviz_chart(touched_dot)
        st.markdown(summary_md)