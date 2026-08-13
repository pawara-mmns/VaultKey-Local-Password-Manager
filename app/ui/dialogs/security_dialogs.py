"""Security-sensitive confirmation dialogs used by Settings."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.components.auth_widgets import PasswordInput, PasswordStrengthMeter
from app.security.password_strength import assess_password_strength


class _SecurityDialog(QDialog):
    def __init__(self, title: str, subtitle: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("securityDialog")
        self.setModal(True)
        self.setWindowTitle(title)
        self.setMinimumWidth(500)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 25, 28, 25)
        self.layout.setSpacing(12)
        self.layout.addWidget(QLabel(title, objectName="dialogTitle"))
        description = QLabel(subtitle, objectName="dialogSubtitle")
        description.setWordWrap(True)
        self.layout.addWidget(description)
        self.error = QLabel(objectName="dialogError")
        self.error.setWordWrap(True)
        self.error.hide()

    def add_password(self, label: str, placeholder: str) -> PasswordInput:
        self.layout.addWidget(QLabel(label, objectName="dialogFieldLabel"))
        field = PasswordInput(placeholder)
        self.layout.addWidget(field)
        return field

    def finish(self, accept_text: str, *, danger: bool = False) -> QPushButton:
        self.layout.addWidget(self.error)
        row = QHBoxLayout()
        cancel = QPushButton("Cancel", objectName="dialogSecondaryButton")
        accept = QPushButton(
            accept_text, objectName="dangerButton" if danger else "primaryButton"
        )
        cancel.clicked.connect(self.reject)
        row.addStretch(1)
        row.addWidget(cancel)
        row.addWidget(accept)
        self.layout.addLayout(row)
        return accept

    def show_error(self, message: str) -> None:
        self.error.setText(message)
        self.error.show()


class ChangeMasterPasswordDialog(_SecurityDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(
            "Change master password",
            "Every stored credential will be re-encrypted. You will be locked afterward.",
            parent,
        )
        self.current = self.add_password("Current master password", "Current password")
        self.new = self.add_password("New master password", "At least 12 characters")
        self.confirm = self.add_password("Confirm new master password", "Enter it again")
        self.strength = PasswordStrengthMeter()
        self.layout.addWidget(self.strength)
        self.new.line_edit.textChanged.connect(
            lambda value: self.strength.update_strength(assess_password_strength(value))
        )
        submit = self.finish("Change Password")
        submit.clicked.connect(self._submit)

    def _submit(self) -> None:
        if not self.current.text() or not self.new.text() or not self.confirm.text():
            self.show_error("Complete all password fields.")
            return
        self.accept()

    def values(self) -> tuple[str, str, str]:
        return self.current.text(), self.new.text(), self.confirm.text()

    def wipe_sensitive(self) -> None:
        self.current.clear()
        self.new.clear()
        self.confirm.clear()


class MasterPasswordDialog(_SecurityDialog):
    def __init__(self, title: str, subtitle: str, action: str, parent=None) -> None:
        super().__init__(title, subtitle, parent)
        self.password = self.add_password("Master password", "Enter your master password")
        submit = self.finish(action)
        submit.clicked.connect(lambda: self.accept() if self.password.text() else self.show_error("Enter your master password."))

    def wipe_sensitive(self) -> None:
        self.password.clear()


class ResetVaultDialog(_SecurityDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(
            "Reset Vault",
            "This permanently deletes local credentials and settings. Existing backup files are not deleted.",
            parent,
        )
        self.password = self.add_password("Master password", "Enter your master password")
        self.layout.addWidget(QLabel('Type "RESET" to confirm', objectName="dialogFieldLabel"))
        self.confirmation = QLineEdit(objectName="dialogInput")
        self.confirmation.setPlaceholderText("RESET")
        self.layout.addWidget(self.confirmation)
        submit = self.finish("Reset Vault", danger=True)
        submit.setEnabled(False)
        self.confirmation.textChanged.connect(
            lambda value: submit.setEnabled(value == "RESET")
        )
        submit.clicked.connect(self._submit)

    def _submit(self) -> None:
        if not self.password.text():
            self.show_error("Enter your master password.")
        elif self.confirmation.text() != "RESET":
            self.show_error('Type "RESET" exactly to confirm.')
        else:
            self.accept()

    def wipe_sensitive(self) -> None:
        self.password.clear()
        self.confirmation.clear()


class RestoreConfirmationDialog(_SecurityDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(
            "Restore this backup?",
            "Your current vault will be replaced with the selected backup. A temporary safety copy will be created before restoring.",
            parent,
        )
        restore = self.finish("Restore", danger=True)
        restore.clicked.connect(self.accept)


class MessageDialog(_SecurityDialog):
    def __init__(self, title: str, message: str, parent=None, *, danger: bool = False) -> None:
        super().__init__(title, message, parent)
        row = QHBoxLayout()
        close = QPushButton(
            "Close", objectName="dangerButton" if danger else "primaryButton"
        )
        close.clicked.connect(self.accept)
        row.addStretch(1)
        row.addWidget(close)
        self.layout.addLayout(row)
