# AQF Design System

## 1) Design Tokens

### Colors
- Primary: `#0066CC`
- Secondary: `#7C3AED`
- Success: `#10B981`
- Warning: `#F59E0B`
- Danger: `#EF4444`
- Neutral scale: `#6B7280`, `#9CA3AF`, `#D1D5DB`, `#E5E7EB`, `#F3F4F6`
- Background: light `#FFFFFF`, dark `#111827`
- Surface: light `#F9FAFB`, dark `#1F2937`

### Typography
- Font families:
  - Headers: Poppins, Inter
  - Body: Roboto, Inter
  - Code: JetBrains Mono
- Font sizes: xs `12px`, sm `14px`, base `16px`, lg `18px`, xl `20px`, 2xl `24px`, 3xl `30px`
- Font weights: regular `400`, medium `500`, semibold `600`, bold `700`
- Line heights: tight `1.25`, normal `1.5`, relaxed `1.625`

### Spacing
- 1=`4px`, 2=`8px`, 3=`12px`, 4=`16px`, 5=`24px`, 6=`32px`, 7=`48px`, 8=`64px`

### Sizing
- xs `20px`, sm `24px`, base `32px`, lg `40px`, xl `48px`, 2xl `56px`, 3xl `64px`

### Border Radius
- sm `4px`, base `6px`, md `8px`, lg `12px`, xl `16px`, full `9999px`

### Shadows
- sm: `0 1px 2px 0 rgba(0, 0, 0, 0.05)`
- base: `0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)`
- md: `0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)`
- lg: `0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)`
- xl: `0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)`

### Motion and Layering
- Transition durations: fast `150ms`, base `200ms`, slow `300ms`
- Z-index: base `0`, dropdown `100`, sticky `200`, fixed `300`, modal `400`, tooltip `500`

---

## 2) Component Usage Patterns

### Status badge
```python
from utils.ui_helpers import status_badge
status_badge("Ready", tone="success", icon="✅")
```

### Metric card
```python
from utils.ui_helpers import metric_card
metric_card("Matched Records", "245", "After filters", tone="primary")
```

### Alert box
```python
from utils.ui_helpers import alert_box
alert_box("Schema cache is outdated.", tone="warning", title="Attention")
```

### Chip / tag
```python
from utils.ui_helpers import chip
chip("Age ≥ 65")
```

---

## 3) Color Palette Showcase and Use Cases

- **Primary (`#0066CC`)**: primary actions, focus states, links
- **Secondary (`#7C3AED`)**: lineage visualization, advanced interactions
- **Success (`#10B981`)**: ready state, successful execution
- **Warning (`#F59E0B`)**: caution, stale cache, partial data
- **Danger (`#EF4444`)**: errors, destructive actions
- **Neutral scale**: surfaces, borders, muted text

These choices support high contrast and healthcare-oriented clarity.

---

## 4) Typography Guidelines

- Use header font for page and card titles.
- Use body font for inputs, labels, table text, and descriptions.
- Use mono font for generated query snippets and code-like data.
- Keep body text at `16px` default; only reduce to `14px` for dense metadata.

---

## 5) Spacing and Sizing Reference

- Use spacing scale only (`4-64px`) to keep rhythm consistent.
- Card padding defaults to `16px` (`space-4`).
- Section spacing defaults to `24px` (`space-5`).
- Touch targets should be at least `32px` (`size-base`) height.

---

## 6) Accessibility Guidelines

- Maintain strong contrast for text over background/surface.
- Preserve visible keyboard focus (`:focus-visible` outline).
- Respect `prefers-reduced-motion` for users sensitive to animation.
- Use semantic tone mapping for alerts and statuses.

---

## 7) Common Integration Patterns

### App bootstrap
```python
from config import CUSTOM_CSS_FILE
from utils.theme_manager import initialize_ui

initialize_ui(CUSTOM_CSS_FILE)
```

### Theme toggle
```python
from utils.theme_manager import toggle_theme

if st.button("Toggle theme"):
    toggle_theme()
    st.rerun()
```

### Token usage in Python
```python
from styles.design_tokens import COLOR_PALETTE, SPACING

primary = COLOR_PALETTE["primary"]
padding = SPACING["4"]
```
