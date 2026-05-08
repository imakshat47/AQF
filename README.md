# AQF UI Starter

This is a polished **UI/UX starter package** for AQF based on the design-system and Streamlit theming plan.

## Included
- `.streamlit/config.toml` — minimalist Streamlit theme
- `assets/aqf.css` — AQF design-system CSS
- `assets/aqf_logo.svg` — simple placeholder AQF logo mark
- `ui/theme.py` — theme tokens and helper values
- `ui/css.py` — CSS loading helper
- `ui/icons.py` — icon/symbol mapping
- `ui/components.py` — reusable UI helpers (cards, chips, badges, summaries)
- `config.py` — app-level configuration defaults
- `app.py` — minimal demo shell using the design system

## Quick start
```bash
streamlit run app.py
```

## Notes
- This is a **starter scaffold**, not the full AQF product.
- It is designed so you can progressively merge it into your current AQF app.
- The `app.py` file demonstrates:
  - brand header
  - stepper
  - query summary box
  - chips
  - preview / warning / success cards
  - example result cards

## Recommended next integration steps
1. Move your current AQF backend logic into this shell.
2. Replace the mock data in `app.py` with real AQF state.
3. Reuse `ui/components.py` to keep styling consistent.
4. Expand result rendering with your table/card toggle and lazy loading.
5. Add beginner/expert mode and live preview.


# AQF v2 — Adaptive Query Forms for Hierarchical Healthcare Data

AQF (**Adaptive Query Forms**) is an **automatic query form generation system** for hierarchical standardized healthcare records. Instead of requiring users to know a query language or hidden structural paths inside complex healthcare data, AQF automatically generates a structured query interface from the **schema and content** of the dataset itself. The goal is to make querying possible, understandable, and progressively refinable even when the underlying records are deeply nested and semantically rich.

This repository contains the **single-page AQF v2 Streamlit application**, centered around `app_v2.py`. The v2 interface is not a generic manual query builder. It deliberately preserves the core AQF idea:

- the query interface is **generated automatically**
- the user interacts with the **generated AQF form**
- the system compiles the form state into an executable query
- the interface then helps the user understand the result through summaries, funneling, and structural explanation

In this sense, AQF v2 is both:
1. an **automatic query form generation interface**, and  
2. a more **polished product-like user experience** built around that generated form.

---

## 1. Project philosophy

AQF is not intended to be a freeform search console where users manually assemble arbitrary fields from a dropdown list. That would move the system away from its research and product identity. Instead, AQF generates the form itself from the data and then presents that generated structure in a cleaner, more intuitive way.

The design direction behind AQF v2 is:

> **Keep the generated AQF form as the core interaction model, but make that generated form much easier, cleaner, and more intuitive for an end user to use.**

This means:

- **Do not replace AQF with a generic search builder**
- **Do preserve generated sections, subgroup paths, and fields**
- **Do improve layout, readability, action placement, result presentation, and explainability**

AQF v2 therefore represents a UX redesign of the generated AQF form, not a departure from AQF’s automatic form-generation principle.

---

## 2. What AQF solves

Modern healthcare records are often:

- hierarchical
- semantically rich
- deeply nested
- difficult to query for non-technical users

Traditional query interfaces often fail because users must know:
- the backend query language
- the hidden schema
- where in the hierarchy the desired field lives
- how multiple constraints interact

AQF addresses this by:

1. analyzing the structure of the dataset,
2. generating a usable form automatically,
3. exposing filtering, output, and ordering options through that generated form,
4. executing the query over the dataset,
5. and explaining what happened — especially when a query becomes too restrictive.

---

## 3. What changed in AQF v2

The original AQF interface (v1) already had the right backend logic, but the user experience was still rough and developer-oriented. The v2 redesign focuses on **usability and product feel** while preserving the generated-form model.

