"""Phase 5 settings, lifecycle, key rotation, and backup security tests."""

from __future__ import annotations

import os
import secrets
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app.application import create_application
from app.config import load_stylesheet
from app.controller import VaultApplicationController
from app.database import DatabaseManager, VaultSettings
from app.database.models import CredentialDraft
from app.security.encryption import EncryptionError, EncryptionService
from app.security.inactivity_manager import InactivityManager
from app.security.key_manager import create_vault_secrets, verify_master_password
from app.security.session import VaultSession
from app.services.backup_service import BackupError, BackupService, MAGIC
from app.services.clipboard_service import ClipboardService
from app.services.settings_service import AppSettings, SettingsService
from app.services.vault_security_service import (
    IncorrectMasterPasswordError,
    VaultSecurityError,
    VaultSecurityService,
)
from app.services.vault_service import VaultService
from app.ui.main_window import MainWindow
from app.ui.settings_page import SettingsPage
from app.ui.unlock_window import UnlockWindow


class Phase5ServiceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or create_application(
            ["vaultkey-phase5-tests"]
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.database = DatabaseManager(self.root / "vault.db")
        self.database.initialize()
        self.master_password = "Correct-Horse-Battery-Staple"
        bundle = create_vault_secrets(self.master_password)
        self.database.create_vault(
            VaultSettings(
                bundle.password_verifier,
                bundle.salt,
                bundle.kdf_parameters,
                "2026-08-13T00:00:00+00:00",
            )
        )
        self.session = VaultSession()
        self.session.unlock(bundle.derived_key)
        self.vault = VaultService(self.database, self.session)
        self.category_id = self.vault.list_categories()[0].id

    def tearDown(self) -> None:
        QGuiApplication.clipboard().clear()
        self.session.lock()
        self.temporary.cleanup()

    def add_credential(self, marker: str = "phase-five-secret") -> int:
        return self.vault.create_credential(
            CredentialDraft(
                "Phase Five",
                "local-user",
                marker,
                "vaultkey.test",
                self.category_id,
                "private local note",
                True,
            )
        )


class SettingsAndLifecycleTests(Phase5ServiceTestCase):
    def test_settings_persist_and_invalid_values_fall_back(self) -> None:
        settings = SettingsService(self.database)
        self.assertEqual(settings.load(), AppSettings())
        settings.set_auto_lock_minutes(10)
        settings.set_clipboard_clear_seconds(60)
        settings.set_appearance_mode("light")
        self.assertEqual(
            SettingsService(self.database).load(), AppSettings(10, 60, "light")
        )
        with self.database.connection() as connection:
            connection.execute(
                "UPDATE app_settings SET value = 'abc' WHERE key = 'auto_lock_minutes'"
            )
            connection.execute(
                "UPDATE app_settings SET value = 'unsafe' WHERE key = 'appearance_mode'"
            )
        loaded = SettingsService(self.database).load()
        self.assertEqual(loaded.auto_lock_minutes, 5)
        self.assertEqual(loaded.appearance_mode, "dark")
        with self.assertRaises(ValueError):
            settings.set_clipboard_clear_seconds(999)
        self.assertIn("#F4F6FA", load_stylesheet("system", system_is_dark=False))
        self.assertIn("#0D0F12", load_stylesheet("system", system_is_dark=True))

    def test_phase4_database_migration_preserves_existing_encrypted_rows(self) -> None:
        credential_id = self.add_credential("migration-secret")
        with self.database.connection() as connection:
            encrypted_before = connection.execute(
                "SELECT username_encrypted, password_encrypted, notes_encrypted FROM credentials WHERE id = ?",
                (credential_id,),
            ).fetchone()
            connection.execute("DROP TABLE app_settings")
            connection.execute("DROP TABLE schema_metadata")
        self.database.initialize()
        with self.database.connection() as connection:
            encrypted_after = connection.execute(
                "SELECT username_encrypted, password_encrypted, notes_encrypted FROM credentials WHERE id = ?",
                (credential_id,),
            ).fetchone()
        self.assertEqual(tuple(encrypted_before), tuple(encrypted_after))
        self.assertEqual(
            self.vault.get_credential(credential_id).password, "migration-secret"
        )
        self.assertEqual(SettingsService(self.database).load(), AppSettings())

    def test_clipboard_clear_is_ownership_aware_and_lock_safe(self) -> None:
        clipboard = QGuiApplication.clipboard()
        service = ClipboardService(clipboard, 10)
        service.copy_sensitive("first-secret")
        service._clear_if_unchanged()
        self.assertEqual(clipboard.text(), "")

        service.copy_sensitive("second-secret")
        clipboard.setText("newer unrelated text")
        service._clear_if_unchanged()
        self.assertEqual(clipboard.text(), "newer unrelated text")

        service.copy_sensitive("password-a")
        service.copy_sensitive("password-b")
        service.clear_owned()
        self.assertEqual(clipboard.text(), "")

        service.set_clear_seconds(0)
        service.copy_sensitive("never-timed-secret")
        service.clear_owned()
        self.assertEqual(clipboard.text(), "")

    def test_inactivity_resets_uses_elapsed_time_and_supports_never(self) -> None:
        now = [100.0]
        manager = InactivityManager(lambda: now[0])
        locks: list[bool] = []
        manager.lock_requested.connect(lambda: locks.append(True))
        manager.configure_minutes(1)
        manager.start()
        now[0] += 30
        manager.eventFilter(self, QEvent(QEvent.Type.KeyPress))
        now[0] += 40
        manager._check_timeout()
        self.assertEqual(locks, [])
        now[0] += 21
        manager._check_timeout()
        self.assertEqual(locks, [True])

        manager.configure_minutes(0)
        manager.start()
        now[0] += 10_000
        manager._check_timeout()
        self.assertEqual(locks, [True])

        manager.configure_minutes(5)
        manager.start()
        now[0] += 20
        manager.configure_minutes(1)
        now[0] += 61
        manager._check_timeout()
        self.assertEqual(locks, [True, True])

    def test_controller_applies_settings_and_lock_clears_ui_clipboard_and_session(self) -> None:
        controller = VaultApplicationController(self.application, self.database)
        settings = self.database.get_vault_settings()
        assert settings is not None
        key = verify_master_password(self.master_password, settings)
        assert key is not None
        controller.session.unlock(key)
        controller.show_main_window()
        main = controller.current_window
        assert isinstance(main, MainWindow)
        settings_page = main._pages["settings"]
        assert isinstance(settings_page, SettingsPage)
        settings_page.auto_lock_combo.setCurrentIndex(
            settings_page.auto_lock_combo.findData(10)
        )
        settings_page.clipboard_combo.setCurrentIndex(
            settings_page.clipboard_combo.findData(60)
        )
        self.application.processEvents()
        self.assertEqual(SettingsService(self.database).load(), AppSettings(10, 60, "dark"))

        generator = main._pages["generator"]
        generated = generator.password_output.text()
        generator.copy_password()
        self.assertEqual(QGuiApplication.clipboard().text(), generated)
        controller.lock_vault()
        self.application.processEvents()
        self.assertFalse(controller.session.is_unlocked)
        self.assertEqual(QGuiApplication.clipboard().text(), "")
        self.assertEqual(generator.password_output.text(), "")
        self.assertIsInstance(controller.current_window, UnlockWindow)
        controller.current_window.close()


class MasterPasswordRotationTests(Phase5ServiceTestCase):
    def test_success_reencrypts_all_fields_and_replaces_login(self) -> None:
        credential_id = self.add_credential()
        with self.database.connection() as connection:
            before = connection.execute(
                "SELECT username_encrypted, password_encrypted, notes_encrypted FROM credentials"
            ).fetchone()
        new_password = "New-Correct-Horse-Battery-Staple"
        VaultSecurityService(self.database).change_master_password(
            self.master_password, new_password, new_password
        )
        settings = self.database.get_vault_settings()
        assert settings is not None
        self.assertIsNone(verify_master_password(self.master_password, settings))
        new_key = verify_master_password(new_password, settings)
        self.assertIsNotNone(new_key)
        with self.database.connection() as connection:
            after = connection.execute(
                "SELECT username_encrypted, password_encrypted, notes_encrypted FROM credentials"
            ).fetchone()
        self.assertNotEqual(tuple(before), tuple(after))

        self.session.lock()
        assert new_key is not None
        self.session.unlock(new_key)
        restored = VaultService(self.database, self.session).get_credential(credential_id)
        self.assertEqual(restored.password, "phase-five-secret")
        self.assertEqual(restored.notes, "private local note")

    def test_validation_and_wrong_current_password_leave_vault_unchanged(self) -> None:
        self.add_credential()
        before = self.database.path.read_bytes()
        service = VaultSecurityService(self.database)
        with self.assertRaises(IncorrectMasterPasswordError):
            service.change_master_password(
                "wrong-password", "A-new-long-password", "A-new-long-password"
            )
        with self.assertRaises(ValueError):
            service.change_master_password(self.master_password, "short", "short")
        with self.assertRaises(ValueError):
            service.change_master_password(
                self.master_password, "A-new-long-password", "A-different-password"
            )
        self.assertEqual(self.database.path.read_bytes(), before)

    def test_encryption_failure_rolls_back_partial_migration(self) -> None:
        self.add_credential("first-secret")
        self.add_credential("second-secret")
        before = self.database.path.read_bytes()

        class FailingEncryption(EncryptionService):
            def __init__(self) -> None:
                self.calls = 0

            def encrypt(self, plaintext: str, key: bytes, *, context: str) -> bytes:
                self.calls += 1
                if self.calls == 4:
                    raise EncryptionError("injected migration failure")
                return super().encrypt(plaintext, key, context=context)

        with self.assertRaises(VaultSecurityError):
            VaultSecurityService(self.database, FailingEncryption()).change_master_password(
                self.master_password,
                "Replacement-Master-Password",
                "Replacement-Master-Password",
            )
        self.assertEqual(self.database.path.read_bytes(), before)
        settings = self.database.get_vault_settings()
        assert settings is not None
        self.assertIsNotNone(verify_master_password(self.master_password, settings))


class BackupAndResetTests(Phase5ServiceTestCase):
    def test_backup_is_encrypted_and_restore_recovers_complete_vault(self) -> None:
        credential_id = self.add_credential("backup-secret-marker")
        settings = SettingsService(self.database)
        settings.set_auto_lock_minutes(10)
        settings.set_clipboard_clear_seconds(60)
        settings.set_appearance_mode("light")
        backup_path = self.root / "complete.vkbak"
        backup = BackupService(self.database)
        backup.create_backup(backup_path, self.master_password)
        raw = backup_path.read_bytes()
        self.assertTrue(raw.startswith(MAGIC))
        self.assertNotIn(b"SQLite format 3", raw)
        self.assertNotIn(b"backup-secret-marker", raw)
        self.assertEqual(list(self.root.glob(".vaultkey-*")), [])

        self.vault.delete_credential(credential_id)
        settings.set_appearance_mode("dark")
        backup.restore_backup(backup_path, self.master_password)
        restored_settings = SettingsService(self.database).load()
        self.assertEqual(restored_settings, AppSettings(10, 60, "light"))
        restored = VaultService(self.database, self.session).get_credential(credential_id)
        self.assertEqual(restored.password, "backup-secret-marker")
        self.assertTrue(restored.favorite)
        self.assertEqual(list(self.root.glob(".vaultkey-*")), [])

    def test_wrong_password_corruption_and_invalid_file_preserve_current_vault(self) -> None:
        credential_id = self.add_credential()
        backup_path = self.root / "valid.vkbak"
        backup = BackupService(self.database)
        backup.create_backup(backup_path, self.master_password)
        before = self.database.path.read_bytes()
        with self.assertRaises(BackupError):
            backup.restore_backup(backup_path, "wrong backup password")
        self.assertEqual(self.database.path.read_bytes(), before)

        corrupted = self.root / "corrupt.vkbak"
        damaged = bytearray(backup_path.read_bytes())
        damaged[-1] ^= 1
        corrupted.write_bytes(damaged)
        with self.assertRaises(BackupError):
            backup.restore_backup(corrupted, self.master_password)
        self.assertEqual(self.database.path.read_bytes(), before)

        invalid = self.root / "invalid.vkbak"
        invalid.write_bytes(b"not a VaultKey backup")
        with self.assertRaises(BackupError):
            backup.restore_backup(invalid, self.master_password)
        self.assertEqual(self.database.path.read_bytes(), before)

        malformed_header = self.root / "malformed-header.vkbak"
        malformed_header.write_bytes(
            backup_path.read_bytes().replace(b'"version":1', b'"version":9', 1)
        )
        with self.assertRaises(BackupError):
            backup.restore_backup(malformed_header, self.master_password)
        self.assertEqual(self.database.path.read_bytes(), before)
        self.assertEqual(self.vault.get_credential(credential_id).password, "phase-five-secret")

    def test_reset_removes_active_vault_but_not_backup(self) -> None:
        self.add_credential()
        backup_path = self.root / "kept.vkbak"
        BackupService(self.database).create_backup(backup_path, self.master_password)
        self.assertTrue(VaultSecurityService(self.database).verify_password(self.master_password))
        self.session.lock()
        self.database.reset()
        self.assertIsNone(self.database.get_vault_settings())
        with self.database.connection() as connection:
            count = connection.execute("SELECT COUNT(*) FROM credentials").fetchone()[0]
        self.assertEqual(count, 0)
        self.assertTrue(backup_path.exists())


if __name__ == "__main__":
    unittest.main()
