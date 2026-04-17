# AQF Design System

This project now includes a reusable UI design system for Streamlit:

- `styles/design_tokens.py`: centralized color/spacing/typography tokens
- `styles/custom.css`: shared visual styles, responsive tweaks, transitions, focus states
- `utils/theme_manager.py`: theme state and safe CSS injection
- `utils/ui_helpers.py`: shared UI HTML generators
- `components/`: reusable cards, badges, funnel/table/query preview blocks
- `pages/`: page-level render helpers for header, query builder preview, and results

## Usage

```python
from ui_utils.theme_manager import inject_design_system, initialize_theme_state

initialize_theme_state()
inject_design_system()
```

## Tokens

Primary palette:

- Primary: `#0066CC`
- Secondary: `#7C3AED`
- Success: `#10B981`
- Warning: `#F59E0B`
- Danger: `#EF4444`

Typography:

- Heading: 24–30px bold
- Section title: 18px semibold
- Body: 14–16px regular
- Mono/code: JetBrains Mono 12px

Spacing:

- Horizontal section padding: 16px
- Vertical section gaps: 24px
- Component internal padding: 8px+

Accessibility:

- focus-visible outlines
- minimum touch target adjustments on mobile
- color-coded statuses with labels/icons
