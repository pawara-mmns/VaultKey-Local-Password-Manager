"""Categories page shell."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from app.components.page_widgets import PageHeader


class CategoriesPage(QWidget):
    CATEGORIES = (
        ("S", "Social", "0 items"),
        ("D", "Development", "0 items"),
        ("W", "Work", "0 items"),
        ("E", "Education", "0 items"),
        ("F", "Finance", "0 items"),
        ("O", "Other", "0 items"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)
        layout.addWidget(PageHeader("Categories", "Organize credentials into clear, useful groups."))

        grid = QGridLayout()
        grid.setSpacing(16)
        for index, (letter, name, count) in enumerate(self.CATEGORIES):
            card = QFrame(objectName="categoryCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(22, 22, 22, 22)
            card_layout.setSpacing(12)
            mark = QLabel(letter, objectName="categoryMark")
            mark.setFixedSize(42, 42)
            mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title = QLabel(name, objectName="categoryTitle")
            subtitle = QLabel(count, objectName="categoryCount")
            card_layout.addWidget(mark)
            card_layout.addWidget(title)
            card_layout.addWidget(subtitle)
            grid.addWidget(card, index // 3, index % 3)
            grid.setColumnStretch(index % 3, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
