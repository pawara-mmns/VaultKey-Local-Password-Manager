"""Primary authenticated application window for the Phase 1 UI shell."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from app.config import (
    APP_NAME,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
    WINDOW_START_HEIGHT,
    WINDOW_START_WIDTH,
)
from app.ui.categories_page import CategoriesPage
from app.ui.dashboard import DashboardPage
from app.ui.favorites_page import FavoritesPage
from app.ui.generator_page import GeneratorPage
from app.ui.settings_page import SettingsPage
from app.ui.vault_page import VaultPage
from app.components.sidebar import Sidebar


class MainWindow(QMainWindow):
    """Hosts sidebar navigation and the page stack."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle(f"{APP_NAME} — Local password manager")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_START_WIDTH, WINDOW_START_HEIGHT)

        self._pages: dict[str, QWidget] = {}
        self._fade_animation: QPropertyAnimation | None = None

        root = QWidget(objectName="rootWidget")
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.sidebar = Sidebar()
        self.stack = QStackedWidget(objectName="pageStack")

        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self._register_pages()
        self.sidebar.page_requested.connect(self.show_page)
        self.sidebar.lock_requested.connect(self._show_phase_message)
        self.sidebar.exit_requested.connect(self.close)
        self.show_page("dashboard", animate=False)

    def _register_pages(self) -> None:
        page_factories: dict[str, Callable[[], QWidget]] = {
            "dashboard": DashboardPage,
            "vault": VaultPage,
            "favorites": FavoritesPage,
            "generator": GeneratorPage,
            "categories": CategoriesPage,
            "settings": SettingsPage,
        }
        for page_id, factory in page_factories.items():
            page = factory()
            self._pages[page_id] = page
            self.stack.addWidget(page)

        dashboard = self._pages["dashboard"]
        if isinstance(dashboard, DashboardPage):
            dashboard.add_password_requested.connect(lambda: self.show_page("vault"))
            dashboard.generate_requested.connect(lambda: self.show_page("generator"))

    def show_page(self, page_id: str, animate: bool = True) -> None:
        page = self._pages.get(page_id)
        if page is None or self.stack.currentWidget() is page:
            self.sidebar.set_active(page_id)
            return

        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(page_id)

        if animate:
            effect = page.graphicsEffect()
            if effect is None:
                from PySide6.QtWidgets import QGraphicsOpacityEffect

                effect = QGraphicsOpacityEffect(page)
                page.setGraphicsEffect(effect)
            effect.setOpacity(0.25)
            animation = QPropertyAnimation(effect, b"opacity", self)
            animation.setDuration(160)
            animation.setStartValue(0.25)
            animation.setEndValue(1.0)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._fade_animation = animation
            animation.start()

    def _show_phase_message(self) -> None:
        self.statusBar().showMessage(
            "Vault locking will be available after security setup is implemented.", 4500
        )
