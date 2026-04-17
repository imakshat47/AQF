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
from components.alert_box import render_alert_box
from components.metric_card import render_metric_card
from pages.header import render_header
from pages.layout import apply_design_system, initialize_theme_manager, section_close, section_open
from pages.query_builder import (
    render_advanced_controls,
    render_criteria_controls,
    render_field_cards_for_subgroup,
    render_output_controls,
    render_preview_panel,
    render_query_builder_header,
)
from pages.results import render_results_dashboard

st.set_page_config(page_title="🏥 AQF - openEHR Query Studio", layout="wide")

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
initialize_theme_manager()
apply_design_system()

section_open("Dataset Configuration")
dataset_exp = st.expander("Dataset path and composition setup", expanded=True)
with dataset_exp:
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

files_for_meta, _, _ = resolve_runtime_files_for_query(dataset_folder, comp_arch)
render_header(dataset_folder, comp_arch, len(files_for_meta), built_at)

# Top controls / quick actions
top1, top2, top3, top4 = st.columns([2, 1, 1, 1])
with top1:
    if st.button("Build / Refresh Schema", key="build_refresh_schema"):
        st.session_state.schema_build_token += 1
        build_or_refresh_schema()
with top2:
    if st.button("Reset Filters", key="reset_filters"):
        reset_filters()
with top3:
    if st.button("Reset Outputs", key="reset_outputs"):
        reset_outputs()
with top4:
    if st.button("Reset Query", key="reset_query"):
        reset_query_state()

with st.expander("Settings", expanded=False):
    st.selectbox("Theme mode", ["auto", "light", "dark"], key="aqf_theme_mode")
    st.caption("Theme mode is persisted in session state for future full light/dark integration.")

if st.button("Reset Schema Cache", key="reset_schema_cache"):
    reset_schema_cache()
    do_rerun()

# Cache banner
if st.session_state.schema_loaded_from_cache:
    if st.session_state.cache_loaded_without_validation:
        render_alert_box(
            "Loaded schema from `.cache` without validating the current dataset folder. "
            "Click **Build / Refresh Schema** if you want to validate/rebuild it.",
            kind="warning",
        )
    else:
        render_alert_box("Loaded schema from cache.", kind="success")

# Status banner
current_sig = signature_of_state(
    st.session_state.active_criteria,
    st.session_state.active_output,
    st.session_state.sort_state,
    st.session_state.active_advanced
)

if st.session_state.last_run_signature is None:
    render_alert_box("Form ready. Apply filters / output settings, then click **Run Query**.", kind="info")
elif st.session_state.last_run_signature != current_sig:
    render_alert_box("Form updated — click **Run Query** to execute the latest changes.", kind="warning")
else:
    render_alert_box("Showing results for the last executed query.", kind="success")

render_query_builder_header(
    st.session_state.active_criteria,
    st.session_state.active_output,
    st.session_state.sort_state
)

# Summary cards
groups_count, subgroups_count, fields_count, suggestion_fields_count, null_fields_count = count_summary(union, catalog)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    render_metric_card("Entry groups", groups_count, icon="📊", tone="neutral", caption="Schema sections")
with c2:
    render_metric_card("Cluster subgroups", subgroups_count, icon="📁", tone="neutral", caption="Nested clusters")
with c3:
    render_metric_card("Leaf fields", fields_count, icon="🏷️", tone="neutral", caption="Selectable fields")
with c4:
    render_metric_card("Fields with suggestions", suggestion_fields_count, icon="💡", tone="neutral", caption="Autocomplete ready")
with c5:
    render_metric_card("Unknown-capable fields", null_fields_count, icon="❔", tone="neutral", caption="Null flavour support")

with st.expander("Dataset diagnostics", expanded=False):
    st.write(f"Loaded composition archetype from schema: `{comp_arch}`")
    st.write(f"Current dataset folder: `{dataset_folder}`")
    if built_at:
        st.write(f"Schema build time: `{built_at}`")

with st.expander("Schema structure overview", expanded=False):
    dot = build_schema_flow_dot(
        union,
        max_depth=SCHEMA_OVERVIEW_MAX_DEPTH,
        direction=SCHEMA_GRAPH_DIRECTION,
        leaf_limit=SCHEMA_LEAF_LIMIT
    )
    st.graphviz_chart(dot)
section_close()

section_open("Query Builder")
left_col, right_col = st.columns([2, 1], gap="large")

