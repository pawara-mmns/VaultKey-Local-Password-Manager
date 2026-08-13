"""Dashboard overview page."""

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

from app.components.page_widgets import PageHeader, StatCard


class DashboardPage(QWidget):
    add_password_requested = Signal()
    generate_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")

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
        cards = (
            ("Total passwords", "0", "primary", "Your saved credentials"),
            ("Favorites", "0", "warning", "Quick access items"),
            ("Weak passwords", "—", "danger", "Analysis coming soon"),
            ("Reused passwords", "—", "success", "Analysis coming soon"),
        )
        for column, card_data in enumerate(cards):
            stats.addWidget(StatCard(*card_data), 0, column)
            stats.setColumnStretch(column, 1)
        layout.addLayout(stats)

        section_row = QHBoxLayout()
        section_title = QLabel("Recent credentials", objectName="sectionTitle")
        view_all = QPushButton("View all  →", objectName="linkButton")
        view_all.clicked.connect(lambda: self.add_password_requested.emit())
        section_row.addWidget(section_title)
        section_row.addStretch(1)
        section_row.addWidget(view_all)
        layout.addLayout(section_row)
        layout.addWidget(self._build_recent_card())
        layout.addStretch(1)
        scroll.setWidget(content)

    @staticmethod
    def _build_recent_card() -> QFrame:
        card = QFrame(objectName="contentCard")
        card.setMinimumHeight(190)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(8)

        symbol = QLabel("◇", objectName="emptyIconSmall")
        symbol.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title = QLabel("Your vault is ready", objectName="emptyTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message = QLabel(
            "Saved credentials will appear here once secure storage is added in a later phase.",
            objectName="emptyDescription",
        )
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message.setWordWrap(True)

        layout.addStretch(1)
        layout.addWidget(symbol)
        layout.addWidget(title)
        layout.addWidget(message)
        layout.addStretch(1)
        return card
