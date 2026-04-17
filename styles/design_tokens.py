"""Centralized, platform-agnostic design tokens for AQF."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ThemeColors:
    """Theme-specific surface and background colors."""

    background: str
    surface: str
    text: str
    text_muted: str
    border: str


CORE_COLORS: Dict[str, str] = {
    "primary": "#0066CC",
    "secondary": "#7C3AED",
    "success": "#10B981",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

NEUTRAL_COLORS: Dict[str, str] = {
    "500": "#6B7280",
    "400": "#9CA3AF",
    "300": "#D1D5DB",
    "200": "#E5E7EB",
    "100": "#F3F4F6",
}

THEME_BASE_COLORS: Dict[str, Dict[str, str]] = {
    "background": {"light": "#FFFFFF", "dark": "#111827"},
    "surface": {"light": "#F9FAFB", "dark": "#1F2937"},
}

COLOR_PALETTE = {
    **CORE_COLORS,
    "neutral": NEUTRAL_COLORS,
    **THEME_BASE_COLORS,
}

THEME_COLORS = {
    "light": ThemeColors(
        background="#FFFFFF",
        surface="#F9FAFB",
        text="#111827",
        text_muted="#6B7280",
        border="#E5E7EB",
    ),
    "dark": ThemeColors(
        background="#111827",
        surface="#1F2937",
        text="#F9FAFB",
        text_muted="#D1D5DB",
        border="#374151",
    ),
}

TYPOGRAPHY = {
    "font_families": {
        "header": '"Poppins", "Inter", sans-serif',
        "body": '"Roboto", "Inter", sans-serif',
        "code": '"JetBrains Mono", monospace',
        "ui": '"Inter", sans-serif',
    },
    "font_sizes": {
        "xs": "12px",
        "sm": "14px",
        "base": "16px",
        "lg": "18px",
        "xl": "20px",
        "2xl": "24px",
        "3xl": "30px",
    },
    "font_weights": {
        "regular": 400,
        "medium": 500,
        "semibold": 600,
        "bold": 700,
    },
    "line_heights": {
        "tight": 1.25,
        "normal": 1.5,
        "relaxed": 1.625,
    },
}

SPACING = {
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
    "base": "32px",
    "lg": "40px",
    "xl": "48px",
    "2xl": "56px",
    "3xl": "64px",
}

BORDER_RADIUS = {
    "sm": "4px",
    "base": "6px",
    "md": "8px",
    "lg": "12px",
    "xl": "16px",
    "full": "9999px",
}

SHADOWS = {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.05)",
    "base": "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)",
}

TRANSITIONS = {
    "fast": "150ms",
    "base": "200ms",
    "slow": "300ms",
}

Z_INDEX = {
    "base": 0,
    "dropdown": 100,
    "sticky": 200,
    "fixed": 300,
    "modal": 400,
    "tooltip": 500,
}


def as_css_variables(theme: str = "light") -> str:
    """Export tokens as CSS custom properties for runtime injection."""
    selected_theme = THEME_COLORS.get(theme, THEME_COLORS["light"])
    neutral = COLOR_PALETTE["neutral"]

    css_vars = {
        "--aqf-color-primary": COLOR_PALETTE["primary"],
        "--aqf-color-secondary": COLOR_PALETTE["secondary"],
        "--aqf-color-success": COLOR_PALETTE["success"],
        "--aqf-color-warning": COLOR_PALETTE["warning"],
        "--aqf-color-danger": COLOR_PALETTE["danger"],
        "--aqf-color-neutral-500": neutral["500"],
        "--aqf-color-neutral-400": neutral["400"],
        "--aqf-color-neutral-300": neutral["300"],
        "--aqf-color-neutral-200": neutral["200"],
        "--aqf-color-neutral-100": neutral["100"],
        "--aqf-color-bg": selected_theme.background,
        "--aqf-color-surface": selected_theme.surface,
        "--aqf-color-text": selected_theme.text,
        "--aqf-color-text-muted": selected_theme.text_muted,
        "--aqf-color-border": selected_theme.border,
        "--aqf-font-header": TYPOGRAPHY["font_families"]["header"],
        "--aqf-font-body": TYPOGRAPHY["font_families"]["body"],
        "--aqf-font-code": TYPOGRAPHY["font_families"]["code"],
        "--aqf-radius-md": BORDER_RADIUS["md"],
        "--aqf-shadow-base": SHADOWS["base"],
        "--aqf-transition-base": TRANSITIONS["base"],
    }
    return "\n".join(f"{name}: {value};" for name, value in css_vars.items())
