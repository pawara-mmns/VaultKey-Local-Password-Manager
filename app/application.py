"""Qt application bootstrap."""

from __future__ import annotations

import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from app.config import APP_NAME, ORGANIZATION_NAME, WINDOW_ICON_PATH, load_stylesheet
from app.ui.main_window import MainWindow


def create_application(argv: list[str] | None = None) -> QApplication:
    """Create and configure the shared Qt application instance."""
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationName(APP_NAME)
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    application = QApplication(argv if argv is not None else sys.argv)
    application.setApplicationDisplayName(APP_NAME)
    application.setStyle("Fusion")
    application.setStyleSheet(load_stylesheet())

    if WINDOW_ICON_PATH.exists():
        from PySide6.QtGui import QIcon

        application.setWindowIcon(QIcon(str(WINDOW_ICON_PATH)))

    return application


def run() -> int:
    """Start the VaultKey event loop."""
    application = create_application()
    window = MainWindow()
    window.show()
    return application.exec()