with left_col:
    st.subheader(form["composition_label"])

    with st.form("query_builder_form"):
        search = render_criteria_controls(form)
        widget_meta = []

        for group in form["criteria_groups"]:
            with st.expander(group["group_label"], expanded=(group["group_label"] in ["HCPA", "Problem/Diagnosis"])):
                for subgroup in group["subgroups"]:
                    visible_fields = render_field_cards_for_subgroup(subgroup, search)
                    for fld in visible_fields:
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
                            st.selectbox("Operator", op_labels, key=op_key, help=fld["tooltip"])

                        with cols[2]:
                            mode = fld.get("suggestion_mode", "none")
                            suggestions = fld.get("suggested_values", [])
                            if mode in ("categorical", "boolean") and suggestions:
                                st.selectbox(
                                    "Value suggestions",
                                    ["<Enter custom value>"] + suggestions,
                                    key=suggest_key,
                                    help=fld["tooltip"]
                                )
                                st.text_input("Custom value", key=val_key)
                            elif mode == "boolean":
                                st.selectbox("Value", ["true", "false"], key=val_key, help=fld["tooltip"])
                            else:
                                st.text_input("Value", key=val_key, help=fld["tooltip"])

                        with cols[3]:
                            if fld.get("suggested_values"):
                                st.caption("Common values: " + ", ".join(fld["suggested_values"][:5]))
                            else:
                                st.caption("No cached suggestions yet.")

                        widget_meta.append(fld)

        apply_criteria = st.form_submit_button("➕ Add / Apply Filters")

        st.markdown("---")
        output_defs = form["output_fields"]
        default_output_labels = [x["name"] for x in st.session_state.active_output] if st.session_state.active_output else []
        selected_labels, sort_label, sort_dir, sort_choices = render_output_controls(output_defs, default_output_labels)
        apply_output = st.form_submit_button("Apply Output Settings")

        st.markdown("---")
        semantics, include_unknown, slice_size, result_limit = render_advanced_controls(
            st.session_state.active_advanced,
            DEFAULT_OCCURRENCE_SEMANTICS,
            DEFAULT_SLICE_SIZE,
            DEFAULT_RESULT_LIMIT
        )
        apply_advanced = st.form_submit_button("Apply Advanced Settings")
        run_query_clicked = st.form_submit_button("🚀 Run Query")

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
            op_obj = next((o for o in fld["operators"] if f"{o['phrase']} ({o['op']})" == op_choice), None)
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

            new_criteria.append({"field_key": fld["field_key"], "operator": op_obj["op"], "value": value})

        st.session_state.active_criteria = enrich_criteria(new_criteria, catalog)
        st.success("Filters applied.")

    if apply_output:
        selected_outputs = []
        for lbl in selected_labels:
            f = next((x for x in output_defs if x["label"] == lbl), None)
            if f:
                selected_outputs.append({"field_key": f["field_key"], "name": f["label"], "dv_type": f["dv_type"]})
        st.session_state.active_output = enrich_outputs(selected_outputs, catalog)
        if sort_label != "(none)":
            raw_sort = {"field_key": sort_choices[sort_label], "direction": sort_dir}
            st.session_state.sort_state = enrich_sort(raw_sort, catalog)
        else:
            st.session_state.sort_state = None
        st.success("Output settings applied.")

    if apply_advanced:
        st.session_state.active_advanced = {
            "occurrence_semantics": semantics,
            "include_unknown": include_unknown,
            "slice_size": slice_size,
            "result_limit": result_limit
        }
        st.success("Advanced settings applied.")

    if run_query_clicked:
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

with right_col:
    render_preview_panel(
        st.session_state.active_criteria,
        st.session_state.active_output,
        st.session_state.sort_state,
        union,
        catalog,
        st.session_state.last_run_result
    )

st.markdown("### Active Selection Tree")
criteria_tree = build_criteria_tree(st.session_state.active_criteria)
render_state_tree("Active Filters", criteria_tree)
output_tree = build_output_tree(st.session_state.active_output)
render_state_tree("Active Output Fields", output_tree)
sort_tree = build_sort_tree(st.session_state.sort_state)
render_state_tree("Active Sort", sort_tree)
advanced_tree = build_advanced_tree(st.session_state.active_advanced)
render_state_tree("Active Advanced Settings", advanced_tree)

section_close()

section_open("Results Dashboard")
if st.session_state.last_run_result:
    out = st.session_state.last_run_result
    display_df = None
    source_df = None
    if out["rows"]:
        full_df = format_results_for_display(out["rows"], st.session_state.active_output)
        visible_cols = [c for c in full_df.columns if c != "_source_file"]
        display_df = full_df[visible_cols]
        if "_source_file" in full_df.columns:
            source_df = full_df[["Record", "_source_file"]]

    query_summary_md = build_query_summary_markdown(
        st.session_state.active_criteria,
        st.session_state.active_output,
        st.session_state.sort_state,
        st.session_state.active_advanced
    )

    render_results_dashboard(out, query_summary_md, display_df, source_df)

    st.markdown("### Schema Lineage")
    touched_dot = build_touched_query_dot(
        criteria=st.session_state.active_criteria,
        outputs=st.session_state.active_output,
        sort_state=st.session_state.sort_state,
        advanced=st.session_state.active_advanced,
        mode="all",
        direction=SCHEMA_GRAPH_DIRECTION
    )
    st.graphviz_chart(touched_dot)

    with st.expander("Touched paths", expanded=False):
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
                st.write(f"- {o.get('entry_name')} → {cluster_label} → {o.get('element_name')}")

        if st.session_state.sort_state:
            s = st.session_state.sort_state
            cluster_label = display_cluster_label(s.get("cluster_path_str", "(no cluster)"))
            st.markdown("**Sort**")
            st.write(f"- {s.get('entry_name')} → {cluster_label} → {s.get('element_name')} ({s.get('direction')})")
else:
    st.info("Apply filters/output settings and click **Run Query** in the Query Builder section.")
section_close()
