"""Shared centered window shell for vault authentication screens."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import (
    APP_NAME,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_START_HEIGHT,
    WINDOW_START_WIDTH,
)


class AuthWindow(QMainWindow):
    """Maintains the same dark visual language as the Phase 1 main window."""

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self.setObjectName("authWindow")
        self.setWindowTitle(f"{APP_NAME} — Local password manager")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_START_WIDTH, WINDOW_START_HEIGHT)

        root = QWidget(objectName="authRoot")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(36, 32, 36, 32)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame(objectName="authCard")
        self.card.setFixedWidth(540)
        self.card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(44, 38, 44, 40)
        self.card_layout.setSpacing(0)

        brand = QLabel("V", objectName="authBrandMark")
        brand.setFixedSize(48, 48)
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_name = QLabel(APP_NAME, objectName="authBrandName")
        brand_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading = QLabel(title, objectName="authTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description = QLabel(subtitle, objectName="authSubtitle")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)

        self.card_layout.addWidget(brand, 0, Qt.AlignmentFlag.AlignCenter)
        self.card_layout.addSpacing(10)
        self.card_layout.addWidget(brand_name)
        self.card_layout.addSpacing(28)
        self.card_layout.addWidget(heading)
        self.card_layout.addSpacing(7)
        self.card_layout.addWidget(description)
        self.card_layout.addSpacing(28)

        self.error_label = QLabel(objectName="authError")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        outer.addWidget(self.card)
        self.setCentralWidget(root)

    def show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.hide()
