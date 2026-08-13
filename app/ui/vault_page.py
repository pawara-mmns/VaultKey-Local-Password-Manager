"""Searchable encrypted credential vault page."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.components.credential_item import CredentialItem
from app.components.page_widgets import PageHeader
from app.services.vault_service import VaultService


class VaultPage(QWidget):
    add_requested = Signal()
    credential_requested = Signal(int)
    favorite_requested = Signal(int, bool)

    def __init__(self, service: VaultService | None = None) -> None:
        super().__init__()
        self.setObjectName("page")
        self.service = service
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self.refresh)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(20)
        add_button = QPushButton("＋  Add Password", objectName="primaryButton")
        add_button.setEnabled(service is not None)
        add_button.clicked.connect(lambda checked=False: self.add_requested.emit())
        layout.addWidget(
            PageHeader("Vault", "Browse and manage your saved credentials.", [add_button])
        )

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        self.search_input = QLineEdit(objectName="searchInput")
        self.search_input.setPlaceholderText("Search service, username, or website…")
        self.search_input.setClearButtonEnabled(True)
        self.category_filter = QComboBox(objectName="filterCombo")
        self.sort_filter = QComboBox(objectName="filterCombo")
        self.sort_filter.addItem("Recently updated", "recent")
        self.sort_filter.addItem("Name A–Z", "name_asc")
        self.sort_filter.addItem("Name Z–A", "name_desc")
        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.category_filter)
        toolbar.addWidget(self.sort_filter)
        layout.addLayout(toolbar)

        self.message = QLabel(objectName="pageMessage")
        self.message.hide()
        layout.addWidget(self.message)

        self.scroll = QScrollArea(objectName="credentialScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.list_widget = QWidget(objectName="credentialList")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)
        self.scroll.setWidget(self.list_widget)
        layout.addWidget(self.scroll, 1)

        self.search_input.textChanged.connect(lambda text="": self._search_timer.start())
        self.category_filter.currentIndexChanged.connect(lambda index=-1: self.refresh())
        self.sort_filter.currentIndexChanged.connect(lambda index=-1: self.refresh())
        self.refresh()

    def set_category_filter(self, category_id: int) -> None:
        index = self.category_filter.findData(category_id)
        if index >= 0:
            self.category_filter.setCurrentIndex(index)
        self.refresh()

    def refresh(self) -> None:
        if self.service is None:
            self._render_message("Credential storage is available after unlocking a vault.")
            return
        selected_category = self.category_filter.currentData()
        try:
            categories = self.service.list_categories()
            self.category_filter.blockSignals(True)
            self.category_filter.clear()
            self.category_filter.addItem("All categories", None)
            for category in categories:
                self.category_filter.addItem(category.name, category.id)
            selected_index = self.category_filter.findData(selected_category)
            self.category_filter.setCurrentIndex(max(0, selected_index))
            self.category_filter.blockSignals(False)
            credentials = self.service.list_credentials(
                search=self.search_input.text(),
                category_id=self.category_filter.currentData(),
                sort=self.sort_filter.currentData() or "recent",
            )
            self._render_credentials(credentials)
        except Exception:
            self.category_filter.blockSignals(False)
            self._render_message("Unable to load credentials. The vault data may be damaged.")

    def _render_credentials(self, credentials) -> None:
        self._clear_list()
        if not credentials:
            message = (
                "No credentials match your filters."
                if self.search_input.text() or self.category_filter.currentData()
                else "No passwords saved yet. Add your first encrypted credential."
            )
            self._render_message(message)
            return
        self.message.hide()
        for credential in credentials:
            item = CredentialItem(credential)
            item.credential_requested.connect(self.credential_requested)
            item.favorite_requested.connect(self.favorite_requested)
            self.list_layout.insertWidget(self.list_layout.count() - 1, item)

    def _render_message(self, message: str) -> None:
        self._clear_list()
        self.message.setText(message)
        self.message.show()

    def _clear_list(self) -> None:
        while self.list_layout.count() > 1:
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
