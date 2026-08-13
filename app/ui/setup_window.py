"""First-launch vault creation screen."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton

from app.components.auth_widgets import PasswordInput, PasswordStrengthMeter
from app.security.password_strength import (
    assess_password_strength,
    validate_master_password,
)
from app.ui.auth_window import AuthWindow


class SetupWindow(AuthWindow):
    """Collects and validates a new master password."""

    create_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__(
            "Create your private vault",
            "Your passwords. Your device. Nothing leaves this computer.",
        )

        password_label = QLabel("Master password", objectName="authFieldLabel")
        self.password_input = PasswordInput("Enter at least 12 characters")
        confirm_label = QLabel("Confirm master password", objectName="authFieldLabel")
        self.confirm_input = PasswordInput("Enter it again")
        self.strength_meter = PasswordStrengthMeter()
        hint = QLabel(
            "Use a long, memorable passphrase. VaultKey cannot recover a forgotten master password.",
            objectName="authHint",
        )
        hint.setWordWrap(True)
        self.create_button = QPushButton("Create Vault", objectName="authPrimaryButton")
        self.create_button.setDefault(True)

        self.card_layout.addWidget(password_label)
        self.card_layout.addSpacing(7)
        self.card_layout.addWidget(self.password_input)
        self.card_layout.addSpacing(18)
        self.card_layout.addWidget(confirm_label)
        self.card_layout.addSpacing(7)
        self.card_layout.addWidget(self.confirm_input)
        self.card_layout.addSpacing(20)
        self.card_layout.addWidget(self.strength_meter)
        self.card_layout.addSpacing(16)
        self.card_layout.addWidget(hint)
        self.card_layout.addSpacing(18)
        self.card_layout.addWidget(self.error_label)
        self.card_layout.addSpacing(14)
        self.card_layout.addWidget(self.create_button)

        self.password_input.line_edit.textChanged.connect(self._password_changed)
        self.confirm_input.line_edit.textChanged.connect(self.clear_error)
        self.password_input.line_edit.returnPressed.connect(
            self.confirm_input.line_edit.setFocus
        )
        self.confirm_input.line_edit.returnPressed.connect(self._submit)
        self.create_button.clicked.connect(self._submit)

    def _password_changed(self, password: str) -> None:
        self.password_input.set_error(False)
        self.clear_error()
        self.strength_meter.update_strength(assess_password_strength(password))

    def _submit(self) -> None:
        password = self.password_input.text()
        confirmation = self.confirm_input.text()
        error = validate_master_password(password, confirmation)
        self.password_input.set_error(bool(error))
        self.confirm_input.set_error(bool(error))
        if error:
            self.show_error(error)
            return

        self.clear_error()
        self.set_busy(True)
        self.create_requested.emit(password)

    def set_busy(self, busy: bool) -> None:
        self.password_input.set_enabled(not busy)
        self.confirm_input.set_enabled(not busy)
        self.create_button.setEnabled(not busy)
        self.create_button.setText("Creating vault…" if busy else "Create Vault")

    def creation_failed(self, message: str) -> None:
        self.password_input.clear()
        self.confirm_input.clear()
        self.password_input.set_error(True)
        self.confirm_input.set_error(True)
        self.set_busy(False)
        self.show_error(message)
        self.password_input.line_edit.setFocus()
