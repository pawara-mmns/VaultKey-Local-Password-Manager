"""Existing-vault unlock screen."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton

from app.components.auth_widgets import PasswordInput
from app.ui.auth_window import AuthWindow


class UnlockWindow(AuthWindow):
    """Collects the master password for a configured local vault."""

    unlock_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__("Welcome back", "Enter your master password to unlock your local vault.")

        password_label = QLabel("Master password", objectName="authFieldLabel")
        self.password_input = PasswordInput("Enter your master password")
        self.unlock_button = QPushButton("Unlock Vault", objectName="authPrimaryButton")
        self.unlock_button.setDefault(True)

        self.card_layout.addWidget(password_label)
        self.card_layout.addSpacing(7)
        self.card_layout.addWidget(self.password_input)
        self.card_layout.addSpacing(18)
        self.card_layout.addWidget(self.error_label)
        self.card_layout.addSpacing(14)
        self.card_layout.addWidget(self.unlock_button)

        self.password_input.line_edit.textChanged.connect(self._input_changed)
        self.password_input.line_edit.returnPressed.connect(self._submit)
        self.unlock_button.clicked.connect(self._submit)

    def _input_changed(self) -> None:
        self.password_input.set_error(False)
        self.clear_error()

    def _submit(self) -> None:
        password = self.password_input.text()
        if not password:
            self.password_input.set_error(True)
            self.show_error("Enter your master password.")
            return
        self.clear_error()
        self.set_busy(True)
        self.unlock_requested.emit(password)

    def set_busy(self, busy: bool) -> None:
        self.password_input.set_enabled(not busy)
        self.unlock_button.setEnabled(not busy)
        self.unlock_button.setText("Unlocking…" if busy else "Unlock Vault")

    def unlock_failed(self, message: str = "Incorrect master password.") -> None:
        self.password_input.clear()
        self.password_input.set_error(True)
        self.set_busy(False)
        self.show_error(message)
        self.password_input.line_edit.setFocus()

    def set_unavailable(self, message: str) -> None:
        self.password_input.clear()
        self.password_input.set_error(True)
        self.password_input.set_enabled(False)
        self.unlock_button.setEnabled(False)
        self.show_error(message)
