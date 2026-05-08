# AQF Auto Parser Final Files

This package adds an **auto parser discovery layer** to AQF while preserving the existing AQF v2 generated-form and query pipeline.

## Files added or changed

### Changed
- `aqf_v2_1_2_auto_parser.py` — AQF app with parser scan/generation UI and JSON type selection.
- `record_unit_loader.py` — registry-aware record-unit loader that parses selected JSON types.
- `config.py` — adds parser discovery, generated parser registry, and EHR/reference-resolution settings.
- `parser_mappings.json` — base/manual parser registry.

### Added
- `json_profiler.py` — scans JSON structure, paths, markers, and fingerprints.
- `parser_registry.py` — loads/merges parser mappings and matches profiles to parsers.
- `parser_discovery.py` — scans dataset, clusters unknown structures, generates parser candidates.
- `record_family_index.py` — convenience wrappers for record-family and JSON-type summaries.

## How the new pipeline works

```text
Dataset folder
→ json_profiler profiles every JSON file
→ parser_registry matches known parser mappings
→ parser_discovery clusters unknown JSON shapes and generates parser candidates
→ generated parser registry is saved under .cache/parser_mappings.generated.json
→ user selects JSON types to include
→ record_unit_loader extracts AQF record units only from selected JSON types
→ user selects record family
→ existing AQF form generation and query execution run unchanged
```

## Recommended run workflow

```bash
streamlit run aqf_v2_1_2_auto_parser.py
```

Then:

1. Set dataset folder in the sidebar.
2. Click **Scan dataset / generate parser registry**.
3. Review detected JSON types.
4. Select JSON types to include.
5. Click **Detect record families**.
6. Select target record family.
7. Click **Build / Refresh Schema**.
8. Use the generated AQF form and click **Search**.

## Important design decision

Parser discovery does **not** directly create query forms. Parser discovery creates/selects **record units**. AQF still generates query forms from selected **record families**.

This keeps the architecture clean:

```text
Parser system = understand files
AQF system = generate and execute query forms
```

## Existing AQF core unchanged

The following modules do not need changes for this phase:

- `schema_union_builder.py`
- `field_catalog.py`
- `form_definition_builder.py`
- `query_compiler.py`
- `query_executor.py`
- `result_formatter.py`
- `schema_diagram.py`
- `query_summary.py`

The executor still receives materialized JSON files under `.cache/record_units`, so no executor rewrite is required.
