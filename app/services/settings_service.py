"""Validated, non-sensitive application settings stored in SQLite."""

from __future__ import annotations

from dataclasses import dataclass
import sqlite3

from app.database.database import DatabaseError, DatabaseManager


AUTO_LOCK_OPTIONS = (1, 5, 10, 15, 30, 0)
CLIPBOARD_CLEAR_OPTIONS = (10, 30, 60, 120, 0)
APPEARANCE_OPTIONS = ("dark", "light", "system")


@dataclass(frozen=True, slots=True)
class AppSettings:
    auto_lock_minutes: int = 5
    clipboard_clear_seconds: int = 30
    appearance_mode: str = "dark"


class SettingsService:
    """Read and write allow-listed preferences; never stores secrets."""

    DEFAULTS = AppSettings()

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.ensure_defaults()

    def ensure_defaults(self) -> None:
        values = {
            "auto_lock_minutes": str(self.DEFAULTS.auto_lock_minutes),
            "clipboard_clear_seconds": str(self.DEFAULTS.clipboard_clear_seconds),
            "appearance_mode": self.DEFAULTS.appearance_mode,
        }
        try:
            with self.database.connection() as connection:
                connection.executemany(
                    "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
                    values.items(),
                )
        except (sqlite3.Error, OSError) as error:
            raise DatabaseError("Unable to initialize application settings.") from error

    def load(self) -> AppSettings:
        try:
            with self.database.connection() as connection:
                rows = connection.execute(
                    "SELECT key, value FROM app_settings"
                ).fetchall()
            values = {row["key"]: row["value"] for row in rows}
            auto_lock = int(values.get("auto_lock_minutes", "5"))
            clipboard = int(values.get("clipboard_clear_seconds", "30"))
            appearance = values.get("appearance_mode", "dark")
        except (ValueError, TypeError, sqlite3.Error):
            return self.DEFAULTS
        return AppSettings(
            auto_lock if auto_lock in AUTO_LOCK_OPTIONS else 5,
            clipboard if clipboard in CLIPBOARD_CLEAR_OPTIONS else 30,
            appearance if appearance in APPEARANCE_OPTIONS else "dark",
        )

    def set_auto_lock_minutes(self, value: int) -> None:
        self._set_choice("auto_lock_minutes", value, AUTO_LOCK_OPTIONS)

    def set_clipboard_clear_seconds(self, value: int) -> None:
        self._set_choice("clipboard_clear_seconds", value, CLIPBOARD_CLEAR_OPTIONS)

    def set_appearance_mode(self, value: str) -> None:
        self._set_choice("appearance_mode", value, APPEARANCE_OPTIONS)

    def _set_choice(self, key: str, value: object, allowed: tuple[object, ...]) -> None:
        if value not in allowed:
            raise ValueError(f"Unsupported setting value for {key}.")
        try:
            with self.database.connection() as connection:
                connection.execute(
                    """
                    INSERT INTO app_settings (key, value) VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET value = excluded.value
                    """,
                    (key, str(value)),
                )
        except sqlite3.Error as error:
            raise DatabaseError("Unable to save application settings.") from error
