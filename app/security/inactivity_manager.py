"""Application-wide inactivity tracking for automatic vault locking."""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtCore import QEvent, QObject, QTimer, Signal


class InactivityManager(QObject):
    lock_requested = Signal()

    ACTIVITY_EVENTS = {
        QEvent.Type.KeyPress,
        QEvent.Type.MouseButtonPress,
        QEvent.Type.MouseButtonRelease,
        QEvent.Type.MouseMove,
        QEvent.Type.Wheel,
        QEvent.Type.TouchBegin,
        QEvent.Type.WindowActivate,
    }

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        super().__init__()
        self._clock = clock
        self._timeout_seconds = 0.0
        self._last_activity = 0.0
        self._active = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._check_timeout)

    def configure_minutes(self, minutes: int) -> None:
        if minutes not in (1, 5, 10, 15, 30, 0):
            raise ValueError("Unsupported auto-lock timeout.")
        self._timeout_seconds = float(minutes * 60)
        if self._active:
            self.record_activity()

    def start(self) -> None:
        self._active = True
        self.record_activity()

    def stop(self) -> None:
        self._active = False
        self._timer.stop()

    def record_activity(self) -> None:
        if not self._active:
            return
        self._last_activity = self._clock()
        self._timer.stop()
        if self._timeout_seconds:
            self._timer.start(max(1, int(self._timeout_seconds * 1000)))

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if self._active and event.type() in self.ACTIVITY_EVENTS:
            now = self._clock()
            if self._timeout_seconds and now - self._last_activity >= self._timeout_seconds:
                self.stop()
                self.lock_requested.emit()
            else:
                self.record_activity()
        return False

    def _check_timeout(self) -> None:
        if not self._active or not self._timeout_seconds:
            return
        elapsed = self._clock() - self._last_activity
        if elapsed >= self._timeout_seconds:
            self.stop()
            self.lock_requested.emit()
            return
        self._timer.start(max(1, int((self._timeout_seconds - elapsed) * 1000)))
