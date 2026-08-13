"""Application flow controller for setup, unlock, and authenticated states."""

from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication, QMainWindow

from app.config import DATABASE_PATH
from app.database import (
    DatabaseError,
    DatabaseManager,
    VaultAlreadyExistsError,
    VaultConfigurationError,
    VaultSettings,
)
from app.security.key_manager import (
    KdfParameters,
    KeyDerivationError,
    create_vault_secrets,
    verify_master_password,
)
from app.security.session import VaultSession
from app.ui.main_window import MainWindow
from app.ui.setup_window import SetupWindow
from app.ui.unlock_window import UnlockWindow


class VaultApplicationController(QObject):
    """Owns application windows and keeps security state away from widgets."""

    def __init__(
        self,
        application: QApplication,
        database: DatabaseManager | None = None,
    ) -> None:
        super().__init__()
        self.application = application
        self.database = database or DatabaseManager(DATABASE_PATH)
        self.session = VaultSession()
        self.current_window: QMainWindow | None = None
        self.application.aboutToQuit.connect(self.session.lock)

    def start(self) -> None:
        """Initialize persistence and display the correct entry screen."""
        try:
            self.database.initialize()
            settings = self.database.get_vault_settings()
            if settings is None:
                self.show_setup()
                return
            KdfParameters.from_json(settings.kdf_parameters)
            self.show_unlock()
        except VaultConfigurationError:
            self.show_unlock("Vault configuration is damaged and cannot be unlocked.")
        except (DatabaseError, KeyDerivationError):
            self.show_unlock("VaultKey could not access a valid local vault configuration.")

    def show_setup(self) -> None:
        window = SetupWindow()
        window.create_requested.connect(self._create_vault)
        self._replace_window(window)

    def show_unlock(self, unavailable_message: str | None = None) -> None:
        window = UnlockWindow()
        window.unlock_requested.connect(self._unlock_vault)
        if unavailable_message:
            window.set_unavailable(unavailable_message)
        self._replace_window(window)

    def show_main_window(self) -> None:
        window = MainWindow()
        window.lock_requested.connect(self.lock_vault)
        window.exit_requested.connect(self.exit_application)
        self._replace_window(window)

    def lock_vault(self) -> None:
        """Drop active key material and return to the unlock screen."""
        self.session.lock()
        self.show_unlock()

    def exit_application(self) -> None:
        self.session.lock()
        self.application.quit()

    def _create_vault(self, password: str) -> None:
        window = self.current_window
        if not isinstance(window, SetupWindow):
            return
        try:
            secrets_bundle = create_vault_secrets(password)
            self.database.create_vault(
                VaultSettings(
                    password_verifier=secrets_bundle.password_verifier,
                    salt=secrets_bundle.salt,
                    kdf_parameters=secrets_bundle.kdf_parameters,
                    created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                )
            )
            self.session.unlock(secrets_bundle.derived_key)
            window.password_input.clear()
            window.confirm_input.clear()
            self.show_main_window()
        except VaultAlreadyExistsError:
            self.session.lock()
            self.show_unlock()
        except (DatabaseError, KeyDerivationError, ValueError):
            self.session.lock()
            window.creation_failed("VaultKey could not create the vault. Please try again.")

    def _unlock_vault(self, password: str) -> None:
        window = self.current_window
        if not isinstance(window, UnlockWindow):
            return
        try:
            settings = self.database.get_vault_settings()
            if settings is None:
                window.set_unavailable("No configured vault was found.")
                return
            derived_key = verify_master_password(password, settings)
            if derived_key is None:
                window.unlock_failed()
                return
            self.session.unlock(derived_key)
            window.password_input.clear()
            self.show_main_window()
        except VaultConfigurationError:
            self.session.lock()
            window.set_unavailable("Vault configuration is damaged and cannot be unlocked.")
        except (DatabaseError, KeyDerivationError, ValueError):
            self.session.lock()
            window.unlock_failed("VaultKey could not unlock the vault. Please try again.")

    def _replace_window(self, new_window: QMainWindow) -> None:
        previous = self.current_window
        if previous is not None:
            new_window.setGeometry(previous.geometry())
        self.current_window = new_window
        new_window.show()
        if previous is not None:
            previous.close()
            previous.deleteLater()
