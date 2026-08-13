"""Credential categories and counts."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.components.page_widgets import PageHeader
from app.database.models import Category
from app.services.vault_service import VaultService


class CategoryCard(QFrame):
    selected = Signal(int)

    def __init__(self, category: Category) -> None:
        super().__init__(objectName="categoryCard")
        self.category = category
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)
        mark = QLabel(category.name[:1].upper(), objectName="categoryMark")
        mark.setFixedSize(42, 42)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(mark)
        layout.addWidget(QLabel(category.name, objectName="categoryTitle"))
        suffix = "password" if category.credential_count == 1 else "passwords"
        layout.addWidget(
            QLabel(
                f"{category.credential_count} {suffix}", objectName="categoryCount"
            )
        )

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.category.id)
        super().mousePressEvent(event)


class CategoriesPage(QWidget):
    new_category_requested = Signal()
    category_selected = Signal(int)

    def __init__(self, service: VaultService | None = None) -> None:
        super().__init__()
        self.setObjectName("page")
        self.service = service
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)
        add = QPushButton("＋  New Category", objectName="secondaryButton")
        add.setEnabled(service is not None)
        add.clicked.connect(lambda checked=False: self.new_category_requested.emit())
        layout.addWidget(
            PageHeader(
                "Categories", "Organize credentials into clear, useful groups.", [add]
            )
        )
        self.message = QLabel(objectName="pageMessage")
        self.message.hide()
        layout.addWidget(self.message)
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        layout.addLayout(self.grid)
        layout.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        self._clear()
        if self.service is None:
            self.message.setText("Categories are available after unlocking a vault.")
            self.message.show()
            return
        try:
            categories = self.service.list_categories()
        except Exception:
            self.message.setText("Unable to load categories.")
            self.message.show()
            return
        self.message.hide()
        for index, category in enumerate(categories):
            card = CategoryCard(category)
            card.selected.connect(self.category_selected)
            self.grid.addWidget(card, index // 3, index % 3)
            self.grid.setColumnStretch(index % 3, 1)

    def _clear(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
