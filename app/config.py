"""Central application metadata, dimensions, and theme values."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "VaultKey"
ORGANIZATION_NAME = "VaultKey"
APP_VERSION = "0.5.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = PROJECT_ROOT / "styles"
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "vault.db"
WINDOW_ICON_PATH = ASSETS_DIR / "icons" / "vaultkey.svg"
EYE_ICON_PATH = ASSETS_DIR / "icons" / "eye.svg"
EYE_OFF_ICON_PATH = ASSETS_DIR / "icons" / "eye-off.svg"

WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
WINDOW_START_WIDTH = 1280
WINDOW_START_HEIGHT = 800
SIDEBAR_WIDTH = 248

DARK_COLORS = {
    "background": "#0D0F12",
    "sidebar": "#12151A",
    "card": "#171A20",
    "card_hover": "#1D2129",
    "primary": "#6C5CE7",
    "primary_hover": "#7D6EF0",
    "text": "#F5F7FA",
    "text_secondary": "#8B93A1",
    "border": "#252A33",
    "success": "#2ECC71",
    "warning": "#F4B942",
    "danger": "#FF5C5C",
}

LIGHT_COLORS = {
    "background": "#F4F6FA",
    "sidebar": "#FFFFFF",
    "card": "#FFFFFF",
    "card_hover": "#F0F2F7",
    "primary": "#6252D6",
    "primary_hover": "#5545C5",
    "text": "#1B1E27",
    "text_secondary": "#687082",
    "border": "#DDE1EA",
    "success": "#188A4B",
    "warning": "#A66B00",
    "danger": "#D94040",
}

COLORS = DARK_COLORS


def load_stylesheet(appearance: str = "dark", *, system_is_dark: bool = True) -> str:
    """Load a tokenized theme; ``system`` is resolved by the controller."""
    resolved = (
        "dark" if system_is_dark else "light"
    ) if appearance == "system" else appearance
    if resolved not in ("dark", "light"):
        resolved = "dark"
    colors = DARK_COLORS if resolved == "dark" else LIGHT_COLORS
    stylesheet_path = STYLES_DIR / "dark.qss"
    stylesheet = stylesheet_path.read_text(encoding="utf-8")
    stylesheet = stylesheet.format_map(colors)
    if resolved == "light":
        replacements = {
            "#101216": "#F8F9FC",
            "#111318": "#F7F8FB",
            "#0F1115": "#F9FAFC",
            "#13161B": "#F4F5F8",
            "#15181E": "#F1F3F7",
            "#1B1F26": "#EBEEF4",
            "#222730": "#E3E7EF",
            "#252A34": "#DCE1EA",
            "#272C35": "#E5E8EF",
            "#343B48": "#C8CEDA",
            "#3A4250": "#B9C1CF",
            "#BEB6FF": "#5142BC",
            "#A99EFF": "#5D4BC8",
            "#FF8B8B": "#C73737",
        }
        for dark, light in replacements.items():
            stylesheet = stylesheet.replace(dark, light)
        light_overrides = (STYLES_DIR / "light.qss").read_text(encoding="utf-8")
        stylesheet += "\n" + light_overrides.format_map(colors)
    return stylesheet
