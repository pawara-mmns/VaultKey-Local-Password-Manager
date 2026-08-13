"""Credential deletion confirmation."""

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout


class DeleteConfirmationDialog(QDialog):
    def __init__(self, service_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("deleteDialog")
        self.setModal(True)
        self.setWindowTitle("Delete Credential")
        self.setFixedWidth(450)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)
        layout.addWidget(QLabel(f"Delete {service_name}?", objectName="dialogTitle"))
        message = QLabel(
            "This credential will be permanently removed from your local vault.",
            objectName="dialogSubtitle",
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel", objectName="dialogSecondaryButton")
        delete = QPushButton("Delete", objectName="dangerButton")
        cancel.clicked.connect(self.reject)
        delete.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(delete)
        layout.addLayout(actions)
