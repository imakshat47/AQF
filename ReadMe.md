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
