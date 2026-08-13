"""Dashboard overview with live local vault statistics."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.components.credential_item import CredentialItem
from app.components.page_widgets import PageHeader, StatCard
from app.services.vault_service import VaultService


class DashboardPage(QWidget):
    add_password_requested = Signal()
    generate_requested = Signal()
    view_all_requested = Signal()
    credential_requested = Signal(int)
    favorite_requested = Signal(int, bool)

    def __init__(self, service: VaultService | None = None) -> None:
        super().__init__()
        self.setObjectName("page")
        self.service = service

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea(objectName="pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)

        content = QWidget(objectName="pageContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(28)

        add_button = QPushButton("＋  Add Password", objectName="primaryButton")
        add_button.setEnabled(service is not None)
        add_button.clicked.connect(self.add_password_requested)
        generate_button = QPushButton("✦  Generate Password", objectName="secondaryButton")
        generate_button.clicked.connect(self.generate_requested)
        layout.addWidget(
            PageHeader(
                "Good to see you",
                "Your passwords are stored securely on this device.",
                [generate_button, add_button],
            )
        )

        stats = QGridLayout()
        stats.setHorizontalSpacing(16)
        stats.setVerticalSpacing(16)
        self.stat_cards = {
            "total": StatCard("Total passwords", "0", "primary", "Your saved credentials"),
            "favorites": StatCard("Favorites", "0", "warning", "Quick access items"),
            "weak": StatCard("Weak passwords", "0", "danger", "Very weak or weak"),
            "reused": StatCard("Reused passwords", "0", "success", "Credentials involved"),
        }
        for column, card in enumerate(self.stat_cards.values()):
            stats.addWidget(card, 0, column)
            stats.setColumnStretch(column, 1)
        layout.addLayout(stats)

        section_row = QHBoxLayout()
        section_row.addWidget(QLabel("Recent credentials", objectName="sectionTitle"))
        section_row.addStretch(1)
        view_all = QPushButton("View all  →", objectName="linkButton")
        view_all.clicked.connect(lambda checked=False: self.view_all_requested.emit())
        section_row.addWidget(view_all)
        layout.addLayout(section_row)

        self.recent_card = QFrame(objectName="contentCard")
        self.recent_card.setMinimumHeight(190)
        self.recent_layout = QVBoxLayout(self.recent_card)
        self.recent_layout.setContentsMargins(18, 18, 18, 18)
        self.recent_layout.setSpacing(8)
        layout.addWidget(self.recent_card)
        layout.addStretch(1)
        scroll.setWidget(content)
        self.refresh()

    def refresh(self) -> None:
        self._clear_recent()
        if self.service is None:
            self._show_empty("Your vault is ready", "Unlock to view saved credentials.")
            return
        try:
            stats = self.service.dashboard_stats()
            recent = self.service.recent_credentials(5)
        except Exception:
            self._show_empty("Unable to load dashboard", "The vault data may be damaged.")
            return
        self.stat_cards["total"].set_value(stats.total)
        self.stat_cards["favorites"].set_value(stats.favorites)
        self.stat_cards["weak"].set_value(stats.weak)
        self.stat_cards["reused"].set_value(stats.reused)
        if not recent:
            self._show_empty(
                "Your vault is ready", "Add your first password to see it here."
            )
            return
        for credential in recent:
            item = CredentialItem(credential, compact=True)
            item.credential_requested.connect(self.credential_requested)
            item.favorite_requested.connect(self.favorite_requested)
            self.recent_layout.addWidget(item)

    def _show_empty(self, title: str, message: str) -> None:
        symbol = QLabel("◇", objectName="emptyIconSmall")
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading = QLabel(title, objectName="emptyTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(message, objectName="emptyDescription")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.recent_layout.addStretch(1)
        self.recent_layout.addWidget(symbol)
        self.recent_layout.addWidget(heading)
        self.recent_layout.addWidget(body)
        self.recent_layout.addStretch(1)

    def _clear_recent(self) -> None:
        while self.recent_layout.count():
            item = self.recent_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
