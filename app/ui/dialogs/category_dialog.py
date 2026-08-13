"""Small matching dialog for custom category creation."""

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout


class CategoryDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("categoryDialog")
        self.setModal(True)
        self.setWindowTitle("New Category")
        self.setFixedWidth(440)
        self.category_name = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(QLabel("New category", objectName="dialogTitle"))
        layout.addWidget(
            QLabel("Create a custom group for your credentials.", objectName="dialogSubtitle")
        )
        layout.addWidget(QLabel("Category name", objectName="dialogFieldLabel"))
        self.name_input = QLineEdit(objectName="dialogInput")
        self.name_input.setPlaceholderText("e.g. Shopping")
        layout.addWidget(self.name_input)
        self.error_label = QLabel(objectName="dialogError")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel", objectName="dialogSecondaryButton")
        create = QPushButton("Create Category", objectName="primaryButton")
        create.setDefault(True)
        cancel.clicked.connect(self.reject)
        create.clicked.connect(self._submit)
        actions.addWidget(cancel)
        actions.addWidget(create)
        layout.addLayout(actions)

    def _submit(self) -> None:
        name = " ".join(self.name_input.text().strip().split())
        if not name:
            self.error_label.setText("Enter a category name.")
            self.error_label.show()
            return
        self.category_name = name
        self.accept()
