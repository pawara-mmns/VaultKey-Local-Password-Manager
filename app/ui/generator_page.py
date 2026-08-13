"""Password generator visual shell for Phase 1."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.components.page_widgets import PageHeader


class GeneratorPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(44, 36, 44, 40)
        layout.setSpacing(24)
        layout.addWidget(PageHeader("Password Generator", "Create unique, high-entropy passwords locally."))

        card = QFrame(objectName="generatorCard")
        card.setMaximumWidth(840)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 28)
        card_layout.setSpacing(22)

        result_label = QLabel("Generated password", objectName="fieldLabel")
        result = QFrame(objectName="passwordPreview")
        result_row = QHBoxLayout(result)
        preview = QLabel("••••••••••••••••••••", objectName="passwordText")
        copy = QPushButton("Copy", objectName="compactButton")
        copy.setEnabled(False)
        result_row.addWidget(preview, 1)
        result_row.addWidget(copy)
        card_layout.addWidget(result_label)
        card_layout.addWidget(result)

        length_row = QHBoxLayout()
        length_title = QLabel("Password length", objectName="fieldLabel")
        length_value = QLabel("20", objectName="lengthBadge")
        length_row.addWidget(length_title)
        length_row.addStretch(1)
        length_row.addWidget(length_value)
        slider = QSlider(Qt.Orientation.Horizontal, objectName="lengthSlider")
        slider.setRange(8, 64)
        slider.setValue(20)
        slider.setEnabled(False)
        card_layout.addLayout(length_row)
        card_layout.addWidget(slider)

        options = QGridLayout()
        labels = ("Uppercase A–Z", "Lowercase a–z", "Numbers 0–9", "Symbols !@#", "Exclude ambiguous characters")
        for index, text in enumerate(labels):
            option = QCheckBox(text)
            option.setChecked(index < 4)
            option.setEnabled(False)
            options.addWidget(option, index // 2, index % 2)
        options.setHorizontalSpacing(32)
        options.setVerticalSpacing(14)
        card_layout.addLayout(options)

        action_row = QHBoxLayout()
        phase_note = QLabel("Secure generation arrives in Phase 3", objectName="phaseBadge")
        generate = QPushButton("✦  Generate New Password", objectName="primaryButton")
        generate.setEnabled(False)
        action_row.addWidget(phase_note)
        action_row.addStretch(1)
        action_row.addWidget(generate)
        card_layout.addLayout(action_row)

        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch(1)
