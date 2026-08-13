"""Reusable credential summary row for vault, favorites, and dashboard."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.database.models import CredentialSummary


class CredentialItem(QFrame):
    credential_requested = Signal(int)
    favorite_requested = Signal(int, bool)

    def __init__(self, credential: CredentialSummary, *, compact: bool = False) -> None:
        super().__init__(objectName="credentialItem")
        self.credential = credential
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 13 if compact else 16, 14, 13 if compact else 16)
        row.setSpacing(14)

        initial = QLabel(
            credential.service_name[:1].upper() or "?", objectName="credentialInitial"
        )
        initial.setFixedSize(38, 38)
        initial.setAlignment(Qt.AlignmentFlag.AlignCenter)

        identity = QVBoxLayout()
        identity.setSpacing(3)
        service = QLabel(credential.service_name, objectName="credentialService")
        username = QLabel(
            credential.username or "No username", objectName="credentialUsername"
        )
        identity.addWidget(service)
        identity.addWidget(username)
        if compact:
            identity.addWidget(
                QLabel(self._recent_label(credential.updated_at), objectName="credentialWebsite")
            )

        metadata = QVBoxLayout()
        metadata.setSpacing(3)
        website = QLabel(credential.website or "No website", objectName="credentialWebsite")
        category = QLabel(credential.category_name, objectName="credentialCategory")
        website.setAlignment(Qt.AlignmentFlag.AlignRight)
        category.setAlignment(Qt.AlignmentFlag.AlignRight)
        metadata.addWidget(website)
        metadata.addWidget(category)

        self.favorite_button = QPushButton(
            "★" if credential.favorite else "☆", objectName="favoriteButton"
        )
        self.favorite_button.setProperty("favorite", credential.favorite)
        self.favorite_button.setToolTip(
            "Remove from favorites" if credential.favorite else "Add to favorites"
        )
        self.favorite_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favorite_button.clicked.connect(self._toggle_favorite)
        details_button = QPushButton("•••", objectName="credentialMenuButton")
        details_button.setToolTip("View credential")
        details_button.setCursor(Qt.CursorShape.PointingHandCursor)
        details_button.clicked.connect(
            lambda checked=False: self.credential_requested.emit(credential.id)
        )

        row.addWidget(initial)
        row.addLayout(identity, 1)
        if not compact:
            row.addLayout(metadata)
        row.addWidget(self.favorite_button)
        row.addWidget(details_button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.credential_requested.emit(self.credential.id)
        super().mousePressEvent(event)

    def _toggle_favorite(self) -> None:
        self.favorite_requested.emit(self.credential.id, not self.credential.favorite)

    @staticmethod
    def _recent_label(raw_value: str) -> str:
        try:
            updated = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            seconds = max(0, int((datetime.now(timezone.utc) - updated).total_seconds()))
            if seconds < 60:
                return "Updated just now"
            if seconds < 3600:
                return f"Updated {seconds // 60} min ago"
            if seconds < 86400:
                return f"Updated {seconds // 3600} hr ago"
            return f"Updated {seconds // 86400} days ago"
        except ValueError:
            return "Recently updated"
