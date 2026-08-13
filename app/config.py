"""Central application metadata, dimensions, and theme values."""

from __future__ import annotations

from pathlib import Path

APP_NAME = "VaultKey"
ORGANIZATION_NAME = "VaultKey"
APP_VERSION = "0.1.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
STYLES_DIR = PROJECT_ROOT / "styles"
ASSETS_DIR = PROJECT_ROOT / "assets"
WINDOW_ICON_PATH = ASSETS_DIR / "icons" / "vaultkey.svg"

WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
WINDOW_START_WIDTH = 1280
WINDOW_START_HEIGHT = 800
SIDEBAR_WIDTH = 248

COLORS = {
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


def load_stylesheet() -> str:
    """Load the dark QSS theme and inject centralized color tokens."""
    stylesheet_path = STYLES_DIR / "dark.qss"
    stylesheet = stylesheet_path.read_text(encoding="utf-8")
    return stylesheet.format_map(COLORS)