### Major UX changes introduced in v2
- **Single-page search workspace** instead of multi-tab hopping
- **Sticky natural-language query summary** at the top
- **Collapsible “Filters” section**
- **Collapsible “Results to show” section**
- **Collapsible “More options” section**
- **Search actions placed clearly after configuration panels**
- **Dismissible chips** for:
  - active filters
  - selected result fields
  - sort state
- **Cards as the default result view**
- **Table view as an optional alternative**
- **Lazy loading for cards and table rows**
- **Query funnel toggle**
- **Explainability toggle**
- **No-result guidance**
- **Minimalist clinical design system**

These changes are intended to make AQF feel less like a research prototype and more like a polished search product, without changing its core generated-form logic.

---

## 4. Main interface structure

The AQF v2 page is organized as a **single continuous search workspace**:

1. **Sticky query summary**
2. **Quick state chips**
3. **Schema overview (optional)**
4. **Filters** (collapsible)
5. **Results to show** (collapsible)
6. **More options** (collapsible)
7. **Search actions**
8. **Results**
9. **Query funnel** (optional)
10. **Explainability** (optional)

This structure is intended to reflect a natural end-user flow:

> configure → review → search → inspect → refine

---

## 5. AQF v2 UI/UX design decisions

This section documents the design rationale we established for AQF in this project.

### 5.1 Keep the generated form
AQF is an **automatic query form generation** system. Therefore, the main interaction should remain the generated form itself. The interface should not be reduced to a generic builder with arbitrary dropdowns and ad hoc field selection. Instead, the generated groups and fields should remain visible and interpretable.

### 5.2 Use a single-page workspace
Rather than forcing users to switch between technical tabs such as Criteria, Output, Advanced, and Results, AQF v2 keeps everything on one page and uses collapsible sections to manage complexity.

### 5.3 Keep the natural-language summary always visible
The natural-language query summary is one of AQF’s strongest features. It helps users understand:
- what they are searching for
- what fields will be shown
- what ordering is active
- what execution settings are in effect

To reinforce that, AQF v2 keeps the summary in a sticky top bar.

### 5.4 Make active state controllable
Users should not have to hunt through the form to remember or undo what they have already selected. That is why AQF v2 uses dismissible chips for:
- active filters
- selected result fields
- sort settings

### 5.5 Cards first, tables optional
Healthcare query results are often easier to interpret in a card-based presentation than in a wide spreadsheet-like table. AQF v2 therefore defaults to cards, while still allowing table mode for denser inspection.

### 5.6 Explainability is optional but important
The interface should stay clean for new users, so explainability artifacts such as touched-schema graphs and query funneling are hidden behind explicit actions. But they remain essential AQF features, especially for:
- understanding no-result cases
- understanding the narrowing effect of multiple constraints
- preserving trust in the generated form

---

## 6. Architecture overview

`app_v2.py` is primarily a **frontend shell** over the existing AQF backend modules. The AQF engine remains in the supporting Python modules, while `app_v2.py` focuses on rendering and orchestration.

### Backend modules expected
The app imports and relies on:

- `config.py`
- `composition_loader.py`
- `schema_union_builder.py`
- `field_catalog.py`
- `form_definition_builder.py`
- `query_compiler.py`
- `query_executor.py`
- `result_formatter.py`
- `schema_diagram.py`
- `query_summary.py`

### Backend responsibilities
These modules are responsible for:
- loading hierarchical healthcare records
- grouping documents by composition archetype
- building the union schema
- building the field catalog
- generating the AQF form definition
- compiling the user’s form state into a query plan
- running the query over the data
- formatting the results
- building schema and touched-query diagrams
- generating natural-language query summaries

---

## 7. Expected project structure

A typical AQF project structure for this app is:

```text
project/
├── app_v2.py
├── config.py
├── composition_loader.py
├── schema_union_builder.py
├── field_catalog.py
├── form_definition_builder.py
├── query_compiler.py
├── query_executor.py
├── result_formatter.py
├── schema_diagram.py
├── query_summary.py
├── data/
└── .cache/