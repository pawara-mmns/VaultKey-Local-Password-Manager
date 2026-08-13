"""Shared building blocks used across pages."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PageHeader(QWidget):
    """Consistent title, subtitle, and optional actions for pages."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        actions: list[QPushButton] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        title_label = QLabel(title, objectName="pageTitle")
        subtitle_label = QLabel(subtitle, objectName="pageSubtitle")
        subtitle_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        text_layout.addWidget(subtitle_label)

        layout.addLayout(text_layout, 1)
        for action in actions or []:
            layout.addWidget(action, 0, Qt.AlignmentFlag.AlignBottom)


class StatCard(QFrame):
    """Small dashboard overview card."""

    def __init__(self, title: str, value: str, accent: str, hint: str) -> None:
        super().__init__()
        self.setObjectName("statCard")
        self.setProperty("accent", accent)
        self.setMinimumHeight(142)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        top = QHBoxLayout()
        label = QLabel(title, objectName="statTitle")
        dot = QLabel("●", objectName="statDot")
        dot.setProperty("accent", accent)
        top.addWidget(label)
        top.addStretch(1)
        top.addWidget(dot)

        value_label = QLabel(value, objectName="statValue")
        hint_label = QLabel(hint, objectName="statHint")

        layout.addLayout(top)
        layout.addWidget(value_label)
        layout.addWidget(hint_label)


class EmptyState(QFrame):
    """Friendly placeholder for features completed in later phases."""

    def __init__(
        self,
        symbol: str,
        title: str,
        description: str,
        action_text: str | None = None,
    ) -> None:
        super().__init__()
        self.setObjectName("emptyState")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 48, 32, 48)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel(symbol, objectName="emptyIcon")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading = QLabel(title, objectName="emptyTitle")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body = QLabel(description, objectName="emptyDescription")
        body.setAlignment(Qt.AlignmentFlag.AlignCenter)
        body.setWordWrap(True)
        body.setMaximumWidth(460)

        layout.addWidget(icon)
        layout.addSpacing(6)
        layout.addWidget(heading)
        layout.addWidget(body)

        if action_text:
            action = QPushButton(action_text, objectName="secondaryButton")
            action.setEnabled(False)
            action.setToolTip("Available in a later development phase")
            layout.addSpacing(10)
            layout.addWidget(action, 0, Qt.AlignmentFlag.AlignCenter)
