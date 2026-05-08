# AQF Final EHR Support Files

This package contains the final files for AQF v2.1.1 EHR/composition ingestion support.

## Files

- `aqf_v2_1_1.py` — Streamlit AQF app with record-family detection and EHR-aware ingestion integration.
- `record_unit_loader.py` — EHR/composition normalization layer with parser-registry support, EHR index/reference parsing, reference resolution, and materialization.
- `parser_mappings.json` — Declarative parser mapping/registry for supported JSON shapes.
- `config.py` — Updated config with record-unit cache, parser mapping, and EHR support settings.

## Run

```bash
streamlit run aqf_v2_1_1.py
```

## Recommended workflow

1. Confirm the dataset folder path in the sidebar.
2. Click **Detect record families**.
3. Select the target record family.
4. Click **Build / Refresh Schema**.
5. Use the generated AQF form and click **Search**.

## Notes

- Standalone composition JSONs remain supported.
- EHR JSONs with inline compositions are supported.
- EHR index/reference JSONs are supported as metadata records and can resolve referenced VERSIONED_COMPOSITION files if those files exist in the dataset folder.
- Extracted record units are materialized under `.cache/record_units` so the existing query executor can keep working without a rewrite.
