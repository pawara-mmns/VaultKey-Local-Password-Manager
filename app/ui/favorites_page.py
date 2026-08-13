"""Favorites page shell."""

from PySide6.QtWidgets import QVBoxLayout, QWidget

from app.components.page_widgets import EmptyState, PageHeader


class FavoritesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)
        layout.addWidget(PageHeader("Favorites", "Keep your most-used credentials close at hand."))
        layout.addWidget(
            EmptyState(
                "☆",
                "Nothing favorited yet",
                "Star any credential in your vault and it will appear in this focused view.",
            ),
            1,
        )
