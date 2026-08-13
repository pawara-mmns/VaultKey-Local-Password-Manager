"""Sensitive clipboard ownership and automatic clearing."""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer
from PySide6.QtGui import QClipboard


class ClipboardService(QObject):
    """Clear only a secret VaultKey still owns, never newer user clipboard data."""

    def __init__(self, clipboard: QClipboard, clear_seconds: int = 30) -> None:
        super().__init__()
        self.clipboard = clipboard
        self._owned_value: str | None = None
        self._clear_seconds = 30
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._clear_if_unchanged)
        self.set_clear_seconds(clear_seconds)

    @property
    def clear_seconds(self) -> int:
        return self._clear_seconds

    def set_clear_seconds(self, seconds: int) -> None:
        if seconds not in (10, 30, 60, 120, 0):
            raise ValueError("Unsupported clipboard timeout.")
        self._clear_seconds = seconds
        if self._owned_value is not None:
            self._timer.stop()
            if seconds:
                self._timer.start(seconds * 1000)

    def copy_sensitive(self, value: str) -> None:
        if not value:
            return
        self.clipboard.setText(value)
        self._timer.stop()
        self._owned_value = value
        if self._clear_seconds:
            self._timer.start(self._clear_seconds * 1000)

    def copy_text(self, value: str) -> None:
        self._timer.stop()
        self._owned_value = None
        self.clipboard.setText(value)

    def clear_owned(self) -> None:
        self._timer.stop()
        self._clear_if_unchanged()

    def _clear_if_unchanged(self) -> None:
        owned = self._owned_value
        self._owned_value = None
        if owned is not None and self.clipboard.text() == owned:
            self.clipboard.clear()
