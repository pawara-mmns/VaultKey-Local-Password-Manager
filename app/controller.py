"""Application flow controller for setup, unlock, and authenticated states."""

from __future__ import annotations

from datetime import datetime, timezone

from pathlib import Path

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMainWindow

from app.config import DATABASE_PATH, load_stylesheet
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
from app.security.inactivity_manager import InactivityManager
from app.services.backup_service import BackupError, BackupService
from app.services.clipboard_service import ClipboardService
from app.services.settings_service import SettingsService
from app.services.vault_security_service import (
    IncorrectMasterPasswordError,
    VaultSecurityError,
    VaultSecurityService,
)
from app.services.vault_service import VaultService
from app.ui.dialogs import (
    ChangeMasterPasswordDialog,
    MasterPasswordDialog,
    MessageDialog,
    ResetVaultDialog,
    RestoreConfirmationDialog,
)
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
        self.settings_service: SettingsService | None = None
        self.clipboard_service = ClipboardService(self.application.clipboard())
        self.inactivity = InactivityManager()
        self.application.installEventFilter(self.inactivity)
        self.inactivity.lock_requested.connect(
            lambda: self.lock_vault("Vault locked after inactivity.")
        )
        self.application.aboutToQuit.connect(self._cleanup_sensitive_state)
        try:
            self.application.styleHints().colorSchemeChanged.connect(
                self._system_theme_changed
            )
        except AttributeError:
            pass

    def start(self) -> None:
        """Initialize persistence and display the correct entry screen."""
        try:
            self.database.initialize()
            self._reload_settings()
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

    def show_unlock(
        self,
        unavailable_message: str | None = None,
        notice_message: str | None = None,
        error_message: str | None = None,
    ) -> None:
        window = UnlockWindow()
        window.unlock_requested.connect(self._unlock_vault)
        if unavailable_message:
            window.set_unavailable(unavailable_message)
        elif error_message:
            window.show_error(error_message)
        elif notice_message:
            window.show_notice(notice_message)
        self._replace_window(window)

    def show_main_window(self) -> None:
        if self.settings_service is None:
            self._reload_settings()
        window = MainWindow(
            VaultService(self.database, self.session),
            self.settings_service,
            self.clipboard_service,
        )
        window.lock_requested.connect(self.lock_vault)
        window.exit_requested.connect(self.exit_application)
        window.auto_lock_changed.connect(self._set_auto_lock)
        window.clipboard_clear_changed.connect(self._set_clipboard_timeout)
        window.appearance_changed.connect(self._set_appearance)
        window.change_master_requested.connect(self._change_master_password)
        window.backup_requested.connect(self._create_backup)
        window.restore_requested.connect(self._restore_backup)
        window.reset_requested.connect(self._reset_vault)
        self._replace_window(window)
        settings = self.settings_service.load()
        self.inactivity.configure_minutes(settings.auto_lock_minutes)
        self.inactivity.start()

    def lock_vault(self, notice_message: str | None = None) -> None:
        """Drop active key material and return to the unlock screen."""
        self._cleanup_sensitive_state()
        self.show_unlock(notice_message=notice_message)

    def exit_application(self) -> None:
        self._cleanup_sensitive_state()
        self.application.quit()

    def _set_auto_lock(self, minutes: int) -> None:
        try:
            assert self.settings_service is not None
            self.settings_service.set_auto_lock_minutes(minutes)
            self.inactivity.configure_minutes(minutes)
            self._status("Auto-lock preference saved.")
        except (DatabaseError, ValueError):
            self._status("Unable to save the auto-lock preference.", 4500)

    def _set_clipboard_timeout(self, seconds: int) -> None:
        try:
            assert self.settings_service is not None
            self.settings_service.set_clipboard_clear_seconds(seconds)
            self.clipboard_service.set_clear_seconds(seconds)
            self._status("Clipboard preference saved.")
        except (DatabaseError, ValueError):
            self._status("Unable to save the clipboard preference.", 4500)

    def _set_appearance(self, appearance: str) -> None:
        try:
            assert self.settings_service is not None
            self.settings_service.set_appearance_mode(appearance)
            self._apply_theme(appearance)
            self._status("Appearance updated.")
        except (DatabaseError, ValueError):
            self._status("Unable to save the appearance preference.", 4500)

    def _change_master_password(self) -> None:
        parent = self._main_window()
        if parent is None:
            return
        dialog = ChangeMasterPasswordDialog(parent)
        service = VaultSecurityService(self.database)
        try:
            while dialog.exec() == QDialog.DialogCode.Accepted:
                current, new, confirmation = dialog.values()
                try:
                    service.change_master_password(current, new, confirmation)
                except IncorrectMasterPasswordError:
                    dialog.show_error("The current master password is incorrect.")
                    continue
                except ValueError as error:
                    dialog.show_error(str(error))
                    continue
                except (DatabaseError, VaultSecurityError, KeyDerivationError):
                    dialog.show_error(
                        "The password was not changed. Your existing vault remains intact."
                    )
                    continue
                self.lock_vault("Master password changed. Unlock with your new password.")
                return
        finally:
            dialog.wipe_sensitive()

    def _create_backup(self) -> None:
        parent = self._main_window()
        if parent is None:
            return
        raw_path, _ = QFileDialog.getSaveFileName(
            parent,
            "Create Encrypted Backup",
            "VaultKey-Backup.vkbak",
            "VaultKey Backup (*.vkbak)",
        )
        if not raw_path:
            return
        path = Path(raw_path)
        if path.suffix.lower() != ".vkbak":
            path = path.with_suffix(".vkbak")
        dialog = MasterPasswordDialog(
            "Create encrypted backup",
            "Confirm your master password. The backup will contain the complete vault encrypted with AES-GCM.",
            "Create Backup",
            parent,
        )
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            BackupService(self.database).create_backup(path, dialog.password.text())
            MessageDialog(
                "Backup created", f"Encrypted backup saved to:\n{path}", parent
            ).exec()
        except BackupError as error:
            MessageDialog("Backup failed", str(error), parent, danger=True).exec()
        finally:
            dialog.wipe_sensitive()

    def _restore_backup(self) -> None:
        parent = self._main_window()
        if parent is None:
            return
        raw_path, _ = QFileDialog.getOpenFileName(
            parent,
            "Restore Encrypted Backup",
            "",
            "VaultKey Backup (*.vkbak)",
        )
        if not raw_path:
            return
        dialog = MasterPasswordDialog(
            "Validate backup",
            "Enter the master password used by this backup.",
            "Validate Backup",
            parent,
        )
        try:
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            password = dialog.password.text()
            backup = BackupService(self.database)
            backup.validate_backup(Path(raw_path), password)
            if (
                RestoreConfirmationDialog(parent).exec()
                != QDialog.DialogCode.Accepted
            ):
                return
            self._cleanup_sensitive_state()
            backup.restore_backup(Path(raw_path), password)
            self._reload_settings()
            self.show_unlock(notice_message="Backup restored. Unlock with the backup's master password.")
        except BackupError as error:
            if not self.session.is_unlocked:
                self.show_unlock(error_message=str(error))
            else:
                MessageDialog("Restore failed", str(error), parent, danger=True).exec()
        finally:
            dialog.wipe_sensitive()

    def _reset_vault(self) -> None:
        parent = self._main_window()
        if parent is None:
            return
        dialog = ResetVaultDialog(parent)
        try:
            while dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    if not VaultSecurityService(self.database).verify_password(
                        dialog.password.text()
                    ):
                        dialog.show_error("The master password is incorrect.")
                        continue
                    self._cleanup_sensitive_state()
                    self.database.reset()
                    self._reload_settings()
                    self.show_setup()
                    return
                except (DatabaseError, KeyDerivationError, ValueError):
                    dialog.show_error("VaultKey could not reset the vault safely.")
        finally:
            dialog.wipe_sensitive()

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

    def _reload_settings(self) -> None:
        self.settings_service = SettingsService(self.database)
        settings = self.settings_service.load()
        self.clipboard_service.set_clear_seconds(settings.clipboard_clear_seconds)
        self.inactivity.configure_minutes(settings.auto_lock_minutes)
        self._apply_theme(settings.appearance_mode)

    def _apply_theme(self, appearance: str) -> None:
        try:
            system_is_dark = (
                self.application.styleHints().colorScheme() == Qt.ColorScheme.Dark
            )
        except AttributeError:
            system_is_dark = True
        self.application.setStyleSheet(
            load_stylesheet(appearance, system_is_dark=system_is_dark)
        )

    def _system_theme_changed(self, *_args: object) -> None:
        if self.settings_service is None:
            return
        settings = self.settings_service.load()
        if settings.appearance_mode == "system":
            self._apply_theme("system")

    def _cleanup_sensitive_state(self) -> None:
        self.inactivity.stop()
        if isinstance(self.current_window, MainWindow):
            self.current_window.prepare_for_lock()
        self.clipboard_service.clear_owned()
        self.session.lock()

    def _main_window(self) -> MainWindow | None:
        return self.current_window if isinstance(self.current_window, MainWindow) else None

    def _status(self, message: str, timeout: int = 3000) -> None:
        window = self._main_window()
        if window is not None:
            window.statusBar().showMessage(message, timeout)
