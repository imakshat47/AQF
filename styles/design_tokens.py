"""AQF design tokens for colors, type, spacing, shadows, and theme variants."""

from __future__ import annotations

from dataclasses import dataclass

COLORS = {
    "primary": "#0066CC",
    "secondary": "#7C3AED",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
    "neutral": {
        "50": "#F9FAFB",
        "100": "#F3F4F6",
        "200": "#E5E7EB",
        "300": "#D1D5DB",
        "400": "#9CA3AF",
        "500": "#6B7280",
        "600": "#4B5563",
        "700": "#374151",
        "800": "#1F2937",
        "900": "#111827",
    },
}

TYPOGRAPHY = {
    "font_family": {
        "sans": "Inter, Poppins, Roboto, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "mono": "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace",
    },
    "sizes": {
        "xs": "12px",
        "sm": "14px",
        "base": "16px",
        "lg": "18px",
        "xl": "20px",
        "2xl": "24px",
        "3xl": "30px",
    },
    "weights": {"regular": 400, "medium": 500, "semibold": 600, "bold": 700},
    "line_height": {"tight": 1.2, "normal": 1.5, "relaxed": 1.7},
}

SPACING = {
    "0": "0px",
    "1": "4px",
    "2": "8px",
    "3": "12px",
    "4": "16px",
    "5": "24px",
    "6": "32px",
    "7": "48px",
    "8": "64px",
}

SIZING = {
    "xs": "20px",
    "sm": "24px",
    "md": "32px",
    "lg": "40px",
    "xl": "48px",
    "2xl": "56px",
    "3xl": "64px",
}

RADIUS = {
    "sm": "4px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "2xl": "20px",
    "full": "9999px",
}

SHADOWS = {
    "sm": "0 1px 2px rgba(17, 24, 39, 0.06)",
    "md": "0 6px 16px rgba(17, 24, 39, 0.08)",
    "lg": "0 12px 28px rgba(17, 24, 39, 0.10)",
    "xl": "0 20px 40px rgba(17, 24, 39, 0.12)",
}

TRANSITIONS = {
    "fast": "all 150ms ease",
    "base": "all 200ms ease",
    "slow": "all 300ms ease",
}

Z_INDEX = {
    "base": 0,
    "dropdown": 100,
    "sticky": 200,
    "overlay": 300,
    "modal": 400,
    "tooltip": 500,
}

THEMES = {
    "light": {
        "bg": COLORS["neutral"]["50"],
        "surface": "#FFFFFF",
        "text": COLORS["neutral"]["800"],
        "muted_text": COLORS["neutral"]["500"],
        "border": COLORS["neutral"]["200"],
    },
    "dark": {
        "bg": "#0F172A",
        "surface": "#111827",
        "text": "#E5E7EB",
        "muted_text": "#9CA3AF",
        "border": "#374151",
    },
}


@dataclass(frozen=True)
class ThemeTokens:
    mode: str
    bg: str
    surface: str
    text: str
    muted_text: str
    border: str


def get_theme_tokens(mode: str = "light") -> ThemeTokens:
    selected = THEMES.get(mode, THEMES["light"])
    return ThemeTokens(mode=mode, **selected)


def css_variables(mode: str = "light") -> dict[str, str]:
    theme = get_theme_tokens(mode)
    return {
        "--aqf-color-primary": COLORS["primary"],
        "--aqf-color-secondary": COLORS["secondary"],
        "--aqf-color-success": COLORS["success"],
        "--aqf-color-warning": COLORS["warning"],
        "--aqf-color-danger": COLORS["danger"],
        "--aqf-bg": theme.bg,
        "--aqf-surface": theme.surface,
        "--aqf-text": theme.text,
        "--aqf-muted-text": theme.muted_text,
        "--aqf-border": theme.border,
        "--aqf-radius": RADIUS["lg"],
        "--aqf-shadow": SHADOWS["md"],
    }
