"""Phase 2 database, security, validation, and application-flow tests."""

from __future__ import annotations

import hmac
import os
import secrets
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton

from app.application import create_application
from app.controller import VaultApplicationController
from app.database import DatabaseManager, VaultSettings
from app.database.database import VaultConfigurationError
from app.security.key_manager import (
    KdfParameters,
    KeyDerivationError,
    create_vault_secrets,
    verify_master_password,
)
from app.security.password_strength import assess_password_strength, validate_master_password
from app.ui.main_window import MainWindow
from app.ui.setup_window import SetupWindow
from app.ui.unlock_window import UnlockWindow


class SecurityAndDatabaseTests(unittest.TestCase):
    def test_validation_and_strength_feedback(self) -> None:
        self.assertEqual(validate_master_password("", ""), "Enter a master password.")
        self.assertIsNotNone(validate_master_password("short", "short"))
        self.assertIsNotNone(validate_master_password("long-enough-value", "different-value"))
        self.assertIsNone(
            validate_master_password(
                "Blue-Mountain-Coffee-2026",
                "Blue-Mountain-Coffee-2026",
            )
        )
        self.assertGreater(
            assess_password_strength("Blue-Mountain-Coffee-2026").level,
            assess_password_strength("password1234").level,
        )

    def test_vault_record_contains_only_verification_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "vault.db"
            database = DatabaseManager(path)
            database.initialize()
            self.assertFalse(database.has_vault())

            password = secrets.token_urlsafe(20)
            bundle = create_vault_secrets(password)
            database.create_vault(
                VaultSettings(
                    bundle.password_verifier,
                    bundle.salt,
                    bundle.kdf_parameters,
                    "2026-01-01T00:00:00+00:00",
                )
            )

            settings = database.get_vault_settings()
            self.assertIsNotNone(settings)
            assert settings is not None
            self.assertIsNone(verify_master_password("definitely-incorrect", settings))
            verified_key = verify_master_password(password, settings)
            self.assertIsNotNone(verified_key)
            assert verified_key is not None
            self.assertTrue(hmac.compare_digest(verified_key, bundle.derived_key))
            self.assertFalse(password.encode("utf-8") in path.read_bytes())

            with closing(sqlite3.connect(path)) as connection:
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(vault_settings)")
                }
                row = connection.execute(
                    """
                    SELECT COUNT(*), length(password_verifier), length(salt)
                    FROM vault_settings
                    """
                ).fetchone()
            self.assertEqual(
                columns,
                {"id", "password_verifier", "salt", "kdf_parameters", "created_at"},
            )
            self.assertEqual(row, (1, 32, 16))

    def test_corrupt_configuration_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "vault.db"
            database = DatabaseManager(path)
            database.initialize()
            with closing(sqlite3.connect(path)) as connection:
                connection.execute(
                    """
                    INSERT INTO vault_settings (
                        id, password_verifier, salt, kdf_parameters, created_at
                    ) VALUES (1, ?, ?, ?, ?)
                    """,
                    (b"invalid", b"invalid", "{}", "2026-01-01T00:00:00+00:00"),
                )
                connection.commit()
            with self.assertRaises(VaultConfigurationError):
                database.get_vault_settings()
            with self.assertRaises(KeyDerivationError):
                KdfParameters.from_json("{}")


class ApplicationFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or create_application(["vaultkey-tests"])

    def test_first_launch_restart_wrong_password_lock_and_reunlock(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "vault.db"
            password = secrets.token_urlsafe(20)
            controller = VaultApplicationController(
                self.application, DatabaseManager(path)
            )
            controller.start()
            self.application.processEvents()
            self.assertIsInstance(controller.current_window, SetupWindow)
            setup = controller.current_window
            assert isinstance(setup, SetupWindow)

            setup._submit()
            self.assertTrue(setup.error_label.isVisible())
            setup.password_input.line_edit.setText("too-short")
            setup.confirm_input.line_edit.setText("too-short")
            setup._submit()
            self.assertTrue(setup.error_label.isVisible())
            setup.password_input.line_edit.setText(password)
            setup.confirm_input.line_edit.setText(password + "x")
            setup._submit()
            self.assertTrue(setup.error_label.isVisible())

            setup.confirm_input.line_edit.setText(password)
            setup._submit()
            self.application.processEvents()
            self.assertIsInstance(controller.current_window, MainWindow)
            self.assertTrue(controller.session.is_unlocked)
            controller.current_window.close()
            controller.session.lock()
            self.application.processEvents()

            restarted = VaultApplicationController(
                self.application, DatabaseManager(path)
            )
            restarted.start()
            self.application.processEvents()
            self.assertIsInstance(restarted.current_window, UnlockWindow)
            unlock = restarted.current_window
            assert isinstance(unlock, UnlockWindow)
            unlock.password_input.visibility_button.click()
            self.assertEqual(
                unlock.password_input.line_edit.echoMode(), QLineEdit.EchoMode.Normal
            )
            unlock.password_input.visibility_button.click()
            self.assertEqual(
                unlock.password_input.line_edit.echoMode(), QLineEdit.EchoMode.Password
            )

            unlock.password_input.line_edit.setText("wrong-master-password")
            unlock._submit()
            self.assertIsInstance(restarted.current_window, UnlockWindow)
            self.assertFalse(restarted.session.is_unlocked)
            self.assertEqual(unlock.password_input.text(), "")

            unlock.password_input.line_edit.setText(password)
            unlock._submit()
            self.application.processEvents()
            self.assertIsInstance(restarted.current_window, MainWindow)
            self.assertTrue(restarted.session.is_unlocked)

            main_window = restarted.current_window
            lock_buttons = [
                button
                for button in main_window.findChildren(QPushButton)
                if "Lock Vault" in button.text()
            ]
            self.assertEqual(len(lock_buttons), 1)
            lock_buttons[0].click()
            self.application.processEvents()
            self.assertIsInstance(restarted.current_window, UnlockWindow)
            self.assertFalse(restarted.session.is_unlocked)

            unlock_again = restarted.current_window
            assert isinstance(unlock_again, UnlockWindow)
            unlock_again.password_input.line_edit.setText(password)
            unlock_again._submit()
            self.application.processEvents()
            self.assertIsInstance(restarted.current_window, MainWindow)
            self.assertTrue(restarted.session.is_unlocked)
            restarted.current_window.close()
            restarted.session.lock()
            self.application.processEvents()


if __name__ == "__main__":
    unittest.main()
