"""Favorite credentials page using shared credential rows."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from app.components.credential_item import CredentialItem
from app.components.page_widgets import PageHeader
from app.services.vault_service import VaultService


class FavoritesPage(QWidget):
    credential_requested = Signal(int)
    favorite_requested = Signal(int, bool)

    def __init__(self, service: VaultService | None = None) -> None:
        super().__init__()
        self.setObjectName("page")
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(20)
        layout.addWidget(
            PageHeader("Favorites", "Keep your most-used credentials close at hand.")
        )
        self.message = QLabel(objectName="pageMessage")
        self.message.hide()
        layout.addWidget(self.message)
        self.scroll = QScrollArea(objectName="credentialScroll")
        self.scroll.setWidgetResizable(True)
        self.container = QWidget(objectName="credentialList")
        self.list_layout = QVBoxLayout(self.container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)
        self.refresh()

    def refresh(self) -> None:
        self._clear()
        if self.service is None:
            self.message.setText("Favorites are available after unlocking a vault.")
            self.message.show()
            return
        try:
            credentials = self.service.list_credentials(favorites_only=True)
        except Exception:
            self.message.setText("Unable to load favorite credentials.")
            self.message.show()
            return
        if not credentials:
            self.message.setText(
                "No favorites yet. Mark frequently used credentials with the star icon."
            )
            self.message.show()
            return
        self.message.hide()
        for credential in credentials:
            item = CredentialItem(credential)
            item.credential_requested.connect(self.credential_requested)
            item.favorite_requested.connect(self.favorite_requested)
            self.list_layout.insertWidget(self.list_layout.count() - 1, item)

    def _clear(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
