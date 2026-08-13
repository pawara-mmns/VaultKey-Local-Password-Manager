"""Functional Phase 5 security, clipboard, appearance, and data settings."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.components.page_widgets import PageHeader
from app.services.settings_service import AppSettings, SettingsService


class SettingsPage(QWidget):
    auto_lock_changed = Signal(int)
    clipboard_clear_changed = Signal(int)
    appearance_changed = Signal(str)
    change_master_requested = Signal()
    backup_requested = Signal()
    restore_requested = Signal()
    reset_requested = Signal()

    def __init__(self, settings_service: SettingsService | None = None) -> None:
        super().__init__()
        self.settings_service = settings_service
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(20)
        layout.addWidget(PageHeader("Settings", "Security and local vault preferences."))

        settings = settings_service.load() if settings_service else AppSettings()
        card = QFrame(objectName="settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        self.auto_lock_combo = self._combo(
            (("1 minute", 1), ("5 minutes", 5), ("10 minutes", 10),
             ("15 minutes", 15), ("30 minutes", 30), ("Never", 0)),
            settings.auto_lock_minutes,
        )
        self._add_row(
            card_layout,
            "Auto-lock",
            "Lock after no keyboard or mouse activity",
            self.auto_lock_combo,
            section="SECURITY",
        )
        self.auto_lock_combo.currentIndexChanged.connect(
            lambda index: self.auto_lock_changed.emit(int(self.auto_lock_combo.itemData(index)))
        )

        change = QPushButton("Change Master Password", objectName="settingsAction")
        change.clicked.connect(self.change_master_requested.emit)
        self._add_row(card_layout, "Master password", "Re-encrypt every credential with a new key", change)

        self.clipboard_combo = self._combo(
            (("10 seconds", 10), ("30 seconds", 30), ("1 minute", 60),
             ("2 minutes", 120), ("Never", 0)),
            settings.clipboard_clear_seconds,
        )
        self._add_row(
            card_layout,
            "Clipboard",
            "Clear copied passwords if they are still present",
            self.clipboard_combo,
            section="CLIPBOARD",
        )
        self.clipboard_combo.currentIndexChanged.connect(
            lambda index: self.clipboard_clear_changed.emit(
                int(self.clipboard_combo.itemData(index))
            )
        )

        self.appearance_combo = self._combo(
            (("Dark", "dark"), ("Light", "light"), ("Follow system", "system")),
            settings.appearance_mode,
        )
        self._add_row(
            card_layout,
            "Appearance",
            "Apply the theme immediately",
            self.appearance_combo,
            section="APPEARANCE",
        )
        self.appearance_combo.currentIndexChanged.connect(
            lambda index: self.appearance_changed.emit(
                str(self.appearance_combo.itemData(index))
            )
        )

        data_actions = QWidget()
        data_layout = QHBoxLayout(data_actions)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(8)
        backup = QPushButton("Create Backup", objectName="settingsAction")
        restore = QPushButton("Restore Backup", objectName="settingsAction")
        backup.clicked.connect(self.backup_requested.emit)
        restore.clicked.connect(self.restore_requested.emit)
        data_layout.addWidget(backup)
        data_layout.addWidget(restore)
        self._add_row(
            card_layout,
            "Encrypted backup",
            "Save or restore the complete local vault",
            data_actions,
            divider=False,
            section="DATA",
        )
        layout.addWidget(card)

        danger = QFrame(objectName="dangerCard")
        danger_layout = QHBoxLayout(danger)
        danger_layout.setContentsMargins(22, 20, 18, 20)
        danger_text = QVBoxLayout()
        danger_text.setSpacing(4)
        danger_text.addWidget(QLabel("Danger zone", objectName="dangerTitle"))
        danger_text.addWidget(QLabel("Permanently remove this vault's local data", objectName="settingsDescription"))
        reset = QPushButton("Reset Vault", objectName="dangerButton")
        reset.clicked.connect(self.reset_requested.emit)
        danger_layout.addLayout(danger_text, 1)
        danger_layout.addWidget(reset)
        layout.addWidget(danger)
        layout.addStretch(1)

    @staticmethod
    def _combo(items: tuple[tuple[str, object], ...], selected: object) -> QComboBox:
        combo = QComboBox(objectName="settingsCombo")
        for label, value in items:
            combo.addItem(label, value)
        index = combo.findData(selected)
        combo.setCurrentIndex(max(index, 0))
        return combo

    @staticmethod
    def _add_row(
        layout: QVBoxLayout,
        title: str,
        description: str,
        action: QWidget,
        *,
        divider: bool = True,
        section: str | None = None,
    ) -> None:
        row = QWidget(objectName="settingsRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(22, 16, 18, 16)
        text = QVBoxLayout()
        text.setSpacing(4)
        if section:
            text.addWidget(QLabel(section, objectName="settingsSectionLabel"))
        text.addWidget(QLabel(title, objectName="settingsTitle"))
        text.addWidget(QLabel(description, objectName="settingsDescription"))
        row_layout.addLayout(text, 1)
        row_layout.addWidget(action)
        layout.addWidget(row)
        if divider:
            line = QFrame(objectName="divider")
            line.setFixedHeight(1)
            layout.addWidget(line)
