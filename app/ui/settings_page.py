"""Settings page shell."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.components.page_widgets import PageHeader


class SettingsPage(QWidget):
    SECTIONS = (
        ("Security", "Auto-lock and master password", "5 minutes"),
        ("Clipboard", "Clear copied passwords automatically", "30 seconds"),
        ("Appearance", "Choose the VaultKey color theme", "Dark"),
        ("Data", "Backup or restore your encrypted vault", "Manage"),
    )

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)
        layout.addWidget(PageHeader("Settings", "Customize VaultKey for your workflow."))

        card = QFrame(objectName="settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        for index, (title, description, value) in enumerate(self.SECTIONS):
            row = QWidget(objectName="settingsRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(22, 18, 18, 18)
            text = QVBoxLayout()
            text.setSpacing(4)
            text.addWidget(QLabel(title, objectName="settingsTitle"))
            text.addWidget(QLabel(description, objectName="settingsDescription"))
            action = QPushButton(f"{value}  ›", objectName="settingsAction")
            action.setEnabled(False)
            row_layout.addLayout(text, 1)
            row_layout.addWidget(action)
            card_layout.addWidget(row)
            if index < len(self.SECTIONS) - 1:
                divider = QFrame(objectName="divider")
                divider.setFixedHeight(1)
                card_layout.addWidget(divider)
        layout.addWidget(card)

        danger = QFrame(objectName="dangerCard")
        danger_layout = QHBoxLayout(danger)
        danger_layout.setContentsMargins(22, 20, 18, 20)
        danger_text = QVBoxLayout()
        danger_text.setSpacing(4)
        danger_text.addWidget(QLabel("Danger zone", objectName="dangerTitle"))
        danger_text.addWidget(QLabel("Reset this vault and remove its data", objectName="settingsDescription"))
        reset = QPushButton("Reset Vault", objectName="dangerButton")
        reset.setEnabled(False)
        danger_layout.addLayout(danger_text, 1)
        danger_layout.addWidget(reset)
        layout.addWidget(danger)
        layout.addStretch(1)
