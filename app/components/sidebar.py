"""Reusable sidebar navigation components."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import SIDEBAR_WIDTH


class SidebarButton(QPushButton):
    """Checkable navigation button carrying its destination page id."""

    def __init__(self, icon_text: str, label: str, page_id: str) -> None:
        super().__init__(f"{icon_text}    {label}")
        self.page_id = page_id
        self.setObjectName("sidebarButton")
        self.setCheckable(True)
        self.setAutoExclusive(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

class Sidebar(QFrame):
    """Application identity and primary navigation."""

    page_requested = Signal(str)
    lock_requested = Signal()
    exit_requested = Signal()

    NAVIGATION = (
        ("dashboard", "⌂", "Dashboard"),
        ("vault", "◇", "Vault"),
        ("favorites", "☆", "Favorites"),
        ("generator", "✦", "Password Generator"),
        ("categories", "▦", "Categories"),
        ("settings", "⚙", "Settings"),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self._buttons: dict[str, SidebarButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 24, 20, 20)
        layout.setSpacing(8)

        layout.addWidget(self._build_brand())
        layout.addSpacing(30)

        section = QLabel("WORKSPACE", objectName="navSectionLabel")
        layout.addWidget(section)
        layout.addSpacing(4)

        for page_id, icon_text, label in self.NAVIGATION:
            button = SidebarButton(icon_text, label, page_id)
            button.clicked.connect(
                lambda checked=False, target=page_id: self.page_requested.emit(target)
            )
            self._buttons[page_id] = button
            layout.addWidget(button)

        layout.addStretch(1)

        security_card = QFrame(objectName="securityCard")
        security_layout = QVBoxLayout(security_card)
        security_layout.setContentsMargins(14, 14, 14, 14)
        security_layout.setSpacing(4)
        security_title = QLabel("●  Local vault", objectName="securityTitle")
        security_text = QLabel("Your data stays on this device.", objectName="securityText")
        security_text.setWordWrap(True)
        security_layout.addWidget(security_title)
        security_layout.addWidget(security_text)
        layout.addWidget(security_card)
        layout.addSpacing(10)

        lock_button = QPushButton("⌁    Lock Vault", objectName="sidebarUtilityButton")
        lock_button.setCursor(Qt.CursorShape.PointingHandCursor)
        lock_button.clicked.connect(self.lock_requested)
        layout.addWidget(lock_button)

        exit_button = QPushButton("×    Exit", objectName="sidebarUtilityButton")
        exit_button.setCursor(Qt.CursorShape.PointingHandCursor)
        exit_button.clicked.connect(self.exit_requested)
        layout.addWidget(exit_button)

    def _build_brand(self) -> QWidget:
        brand = QWidget()
        row = QHBoxLayout(brand)
        row.setContentsMargins(4, 0, 0, 0)
        row.setSpacing(12)

        mark = QLabel("V", objectName="brandMark")
        mark.setFixedSize(40, 40)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_column = QVBoxLayout()
        text_column.setSpacing(0)
        name = QLabel("VaultKey", objectName="brandName")
        tagline = QLabel("SECURE • LOCAL", objectName="brandTagline")
        text_column.addWidget(name)
        text_column.addWidget(tagline)

        row.addWidget(mark)
        row.addLayout(text_column)
        row.addStretch(1)
        brand.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return brand

    def set_active(self, page_id: str) -> None:
        if page_id in self._buttons:
            self._buttons[page_id].setChecked(True)
