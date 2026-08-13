"""Shared add/edit credential form."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.components.auth_widgets import PasswordInput
from app.database.models import Category, CredentialDetail, CredentialDraft
from app.security.password_generator import DEFAULT_PASSWORD_LENGTH, PasswordGenerator


class CredentialDialog(QDialog):
    """Collect a validated plaintext draft for immediate encrypted persistence."""

    def __init__(
        self,
        categories: list[Category],
        *,
        credential: CredentialDetail | None = None,
        prefilled_password: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("credentialDialog")
        self.setModal(True)
        self.setWindowTitle("Edit Credential" if credential else "Add Password")
        self.setMinimumWidth(560)
        self._existing = credential
        self._draft: CredentialDraft | None = None
        self._generator = PasswordGenerator()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(12)

        title = QLabel(
            "Edit credential" if credential else "Add password", objectName="dialogTitle"
        )
        subtitle = QLabel(
            "Update this encrypted login."
            if credential
            else "Save a login securely to your local vault.",
            objectName="dialogSubtitle",
        )
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        self.service_input = self._line_field(layout, "Service name", "e.g. GitHub")
        self.username_input = self._line_field(
            layout, "Username / email", "Optional"
        )

        layout.addWidget(QLabel("Password", objectName="dialogFieldLabel"))
        password_row = QHBoxLayout()
        self.password_input = PasswordInput("Enter or generate a password")
        generate_button = QPushButton("Generate", objectName="dialogSecondaryButton")
        generate_button.setToolTip("Generate a secure 20-character password")
        generate_button.clicked.connect(self._generate_password)
        password_row.addWidget(self.password_input, 1)
        password_row.addWidget(generate_button)
        layout.addLayout(password_row)

        self.website_input = self._line_field(layout, "Website", "Optional")
        layout.addWidget(QLabel("Category", objectName="dialogFieldLabel"))
        self.category_input = QComboBox(objectName="dialogCombo")
        other_index = 0
        for index, category in enumerate(categories):
            self.category_input.addItem(category.name, category.id)
            if category.name.casefold() == "other":
                other_index = index
        self.category_input.setCurrentIndex(other_index)
        layout.addWidget(self.category_input)

        layout.addWidget(QLabel("Notes", objectName="dialogFieldLabel"))
        self.notes_input = QTextEdit(objectName="dialogNotes")
        self.notes_input.setPlaceholderText("Optional notes")
        self.notes_input.setFixedHeight(82)
        layout.addWidget(self.notes_input)

        self.error_label = QLabel(objectName="dialogError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel", objectName="dialogSecondaryButton")
        save = QPushButton(
            "Save Changes" if credential else "Save Password",
            objectName="primaryButton",
        )
        save.setDefault(True)
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self._validate_and_accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addLayout(actions)

        if credential:
            self.service_input.setText(credential.service_name)
            self.username_input.setText(credential.username)
            self.password_input.line_edit.setText(credential.password)
            self.website_input.setText(credential.website)
            self.notes_input.setPlainText(credential.notes)
            category_index = self.category_input.findData(credential.category_id)
            if category_index >= 0:
                self.category_input.setCurrentIndex(category_index)
        elif prefilled_password:
            self.password_input.line_edit.setText(prefilled_password)

    @staticmethod
    def _line_field(layout: QVBoxLayout, label: str, placeholder: str) -> QLineEdit:
        layout.addWidget(QLabel(label, objectName="dialogFieldLabel"))
        field = QLineEdit(objectName="dialogInput")
        field.setPlaceholderText(placeholder)
        field.setClearButtonEnabled(True)
        layout.addWidget(field)
        return field

    def take_draft(self) -> CredentialDraft | None:
        draft = self._draft
        self._draft = None
        return draft

    def wipe_sensitive(self) -> None:
        self.password_input.clear()
        self.username_input.clear()
        self.notes_input.clear()

    def reject(self) -> None:
        self.wipe_sensitive()
        super().reject()

    def _generate_password(self) -> None:
        self.password_input.line_edit.setText(
            self._generator.generate(DEFAULT_PASSWORD_LENGTH)
        )

    def _validate_and_accept(self) -> None:
        service_name = self.service_input.text().strip()
        password = self.password_input.text()
        if not service_name:
            self._show_error("Enter a service name.")
            self.service_input.setFocus()
            return
        if not password:
            self._show_error("Enter or generate a password.")
            self.password_input.line_edit.setFocus()
            return
        self._draft = CredentialDraft(
            service_name=service_name,
            username=self.username_input.text(),
            password=password,
            website=self.website_input.text(),
            category_id=self.category_input.currentData(),
            notes=self.notes_input.toPlainText(),
            favorite=self._existing.favorite if self._existing else False,
        )
        self.error_label.hide()
        super().accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()
