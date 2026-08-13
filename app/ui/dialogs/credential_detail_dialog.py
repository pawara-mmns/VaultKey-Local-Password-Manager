"""Credential details with lazy password reveal and copy actions."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from app.database.models import CredentialDetail


class CredentialDetailDialog(QDialog):
    edit_requested = Signal(int)
    delete_requested = Signal(int)
    favorite_requested = Signal(int, bool)

    def __init__(
        self,
        credential: CredentialDetail,
        password_loader: Callable[[], str],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("credentialDetailDialog")
        self.setModal(True)
        self.setWindowTitle(credential.service_name)
        self.setMinimumWidth(590)
        self.credential = credential
        self._password_loader = password_loader
        self._password_visible = False
        self._feedback_timer = QTimer(self)
        self._feedback_timer.setSingleShot(True)
        self._feedback_timer.setInterval(1600)
        self._feedback_timer.timeout.connect(self._clear_feedback)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(16)
        heading = QHBoxLayout()
        name = QLabel(credential.service_name, objectName="dialogTitle")
        favorite = QPushButton(
            "★ Favorite" if credential.favorite else "☆ Favorite",
            objectName="detailFavoriteButton",
        )
        favorite.clicked.connect(
            lambda checked=False: self.favorite_requested.emit(
                credential.id, not credential.favorite
            )
        )
        heading.addWidget(name)
        heading.addStretch(1)
        heading.addWidget(favorite)
        layout.addLayout(heading)
        layout.addWidget(QLabel(credential.category_name, objectName="detailCategory"))

        layout.addWidget(self._value_row("Username / email", credential.username, "username"))

        password_card = QFrame(objectName="detailValueCard")
        password_layout = QVBoxLayout(password_card)
        password_layout.setContentsMargins(14, 11, 12, 11)
        password_layout.setSpacing(6)
        password_layout.addWidget(QLabel("Password", objectName="detailFieldLabel"))
        password_row = QHBoxLayout()
        self.password_display = QLineEdit(objectName="detailValue")
        self.password_display.setReadOnly(True)
        self.password_display.setText("••••••••••••••")
        self.reveal_button = QPushButton("Show", objectName="detailActionButton")
        copy_password = QPushButton("Copy", objectName="detailActionButton")
        self.reveal_button.clicked.connect(self._toggle_password)
        copy_password.clicked.connect(self._copy_password)
        password_row.addWidget(self.password_display, 1)
        password_row.addWidget(self.reveal_button)
        password_row.addWidget(copy_password)
        password_layout.addLayout(password_row)
        layout.addWidget(password_card)

        layout.addWidget(self._value_row("Website", credential.website or "—"))
        layout.addWidget(self._value_row("Notes", credential.notes or "—"))

        dates = QHBoxLayout()
        dates.addWidget(self._date_card("Created", credential.created_at))
        dates.addWidget(self._date_card("Updated", credential.updated_at))
        layout.addLayout(dates)

        self.feedback = QLabel(objectName="detailFeedback")
        self.feedback.hide()
        layout.addWidget(self.feedback)

        actions = QHBoxLayout()
        delete = QPushButton("Delete Credential", objectName="dangerButton")
        edit = QPushButton("Edit Credential", objectName="primaryButton")
        delete.clicked.connect(
            lambda checked=False: self.delete_requested.emit(credential.id)
        )
        edit.clicked.connect(
            lambda checked=False: self.edit_requested.emit(credential.id)
        )
        actions.addWidget(delete)
        actions.addStretch(1)
        actions.addWidget(edit)
        layout.addLayout(actions)

    def _value_row(self, label: str, value: str, copy_kind: str | None = None) -> QFrame:
        card = QFrame(objectName="detailValueCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(14, 11, 12, 11)
        box.setSpacing(5)
        box.addWidget(QLabel(label, objectName="detailFieldLabel"))
        row = QHBoxLayout()
        text = QLabel(value, objectName="detailValueLabel")
        text.setWordWrap(True)
        row.addWidget(text, 1)
        if copy_kind == "username":
            button = QPushButton("Copy", objectName="detailActionButton")
            button.clicked.connect(
                lambda checked=False: self._copy_text(self.credential.username, "Username copied.")
            )
            row.addWidget(button)
        box.addLayout(row)
        return card

    @staticmethod
    def _date_card(label: str, raw_value: str) -> QFrame:
        try:
            value = datetime.fromisoformat(raw_value.replace("Z", "+00:00")).strftime("%b %d, %Y")
        except ValueError:
            value = raw_value
        card = QFrame(objectName="detailDateCard")
        box = QVBoxLayout(card)
        box.setContentsMargins(13, 10, 13, 10)
        box.addWidget(QLabel(label, objectName="detailFieldLabel"))
        box.addWidget(QLabel(value, objectName="detailValueLabel"))
        return card

    def _toggle_password(self) -> None:
        if self._password_visible:
            self.password_display.setText("••••••••••••••")
            self.reveal_button.setText("Show")
            self._password_visible = False
            return
        try:
            password = self._password_loader()
            self.password_display.setText(password)
            self.password_display.setCursorPosition(0)
            self.reveal_button.setText("Hide")
            self._password_visible = True
            del password
        except Exception:
            self._show_feedback("Unable to decrypt this credential.", error=True)

    def _copy_password(self) -> None:
        try:
            password = self._password_loader()
            QGuiApplication.clipboard().setText(password)
            del password
            self._show_feedback("Password copied.")
        except Exception:
            self._show_feedback("Unable to decrypt this credential.", error=True)

    def _copy_text(self, value: str, message: str) -> None:
        try:
            QGuiApplication.clipboard().setText(value)
            self._show_feedback(message)
        except Exception:
            self._show_feedback("Unable to access the clipboard.", error=True)

    def _show_feedback(self, message: str, *, error: bool = False) -> None:
        self.feedback.setText(message)
        self.feedback.setProperty("state", "error" if error else "success")
        self.feedback.style().unpolish(self.feedback)
        self.feedback.style().polish(self.feedback)
        self.feedback.show()
        self._feedback_timer.start()

    def _clear_feedback(self) -> None:
        self.feedback.clear()
        self.feedback.hide()

    def done(self, result: int) -> None:
        self.password_display.clear()
        self._password_loader = lambda: ""
        super().done(result)
