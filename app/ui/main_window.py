"""Primary authenticated application window for the Phase 1 UI shell."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Signal
from PySide6.QtWidgets import QDialog, QHBoxLayout, QMainWindow, QStackedWidget, QWidget

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
from app.database.category_repository import DuplicateCategoryError
from app.database.database import DatabaseError
from app.services.vault_service import VaultService, VaultServiceError
from app.security.encryption import DecryptionError, EncryptionError
from app.ui.dialogs import (
    CategoryDialog,
    CredentialDetailDialog,
    CredentialDialog,
    DeleteConfirmationDialog,
)


class MainWindow(QMainWindow):
    """Hosts sidebar navigation and the page stack."""

    lock_requested = Signal()
    exit_requested = Signal()

    def __init__(self, vault_service: VaultService | None = None) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle(f"{APP_NAME} — Local password manager")
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_START_WIDTH, WINDOW_START_HEIGHT)

        self._pages: dict[str, QWidget] = {}
        self._fade_animation: QPropertyAnimation | None = None
        self.vault_service = vault_service

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
        self.sidebar.lock_requested.connect(self.lock_requested.emit)
        self.sidebar.exit_requested.connect(self.exit_requested.emit)
        self.show_page("dashboard", animate=False)

    def _register_pages(self) -> None:
        pages: dict[str, QWidget] = {
            "dashboard": DashboardPage(self.vault_service),
            "vault": VaultPage(self.vault_service),
            "favorites": FavoritesPage(self.vault_service),
            "generator": GeneratorPage(),
            "categories": CategoriesPage(self.vault_service),
            "settings": SettingsPage(),
        }
        for page_id, page in pages.items():
            self._pages[page_id] = page
            self.stack.addWidget(page)

        dashboard = self._pages["dashboard"]
        if isinstance(dashboard, DashboardPage):
            dashboard.add_password_requested.connect(self.open_add_credential)
            dashboard.generate_requested.connect(lambda: self.show_page("generator"))
            dashboard.view_all_requested.connect(lambda: self.show_page("vault"))
            dashboard.credential_requested.connect(self.open_credential_detail)
            dashboard.favorite_requested.connect(self.set_favorite)

        vault = self._pages["vault"]
        if isinstance(vault, VaultPage):
            vault.add_requested.connect(self.open_add_credential)
            vault.credential_requested.connect(self.open_credential_detail)
            vault.favorite_requested.connect(self.set_favorite)

        favorites = self._pages["favorites"]
        if isinstance(favorites, FavoritesPage):
            favorites.credential_requested.connect(self.open_credential_detail)
            favorites.favorite_requested.connect(self.set_favorite)

        categories = self._pages["categories"]
        if isinstance(categories, CategoriesPage):
            categories.new_category_requested.connect(self.open_new_category)
            categories.category_selected.connect(self.show_category)

        generator = self._pages["generator"]
        if isinstance(generator, GeneratorPage):
            generator.save_requested.connect(self.open_add_credential)

    def show_page(self, page_id: str, animate: bool = True) -> None:
        page = self._pages.get(page_id)
        if page is None or self.stack.currentWidget() is page:
            self.sidebar.set_active(page_id)
            return

        self.stack.setCurrentWidget(page)
        self.sidebar.set_active(page_id)
        refresh = getattr(page, "refresh", None)
        if callable(refresh):
            refresh()

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

    def open_add_credential(self, prefilled_password: str = "") -> None:
        if self.vault_service is None:
            return
        try:
            dialog = CredentialDialog(
                self.vault_service.list_categories(),
                prefilled_password=prefilled_password,
                parent=self,
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            draft = dialog.take_draft()
            if draft is None:
                return
            try:
                self.vault_service.create_credential(draft)
            finally:
                dialog.wipe_sensitive()
                del draft
            self.refresh_data()
            self.statusBar().showMessage("Password saved securely.", 3500)
        except (DatabaseError, EncryptionError, VaultServiceError, ValueError):
            self.statusBar().showMessage("Unable to save the credential.", 4500)

    def open_credential_detail(self, credential_id: int) -> None:
        if self.vault_service is None:
            return
        try:
            credential = self.vault_service.get_credential(
                credential_id, include_password=False
            )
            dialog = CredentialDetailDialog(
                credential,
                lambda: self.vault_service.get_password(credential_id),
                self,
            )
            dialog.edit_requested.connect(
                lambda current_id: self._edit_from_detail(dialog, current_id)
            )
            dialog.delete_requested.connect(
                lambda current_id: self._delete_from_detail(
                    dialog, current_id, credential.service_name
                )
            )
            dialog.favorite_requested.connect(
                lambda current_id, favorite: self._favorite_from_detail(
                    dialog, current_id, favorite
                )
            )
            dialog.exec()
        except (DatabaseError, DecryptionError, VaultServiceError):
            self.statusBar().showMessage(
                "Unable to read this credential. The stored data may be damaged.", 5000
            )

    def open_edit_credential(self, credential_id: int) -> None:
        if self.vault_service is None:
            return
        try:
            credential = self.vault_service.get_credential(credential_id)
            dialog = CredentialDialog(
                self.vault_service.list_categories(), credential=credential, parent=self
            )
            if dialog.exec() != QDialog.DialogCode.Accepted:
                dialog.wipe_sensitive()
                return
            draft = dialog.take_draft()
            if draft is None:
                return
            try:
                self.vault_service.update_credential(credential_id, draft)
            finally:
                dialog.wipe_sensitive()
                del draft
                del credential
            self.refresh_data()
            self.statusBar().showMessage("Credential updated securely.", 3500)
        except (DatabaseError, DecryptionError, EncryptionError, VaultServiceError, ValueError):
            self.statusBar().showMessage("Unable to update the credential.", 4500)

    def open_new_category(self) -> None:
        if self.vault_service is None:
            return
        dialog = CategoryDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.vault_service.create_category(dialog.category_name)
            self.refresh_data()
            self.statusBar().showMessage("Category created.", 3000)
        except DuplicateCategoryError:
            self.statusBar().showMessage("A category with this name already exists.", 4000)
        except (DatabaseError, VaultServiceError, ValueError):
            self.statusBar().showMessage("Unable to create the category.", 4000)

    def show_category(self, category_id: int) -> None:
        vault = self._pages.get("vault")
        if isinstance(vault, VaultPage):
            vault.set_category_filter(category_id)
        self.show_page("vault")

    def set_favorite(self, credential_id: int, favorite: bool) -> None:
        if self.vault_service is None:
            return
        try:
            self.vault_service.set_favorite(credential_id, favorite)
            self.refresh_data()
        except (DatabaseError, VaultServiceError):
            self.statusBar().showMessage("Unable to update the favorite.", 4000)

    def refresh_data(self) -> None:
        for page_id in ("dashboard", "vault", "favorites", "categories"):
            refresh = getattr(self._pages.get(page_id), "refresh", None)
            if callable(refresh):
                refresh()

    def _edit_from_detail(
        self, dialog: CredentialDetailDialog, credential_id: int
    ) -> None:
        dialog.accept()
        self.open_edit_credential(credential_id)

    def _delete_from_detail(
        self,
        dialog: CredentialDetailDialog,
        credential_id: int,
        service_name: str,
    ) -> None:
        if self.vault_service is None:
            return
        confirmation = DeleteConfirmationDialog(service_name, self)
        if confirmation.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.vault_service.delete_credential(credential_id)
            dialog.accept()
            self.refresh_data()
            self.statusBar().showMessage("Credential deleted.", 3500)
        except (DatabaseError, VaultServiceError):
            self.statusBar().showMessage("Unable to delete the credential.", 4000)

    def _favorite_from_detail(
        self, dialog: CredentialDetailDialog, credential_id: int, favorite: bool
    ) -> None:
        dialog.accept()
        self.set_favorite(credential_id, favorite)
