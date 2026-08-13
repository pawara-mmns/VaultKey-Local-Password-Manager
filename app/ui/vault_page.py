"""Vault list shell for Phase 1."""

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.components.page_widgets import EmptyState, PageHeader


class VaultPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)

        add_button = QPushButton("＋  Add Password", objectName="primaryButton")
        add_button.setEnabled(False)
        layout.addWidget(PageHeader("Vault", "Browse and manage your saved credentials.", [add_button]))

        toolbar = QHBoxLayout()
        toolbar.setSpacing(12)
        search = QLineEdit(objectName="searchInput")
        search.setPlaceholderText("Search service, username, or website…")
        search.setClearButtonEnabled(True)
        category = QComboBox(objectName="filterCombo")
        category.addItems(["All categories", "Social", "Development", "Work", "Education", "Finance", "Other"])
        sort = QComboBox(objectName="filterCombo")
        sort.addItems(["Recently updated", "Name A–Z", "Name Z–A"])
        toolbar.addWidget(search, 1)
        toolbar.addWidget(category)
        toolbar.addWidget(sort)
        layout.addLayout(toolbar)
        layout.addWidget(
            EmptyState(
                "◇",
                "No passwords saved yet",
                "Your encrypted credentials will live here. Add, search, and organize them once vault storage is available.",
                "＋  Add your first password",
            ),
            1,
        )
