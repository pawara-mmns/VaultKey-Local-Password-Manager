"""Reusable widgets shared by the setup and unlock screens."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.config import EYE_ICON_PATH, EYE_OFF_ICON_PATH
from app.security.password_strength import StrengthResult


class PasswordInput(QFrame):
    """Styled password field with a local show/hide icon."""

    def __init__(self, placeholder: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("passwordInput")
        self.setProperty("error", False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(8)

        self.line_edit = QLineEdit(objectName="passwordLineEdit")
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.line_edit.setClearButtonEnabled(False)
        self.line_edit.installEventFilter(self)

        self.visibility_button = QToolButton(objectName="visibilityButton")
        self.visibility_button.setCheckable(True)
        self.visibility_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.visibility_button.setToolTip("Show password")
        self.visibility_button.setAccessibleName("Show password")
        self.visibility_button.setIcon(QIcon(str(EYE_ICON_PATH)))
        self.visibility_button.setIconSize(QSize(18, 18))
        self.visibility_button.toggled.connect(self._toggle_visibility)

        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.visibility_button)

    def text(self) -> str:
        return self.line_edit.text()

    def clear(self) -> None:
        self.line_edit.clear()

    def set_error(self, has_error: bool) -> None:
        self.setProperty("error", has_error)
        self.style().unpolish(self)
        self.style().polish(self)

    def set_enabled(self, enabled: bool) -> None:
        self.line_edit.setEnabled(enabled)
        self.visibility_button.setEnabled(enabled)

    def _toggle_visibility(self, visible: bool) -> None:
        self.line_edit.setEchoMode(
            QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password
        )
        icon_path = EYE_OFF_ICON_PATH if visible else EYE_ICON_PATH
        action = "Hide password" if visible else "Show password"
        self.visibility_button.setIcon(QIcon(str(icon_path)))
        self.visibility_button.setToolTip(action)
        self.visibility_button.setAccessibleName(action)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.line_edit and event.type() in (
            QEvent.Type.FocusIn,
            QEvent.Type.FocusOut,
        ):
            self.setProperty("focused", event.type() == QEvent.Type.FocusIn)
            self.style().unpolish(self)
            self.style().polish(self)
        return super().eventFilter(watched, event)


class PasswordStrengthMeter(QWidget):
    """Compact five-level password strength indicator."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        heading = QHBoxLayout()
        title = QLabel("Password strength", objectName="authFieldLabel")
        self.label = QLabel("Very Weak", objectName="strengthLabel")
        self.label.setProperty("strength", 0)
        heading.addWidget(title)
        heading.addStretch(1)
        heading.addWidget(self.label)

        self.bar = QProgressBar(objectName="strengthBar")
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setProperty("strength", 0)

        layout.addLayout(heading)
        layout.addWidget(self.bar)

    def update_strength(self, result: StrengthResult) -> None:
        self.label.setText(result.label)
        self.label.setProperty("strength", result.level)
        self.bar.setProperty("strength", result.level)
        self.bar.setValue(result.percent if result.percent > 0 else 0)
        for widget in (self.label, self.bar):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
