# app.py

from __future__ import annotations
import json
import hashlib
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

from config import (
    DATA_DIR, CACHE_DIR, SCHEMA_UNION_FILE, FIELDS_FILE,
    DEFAULT_SLICE_SIZE, DEFAULT_RESULT_LIMIT, DEFAULT_OCCURRENCE_SEMANTICS,
    SCHEMA_OVERVIEW_MAX_DEPTH, SCHEMA_GRAPH_DIRECTION, SCHEMA_LEAF_LIMIT
)
from composition_loader import group_docs_by_composition_archetype
from schema_union_builder import build_union_schema
from field_catalog import build_field_catalog
from form_definition_builder import build_form_definition
from query_compiler import compile_query
from query_executor import run_query
from result_formatter import format_results_for_display
from schema_diagram import build_schema_flow_dot, build_touched_query_dot
from query_summary import build_query_summary_markdown

st.set_page_config(page_title="openEHR Accordion Form Builder", layout="wide")

SCHEMA_META_FILE = CACHE_DIR / "schema_metadata.json"


# -------------------------------------------------------
# Basic helpers
# -------------------------------------------------------
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

def signature_of_state(criteria, output_fields, sort_state, advanced):
    payload = {
        "criteria": criteria,
        "output_fields": output_fields,
        "sort": sort_state,
        "advanced": advanced
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def count_summary(union, catalog):
    groups = len(union.get("groups", {}))
    subgroups = sum(len(g["subgroups"]) for g in union.get("groups", {}).values())
    fields = len(catalog)
    suggestion_fields = sum(1 for f in catalog if f.get("suggested_values"))
    null_fields = sum(1 for f in catalog if f.get("has_null_flavour"))
    return groups, subgroups, fields, suggestion_fields, null_fields

def dataset_signature(folder: str) -> str:
    p = Path(folder)
    if not p.exists():
        return ""
    items = []
    for fp in sorted([x for x in p.iterdir() if x.suffix.lower() == ".json"]):
        stat = fp.stat()
        items.append(f"{fp.name}|{stat.st_size}|{int(stat.st_mtime)}")
    raw = "\n".join(items)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()

def save_schema_metadata(dataset_folder: str, comp_arch: str, built_at: str):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    meta = {
        "dataset_folder": dataset_folder,
        "dataset_signature": dataset_signature(dataset_folder),
        "composition_archetype": comp_arch,
        "built_at": built_at
    }
    save_json(meta, SCHEMA_META_FILE)

def load_schema_metadata():
    if SCHEMA_META_FILE.exists():
        return load_json(SCHEMA_META_FILE)
    return None

def render_query_chips(criteria, outputs, sort_state):
    chips = []

    for c in criteria[:5]:
        val = c.get("value", "")
        chips.append(f"FILTER: {c.get('element_name', 'Field')} {c.get('operator', '')} {val}")

    for o in outputs[:5]:
        chips.append(f"OUTPUT: {o.get('element_name', o.get('name', 'Field'))}")

    if sort_state:
        chips.append(f"SORT: {sort_state.get('element_name', 'Field')} ({sort_state.get('direction', 'asc')})")

    if not chips:
        st.caption("No active query settings yet.")
        return

    html = ""
    for chip in chips:
        html += f"""
        <span style="
            display:inline-block;
            padding:6px 10px;
            margin:4px 6px 4px 0;
            border-radius:12px;
            background:#eef3ff;
            border:1px solid #c7d7ff;
            font-size:12px;
        ">{chip}</span>
        """
    st.markdown(html, unsafe_allow_html=True)


# -------------------------------------------------------
# Friendly display helpers
# -------------------------------------------------------
def display_cluster_label(cluster_path_str: str) -> str:
    if not cluster_path_str or cluster_path_str == "(no cluster)":
        return "Top-level fields"
    return cluster_path_str

def display_element_label(item: dict) -> str:
    return item.get("element_name") or item.get("name") or "Field"

def render_state_tree(title: str, groups: dict):
    st.markdown(f"### {title}")
    if not groups:
        st.caption("No active items.")
        return

    lines = []
    for entry_name, clusters in groups.items():
        lines.append(f"- **{entry_name}**")
        for cluster_label, items in clusters.items():
            lines.append(f"  - **{cluster_label}**")
            for item in items:
                lines.append(f"    - {item}")

    st.markdown("\n".join(lines))

def build_criteria_tree(criteria_list):
    groups = {}
    for c in criteria_list:
        entry = c.get("entry_name", "Unknown section")
        cluster = display_cluster_label(c.get("cluster_path_str", "(no cluster)"))
        field = display_element_label(c)
        op = c.get("operator", "")
        val = c.get("value", "")

        if op in ("is_known", "is_unknown"):
            label = f"**{field}** [{op}]"
        else:
            label = f"**{field}** [{op}] `{val}`"

        groups.setdefault(entry, {}).setdefault(cluster, []).append(label)
    return groups

def build_output_tree(output_list):
    groups = {}
    for o in output_list:
        entry = o.get("entry_name", "Unknown section")
        cluster = display_cluster_label(o.get("cluster_path_str", "(no cluster)"))
        field = display_element_label(o)
        label = f"**{field}**"
        groups.setdefault(entry, {}).setdefault(cluster, []).append(label)
    return groups

def build_sort_tree(sort_state):
    if not sort_state:
        return {}
    entry = sort_state.get("entry_name", "Unknown section")
    cluster = display_cluster_label(sort_state.get("cluster_path_str", "(no cluster)"))
    field = sort_state.get("element_name", "Field")
    direction = sort_state.get("direction", "asc")
    return {entry: {cluster: [f"Sort by **{field}** ({direction})"]}}

def build_advanced_tree(advanced_dict):
    groups = {"Advanced settings": {"Execution": []}}

    if advanced_dict:
        groups["Advanced settings"]["Execution"].append(
            f"Occurrence semantics: **{advanced_dict.get('occurrence_semantics', 'ALL')}**"
        )
        groups["Advanced settings"]["Execution"].append(
            f"Include unknown values: **{'Yes' if advanced_dict.get('include_unknown', False) else 'No'}**"
        )
        groups["Advanced settings"]["Execution"].append(
            f"Slice size: **{advanced_dict.get('slice_size', '')}**"
        )
        groups["Advanced settings"]["Execution"].append(
            f"Result limit: **{advanced_dict.get('result_limit', '')}**"
        )

    return groups


# -------------------------------------------------------
# State reset helpers
# -------------------------------------------------------
def reset_filters():
    st.session_state.active_criteria = []

def reset_outputs():
    st.session_state.active_output = []
    st.session_state.sort_state = None

def reset_query_state():
    reset_filters()
    reset_outputs()
    st.session_state.active_advanced = {
        "occurrence_semantics": DEFAULT_OCCURRENCE_SEMANTICS,
        "include_unknown": False,
        "slice_size": DEFAULT_SLICE_SIZE,
        "result_limit": DEFAULT_RESULT_LIMIT
    }
    st.session_state.active_query_plan = None
    st.session_state.last_run_result = None
    st.session_state.last_run_signature = None

def reset_schema_cache():
    st.session_state.schema_build_token += 1
    st.session_state.cached_schema_bundle = None
    st.session_state.schema_built_at = None
    st.session_state.schema_loaded_from_cache = False
    st.session_state.cache_auto_load_attempted = False
    reset_query_state()

    for fp in [SCHEMA_UNION_FILE, FIELDS_FILE, SCHEMA_META_FILE]:
        if fp.exists():
            fp.unlink()

def initialize_state():
    defaults = {
        "schema_build_token": 0,
        "cached_schema_bundle": None,
        "schema_built_at": None,
        "active_criteria": [],
        "active_output": [],
        "active_advanced": {
            "occurrence_semantics": DEFAULT_OCCURRENCE_SEMANTICS,
            "include_unknown": False,
            "slice_size": DEFAULT_SLICE_SIZE,
            "result_limit": DEFAULT_RESULT_LIMIT
        },
        "sort_state": None,
        "active_query_plan": None,
        "last_run_result": None,
        "last_run_signature": None,
        "dataset_folder_input": str(DATA_DIR),
        "cache_auto_load_attempted": False,
        "schema_loaded_from_cache": False,
        "cache_loaded_without_validation": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# -------------------------------------------------------
# Cache-first startup helpers
# -------------------------------------------------------
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

    dataset_folder = st.session_state.dataset_folder_input.strip()
    validated = False

    if meta:
        if meta.get("dataset_folder") == dataset_folder:
            current_sig = dataset_signature(dataset_folder)
            validated = (meta.get("dataset_signature") == current_sig)

    bundle = {
        "composition_archetype": comp_arch,
        "union": union,
        "catalog": catalog,
        "form": form,
        "built_at": built_at
    }
    return bundle, validated

def resolve_runtime_files_for_query(dataset_folder: str, composition_archetype: str):
    valid_groups, skipped = group_docs_by_composition_archetype(Path(dataset_folder))
    files = []

    if composition_archetype in valid_groups:
        files = [p for p, _ in valid_groups[composition_archetype]]

    return files, skipped, valid_groups


# -------------------------------------------------------
# Explicit schema build / refresh
# -------------------------------------------------------
@st.cache_data(show_spinner=False)
def cached_build_from_dataset(data_dir: str, schema_build_token: int):
    valid_groups, skipped = group_docs_by_composition_archetype(Path(data_dir))

    if not valid_groups:
        return None, skipped, []

    comp_arch = max(valid_groups.items(), key=lambda item: len(item[1]))[0]
    docs = valid_groups[comp_arch]
    docs_only = [d for _, d in docs]

    union = build_union_schema(docs_only)
    catalog = build_field_catalog(union)
    form = build_form_definition(union, catalog)

    comp_arch_options = list(valid_groups.keys())
    return {
        "composition_archetype": comp_arch,
        "union": union,
        "catalog": catalog,
        "form": form
    }, skipped, comp_arch_options

def build_or_refresh_schema():
    data_dir = st.session_state.dataset_folder_input.strip()
    built, skipped, comp_arch_options = cached_build_from_dataset(
        data_dir,
        st.session_state.schema_build_token
    )

    if not built:
        st.error("No valid composition files found in dataset folder.")
        return

    union = built["union"]
    catalog = built["catalog"]

    save_json(union, SCHEMA_UNION_FILE)
    save_json(catalog, FIELDS_FILE)

    built_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_schema_metadata(data_dir, built["composition_archetype"], built_at)

    st.session_state.cached_schema_bundle = {
        **built,
        "built_at": built_at
    }
    st.session_state.schema_built_at = built_at
    st.session_state.schema_loaded_from_cache = False
    st.session_state.cache_loaded_without_validation = False

def get_field_by_key(catalog, field_key: str):
    return next((f for f in catalog if f["field_key"] == field_key), None)

def enrich_criteria(criteria_list, catalog):
    enriched = []
    for c in criteria_list:
        f = get_field_by_key(catalog, c["field_key"])
        if not f:
            enriched.append(c)
            continue

        enriched.append({
            **c,
            "entry_name": f["entry_name"],
            "cluster_path_str": f["cluster_path_str"],
            "element_name": f["element_name"],
            "dv_type": f["dv_type"]
        })
    return enriched

def enrich_outputs(output_list, catalog):
    enriched = []
    for o in output_list:
        f = get_field_by_key(catalog, o["field_key"])
        if not f:
            enriched.append(o)
            continue

        enriched.append({
            **o,
            "entry_name": f["entry_name"],
            "cluster_path_str": f["cluster_path_str"],
            "element_name": f["element_name"],
            "name": f["label"],
            "dv_type": f["dv_type"]
        })
    return enriched

def enrich_sort(sort_state, catalog):
    if not sort_state:
        return None
    f = get_field_by_key(catalog, sort_state["field_key"])
    if not f:
        return sort_state
    return {
        **sort_state,
        "entry_name": f["entry_name"],
        "cluster_path_str": f["cluster_path_str"],
        "element_name": f["element_name"]
    }


# -------------------------------------------------------
# App init
# -------------------------------------------------------
initialize_state()

st.title("openEHR Accordion Form Builder")
st.caption(
    "Accordion-based composition form UI with cache-first startup, "
    "explicit schema rebuild, readable results, query funnel, and touched-schema lineage."
)

# Dataset
st.markdown("### Dataset")
st.text_input(
    "Dataset folder path",
    key="dataset_folder_input",
    help="Enter the folder containing your composition JSON files."
)

dataset_folder = st.session_state.dataset_folder_input.strip()
if not dataset_folder:
    st.warning("Please enter a dataset folder path.")
    st.stop()

if not Path(dataset_folder).exists():
    st.error(f"Dataset folder does not exist: {dataset_folder}")
    st.stop()

# Auto-load cache
if (
    st.session_state.cached_schema_bundle is None
    and not st.session_state.cache_auto_load_attempted
):
    st.session_state.cache_auto_load_attempted = True

    cached_bundle, validated = load_cached_schema_bundle()
    if cached_bundle:
        st.session_state.cached_schema_bundle = cached_bundle
        st.session_state.schema_built_at = cached_bundle.get("built_at")
        st.session_state.schema_loaded_from_cache = True
        st.session_state.cache_loaded_without_validation = not validated
    else:
        build_or_refresh_schema()

prepared = st.session_state.cached_schema_bundle
if prepared is None:
    st.warning("No cached schema found and no valid schema could be built. Click **Build / Refresh Schema** to try again.")
    st.stop()

comp_arch = prepared["composition_archetype"]
union = prepared["union"]
catalog = prepared["catalog"]
form = prepared["form"]
built_at = prepared.get("built_at")

# Top controls
top1, top2, top3, top4, top5 = st.columns([2, 2, 1, 1, 1])

with top1:
    if st.button("Build / Refresh Schema", key="build_refresh_schema"):
        st.session_state.schema_build_token += 1
        build_or_refresh_schema()

with top2:
    if built_at:
        st.info(f"Schema last built: {built_at}")
    else:
        st.info("Loaded cached schema (build time unavailable).")

with top3:
    if st.button("Reset Filters", key="reset_filters"):
        reset_filters()

with top4:
    if st.button("Reset Outputs", key="reset_outputs"):
        reset_outputs()

with top5:
    if st.button("Reset Query", key="reset_query"):
        reset_query_state()

if st.button("Reset Schema Cache", key="reset_schema_cache"):
    reset_schema_cache()
    do_rerun()

# Cache banner
if st.session_state.schema_loaded_from_cache:
    if st.session_state.cache_loaded_without_validation:
        st.warning(
            "Loaded schema from `.cache` without validating the current dataset folder. "
            "Click **Build / Refresh Schema** if you want to validate/rebuild it."
        )
    else:
        st.success("Loaded schema from cache.")

# Status banner
current_sig = signature_of_state(
    st.session_state.active_criteria,
    st.session_state.active_output,
    st.session_state.sort_state,
    st.session_state.active_advanced
)

if st.session_state.last_run_signature is None:
    st.info("Form ready. Apply filters / output settings, then click **Run Query**.")
elif st.session_state.last_run_signature != current_sig:
    st.warning("Form updated — click **Run Query** to execute the latest changes.")
else:
    st.success("Showing results for the last executed query.")

render_query_chips(
    st.session_state.active_criteria,
    st.session_state.active_output,
    st.session_state.sort_state
)

# Summary cards
groups_count, subgroups_count, fields_count, suggestion_fields_count, null_fields_count = count_summary(union, catalog)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Entry groups", groups_count)
c2.metric("Cluster subgroups", subgroups_count)
c3.metric("Leaf fields", fields_count)
c4.metric("Fields with suggestions", suggestion_fields_count)
c5.metric("Fields supporting unknown", null_fields_count)

with st.expander("Dataset diagnostics", expanded=False):
    st.write(f"Loaded composition archetype from schema: `{comp_arch}`")
    st.write(f"Current dataset folder: `{dataset_folder}`")

with st.expander("Schema structure overview", expanded=False):
    dot = build_schema_flow_dot(
        union,
        max_depth=SCHEMA_OVERVIEW_MAX_DEPTH,
        direction=SCHEMA_GRAPH_DIRECTION,
        leaf_limit=SCHEMA_LEAF_LIMIT
    )
    st.graphviz_chart(dot)

# Tabs
tab_criteria, tab_output, tab_advanced, tab_results = st.tabs(
    ["Criteria", "Output", "Advanced", "Results"]
)

# Criteria tab
with tab_criteria:
    st.subheader(form["composition_label"])

    with st.form("criteria_form"):
        search = st.text_input("Search fields by name or cluster", key="criteria_search")
        widget_meta = []

        for group in form["criteria_groups"]:
            with st.expander(group["group_label"], expanded=(group["group_label"] in ["HCPA", "Problem/Diagnosis"])):
                for subgroup in group["subgroups"]:
                    subgroup_label = display_cluster_label(subgroup["label"])
                    st.markdown(f"**{subgroup_label}**")

                    for fld in subgroup["fields"]:
                        hay = f"{fld['full_label']} {fld['label']} {subgroup['label']}".lower()
                        if search and search.lower() not in hay:
                            continue

                        st.markdown("---")
                        cols = st.columns([1, 2, 2, 4])

                        use_key = f"use_{fld['field_key']}"
                        op_key = f"op_{fld['field_key']}"
                        val_key = f"val_{fld['field_key']}"
                        suggest_key = f"suggest_{fld['field_key']}"

                        with cols[0]:
                            st.checkbox("Use", key=use_key)

                        with cols[1]:
                            op_options = fld["operators"]
                            op_labels = [f"{o['phrase']} ({o['op']})" for o in op_options]
                            st.selectbox(
                                "Condition",
                                op_labels,
                                key=op_key,
                                help=fld["tooltip"]
                            )

                        with cols[2]:
                            mode = fld.get("suggestion_mode", "none")
                            suggestions = fld.get("suggested_values", [])

                            if mode in ("categorical", "boolean") and suggestions:
                                st.selectbox(
                                    fld["label"],
                                    ["<Enter custom value>"] + suggestions,
                                    key=suggest_key,
                                    help=fld["tooltip"]
                                )
                                st.text_input(
                                    "Custom value (optional)",
                                    key=val_key
                                )
                            elif mode == "boolean":
                                st.selectbox(
                                    fld["label"],
                                    ["true", "false"],
                                    key=val_key,
                                    help=fld["tooltip"]
                                )
                            else:
                                st.text_input(
                                    fld["label"],
                                    key=val_key,
                                    help=fld["tooltip"]
                                )

                        with cols[3]:
                            if fld.get("suggested_values"):
                                st.caption("Common values: " + ", ".join(fld["suggested_values"][:5]))
                            else:
                                st.caption("No cached suggestions yet.")

                        widget_meta.append(fld)

        apply_criteria = st.form_submit_button("Apply Filters")

        if apply_criteria:
            new_criteria = []

            for fld in widget_meta:
                use_key = f"use_{fld['field_key']}"
                op_key = f"op_{fld['field_key']}"
                val_key = f"val_{fld['field_key']}"
                suggest_key = f"suggest_{fld['field_key']}"

                if not st.session_state.get(use_key, False):
                    continue

                op_choice = st.session_state.get(op_key)
                op_obj = next(
                    (o for o in fld["operators"] if f"{o['phrase']} ({o['op']})" == op_choice),
                    None
                )
                if not op_obj:
                    continue

                value = None
                suggestions = fld.get("suggested_values", [])
                mode = fld.get("suggestion_mode", "none")

                if mode in ("categorical", "boolean") and suggestions:
                    selected = st.session_state.get(suggest_key)
                    custom = st.session_state.get(val_key)
                    if selected == "<Enter custom value>":
                        value = custom
                    elif selected:
                        value = selected
                    else:
                        value = custom
                else:
                    value = st.session_state.get(val_key)

                if op_obj["op"] not in ("is_known", "is_unknown") and (value is None or str(value).strip() == ""):
                    continue

                new_criteria.append({
                    "field_key": fld["field_key"],
                    "operator": op_obj["op"],
                    "value": value
                })

            st.session_state.active_criteria = enrich_criteria(new_criteria, catalog)
            st.success("Filters applied.")

    criteria_tree = build_criteria_tree(st.session_state.active_criteria)
    render_state_tree("Active Filters", criteria_tree)

    with st.expander("Touched schema graph for active filters", expanded=False):
        crit_dot = build_touched_query_dot(
            criteria=st.session_state.active_criteria,
            outputs=[],
            sort_state=None,
            advanced=None,
            mode="criteria",
            direction=SCHEMA_GRAPH_DIRECTION
        )
        st.graphviz_chart(crit_dot)

# Output tab
with tab_output:
    st.subheader("Output fields")

    with st.form("output_form"):
        output_defs = form["output_fields"]
        default_output_labels = [x["name"] for x in st.session_state.active_output] if st.session_state.active_output else []

        selected_labels = st.multiselect(
            "Choose output columns",
            [f["label"] for f in output_defs],
            default=default_output_labels
        )

        sort_choices = {f["label"]: f["field_key"] for f in output_defs}
        sort_label = st.selectbox(
            "Sort by",
            ["(none)"] + list(sort_choices.keys()),
            index=0
        )
        sort_dir = st.selectbox("Direction", ["asc", "desc"], index=0)

        apply_output = st.form_submit_button("Apply Output Settings")

        if apply_output:
            selected_outputs = []
            for lbl in selected_labels:
                f = next((x for x in output_defs if x["label"] == lbl), None)
                if f:
                    selected_outputs.append({
                        "field_key": f["field_key"],
                        "name": f["label"],
                        "dv_type": f["dv_type"]
                    })

            st.session_state.active_output = enrich_outputs(selected_outputs, catalog)

            if sort_label != "(none)":
                raw_sort = {"field_key": sort_choices[sort_label], "direction": sort_dir}
                st.session_state.sort_state = enrich_sort(raw_sort, catalog)
            else:
                st.session_state.sort_state = None

            st.success("Output settings applied.")

    output_tree = build_output_tree(st.session_state.active_output)
    render_state_tree("Active Output Fields", output_tree)

    sort_tree = build_sort_tree(st.session_state.sort_state)
    render_state_tree("Active Sort", sort_tree)

    with st.expander("Touched schema graph for active output and sort", expanded=False):
        out_dot = build_touched_query_dot(
            criteria=[],
            outputs=st.session_state.active_output,
            sort_state=st.session_state.sort_state,
            advanced=None,
            mode="output",
            direction=SCHEMA_GRAPH_DIRECTION
        )
        st.graphviz_chart(out_dot)

# Advanced tab
with tab_advanced:
    st.subheader("Advanced")

    with st.form("advanced_form"):
        semantics = st.selectbox(
            "Repeated occurrence semantics",
            ["ALL", "ANY"],
            index=0 if st.session_state.active_advanced.get("occurrence_semantics", DEFAULT_OCCURRENCE_SEMANTICS) == "ALL" else 1
        )

        include_unknown = st.checkbox(
            "Include unknown (null_flavour) values",
            value=st.session_state.active_advanced.get("include_unknown", False)
        )

        slice_size = st.number_input(
            "Slice size",
            min_value=10,
            max_value=10000,
            value=int(st.session_state.active_advanced.get("slice_size", DEFAULT_SLICE_SIZE)),
            step=10
        )

        result_limit = st.number_input(
            "Result limit",
            min_value=10,
            max_value=5000,
            value=int(st.session_state.active_advanced.get("result_limit", DEFAULT_RESULT_LIMIT)),
            step=10
        )

        apply_advanced = st.form_submit_button("Apply Advanced Settings")

        if apply_advanced:
            st.session_state.active_advanced = {
                "occurrence_semantics": semantics,
                "include_unknown": include_unknown,
                "slice_size": slice_size,
                "result_limit": result_limit
            }
            st.success("Advanced settings applied.")

    advanced_tree = build_advanced_tree(st.session_state.active_advanced)
    render_state_tree("Active Advanced Settings", advanced_tree)

    with st.expander("Touched schema graph for advanced settings", expanded=False):
        adv_dot = build_touched_query_dot(
            criteria=[],
            outputs=[],
            sort_state=st.session_state.sort_state,
            advanced=st.session_state.active_advanced,
            mode="advanced",
            direction=SCHEMA_GRAPH_DIRECTION
        )
        st.graphviz_chart(adv_dot)

    st.write("---")
    if st.button("Run Query", key="run_query_button"):
        files, skipped, valid_groups = resolve_runtime_files_for_query(dataset_folder, comp_arch)

        if not files:
            st.error(
                "No composition files matching the cached schema's composition archetype "
                "were found in the current dataset folder. "
                "Click Build / Refresh Schema if the dataset changed."
            )
            st.stop()

        form_state = {
            "criteria": st.session_state.active_criteria,
            "output_fields": st.session_state.active_output,
            "sort": st.session_state.sort_state,
            "advanced": st.session_state.active_advanced
        }

        plan = compile_query(form_state)
        st.session_state.active_query_plan = plan

        out = run_query(
            files[:int(st.session_state.active_advanced.get("slice_size", DEFAULT_SLICE_SIZE))],
            plan,
            occurrence_semantics=st.session_state.active_advanced.get("occurrence_semantics", DEFAULT_OCCURRENCE_SEMANTICS),
            limit=int(st.session_state.active_advanced.get("result_limit", DEFAULT_RESULT_LIMIT))
        )

        if plan["sort"] and out["rows"]:
            sort_fk = plan["sort"]["field_key"]
            reverse = plan["sort"]["direction"] == "desc"
            out["rows"] = sorted(
                out["rows"],
                key=lambda r: (r.get(sort_fk) is None, r.get(sort_fk)),
                reverse=reverse
            )

        st.session_state.last_run_result = out
        st.session_state.last_run_signature = signature_of_state(
            st.session_state.active_criteria,
            st.session_state.active_output,
            st.session_state.sort_state,
            st.session_state.active_advanced
        )
        st.success("Query executed.")

# Results tab
with tab_results:
    st.subheader("Results")

    if st.session_state.last_run_result:
        out = st.session_state.last_run_result

        c1, c2, c3 = st.columns(3)
        c1.metric("Scanned", out.get("scanned", 0))
        c2.metric("Matched", out.get("matched", 0))
        c3.metric("Sec / doc", f"{out.get('sec_per_doc', 0.0):.6f}")

        st.markdown(
            build_query_summary_markdown(
                st.session_state.active_criteria,
                st.session_state.active_output,
                st.session_state.sort_state,
                st.session_state.active_advanced
            )
        )

        st.markdown("### Query Funnel")
        funnel = out.get("funnel", [])
        if funnel:
            st.dataframe(pd.DataFrame(funnel), use_container_width=True)
        else:
            st.caption("No funnel data available.")

        if out["rows"]:
            display_df = format_results_for_display(
                out["rows"],
                st.session_state.active_output
            )

            visible_cols = [c for c in display_df.columns if c != "_source_file"]
            st.dataframe(display_df[visible_cols], use_container_width=True)

            with st.expander("Show source file mapping"):
                if "_source_file" in display_df.columns:
                    st.dataframe(display_df[["Record", "_source_file"]], use_container_width=True)
        else:
            st.info("No matches found.")

        st.write("---")
        st.markdown("### Touched schema / query lineage")

        touched_dot = build_touched_query_dot(
            criteria=st.session_state.active_criteria,
            outputs=st.session_state.active_output,
            sort_state=st.session_state.sort_state,
            advanced=st.session_state.active_advanced,
            mode="all",
            direction=SCHEMA_GRAPH_DIRECTION
        )
        st.graphviz_chart(touched_dot)

        with st.expander("Show touched paths as text", expanded=False):
            if st.session_state.active_criteria:
                st.markdown("**Filters**")
                for c in st.session_state.active_criteria:
                    cluster_label = display_cluster_label(c.get("cluster_path_str", "(no cluster)"))
                    st.write(
                        f"- {c.get('entry_name')} → {cluster_label} → {c.get('element_name')} "
                        f"[{c.get('operator')}] {c.get('value')}"
                    )

            if st.session_state.active_output:
                st.markdown("**Outputs**")
                for o in st.session_state.active_output:
                    cluster_label = display_cluster_label(o.get("cluster_path_str", "(no cluster)"))
                    st.write(
                        f"- {o.get('entry_name')} → {cluster_label} → {o.get('element_name')}"
                    )

            if st.session_state.sort_state:
                s = st.session_state.sort_state
                cluster_label = display_cluster_label(s.get("cluster_path_str", "(no cluster)"))
                st.markdown("**Sort**")
                st.write(
                    f"- {s.get('entry_name')} → {cluster_label} → {s.get('element_name')} ({s.get('direction')})"
                )

    else:
        st.info("Apply filters/output settings and click **Run Query** in the Advanced tab.")