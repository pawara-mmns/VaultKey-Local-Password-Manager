"""Phase 4 encryption, credential service, and integrated UI tests."""

from __future__ import annotations

import os
import secrets
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app.application import create_application
from app.controller import VaultApplicationController
from app.database import DatabaseManager, VaultSettings
from app.database.category_repository import DuplicateCategoryError
from app.database.models import CredentialDraft
from app.security.encryption import DecryptionError, EncryptionService
from app.security.key_manager import create_vault_secrets, verify_master_password
from app.security.session import VaultSession
from app.services import VaultService
from app.ui.dialogs.credential_dialog import CredentialDialog
from app.ui.dialogs.credential_detail_dialog import CredentialDetailDialog
from app.ui.generator_page import GeneratorPage
from app.ui.main_window import MainWindow
from app.ui.setup_window import SetupWindow
from app.ui.unlock_window import UnlockWindow


class EncryptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.encryption = EncryptionService()
        self.key = secrets.token_bytes(32)
        self.plaintext = secrets.token_urlsafe(24)

    def test_ciphertext_differs_and_round_trip_succeeds(self) -> None:
        encrypted = self.encryption.encrypt(
            self.plaintext, self.key, context="password"
        )
        self.assertFalse(self.plaintext.encode("utf-8") in encrypted)
        decrypted = self.encryption.decrypt(encrypted, self.key, context="password")
        self.assertTrue(decrypted == self.plaintext)

    def test_fresh_nonces_produce_different_ciphertexts(self) -> None:
        first = self.encryption.encrypt(self.plaintext, self.key, context="password")
        second = self.encryption.encrypt(self.plaintext, self.key, context="password")
        self.assertFalse(first == second)

    def test_wrong_key_and_modified_ciphertext_fail_safely(self) -> None:
        encrypted = self.encryption.encrypt(
            self.plaintext, self.key, context="password"
        )
        with self.assertRaises(DecryptionError):
            self.encryption.decrypt(
                encrypted, secrets.token_bytes(32), context="password"
            )
        tampered = bytearray(encrypted)
        tampered[-1] ^= 1
        with self.assertRaises(DecryptionError):
            self.encryption.decrypt(bytes(tampered), self.key, context="password")

    def test_context_binding_prevents_field_swaps(self) -> None:
        encrypted = self.encryption.encrypt(
            self.plaintext, self.key, context="password"
        )
        with self.assertRaises(DecryptionError):
            self.encryption.decrypt(encrypted, self.key, context="username")

    def test_empty_optional_string_round_trip(self) -> None:
        encrypted = self.encryption.encrypt("", self.key, context="notes")
        self.assertTrue(self.encryption.decrypt(encrypted, self.key, context="notes") == "")


class VaultServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary.name) / "vault.db"
        self.database = DatabaseManager(self.database_path)
        self.database.initialize()
        self.session = VaultSession()
        self.session_key = secrets.token_bytes(32)
        self.session.unlock(self.session_key)
        self.service = VaultService(self.database, self.session)
        self.categories = {
            category.name: category.id for category in self.service.list_categories()
        }

    def tearDown(self) -> None:
        self.session.lock()
        self.temporary.cleanup()

    def _draft(
        self,
        service_name: str,
        *,
        username: str = "private-user",
        password: str = "private-password",
        website: str = "example.test",
        category: str = "Other",
        notes: str = "private-notes",
        favorite: bool = False,
    ) -> CredentialDraft:
        return CredentialDraft(
            service_name,
            username,
            password,
            website,
            self.categories[category],
            notes,
            favorite,
        )

    def test_crud_persists_across_unlock_and_sensitive_fields_are_encrypted(self) -> None:
        master_password = secrets.token_urlsafe(24)
        bundle = create_vault_secrets(master_password)
        self.database.create_vault(
            VaultSettings(
                bundle.password_verifier,
                bundle.salt,
                bundle.kdf_parameters,
                "2026-01-01T00:00:00+00:00",
            )
        )
        self.session.unlock(bundle.derived_key)
        credential_id = self.service.create_credential(
            self._draft(
                "GitHub",
                username="sensitive-username-marker",
                password="sensitive-password-marker",
                notes="sensitive-notes-marker",
                category="Development",
            )
        )
        raw_database = self.database_path.read_bytes()
        for marker in (
            b"sensitive-username-marker",
            b"sensitive-password-marker",
            b"sensitive-notes-marker",
        ):
            self.assertFalse(marker in raw_database)

        first = self.service.get_credential(credential_id)
        self.assertTrue(first.username == "sensitive-username-marker")
        self.assertTrue(first.password == "sensitive-password-marker")
        self.assertTrue(first.notes == "sensitive-notes-marker")
        created_at = first.created_at

        self.service.update_credential(
            credential_id,
            self._draft(
                "GitHub Updated",
                username="updated-private-user",
                password="updated-private-password",
                website="github.test",
                category="Work",
                notes="updated-private-notes",
                favorite=True,
            ),
        )
        updated = self.service.get_credential(credential_id)
        self.assertTrue(updated.service_name == "GitHub Updated")
        self.assertTrue(updated.username == "updated-private-user")
        self.assertTrue(updated.password == "updated-private-password")
        self.assertTrue(updated.notes == "updated-private-notes")
        self.assertTrue(updated.category_name == "Work")
        self.assertTrue(updated.created_at == created_at)
        self.assertTrue(updated.updated_at != created_at)

        self.session.lock()
        restarted_session = VaultSession()
        settings = self.database.get_vault_settings()
        assert settings is not None
        restored_key = verify_master_password(master_password, settings)
        self.assertIsNotNone(restored_key)
        assert restored_key is not None
        restarted_session.unlock(restored_key)
        restarted_service = VaultService(self.database, restarted_session)
        persisted = restarted_service.get_credential(credential_id)
        self.assertTrue(persisted.password == "updated-private-password")
        restarted_service.delete_credential(credential_id)
        self.assertTrue(restarted_service.list_credentials() == [])
        restarted_session.lock()

    def test_same_plaintext_uses_fresh_field_nonces(self) -> None:
        first_id = self.service.create_credential(self._draft("First"))
        second_id = self.service.create_credential(self._draft("Second"))
        with self.database.connection() as connection:
            rows = connection.execute(
                """
                SELECT password_encrypted FROM credentials
                WHERE id IN (?, ?) ORDER BY id
                """,
                (first_id, second_id),
            ).fetchall()
        self.assertFalse(rows[0][0] == rows[1][0])

    def test_favorites_search_categories_and_dashboard_stats(self) -> None:
        github = self.service.create_credential(
            self._draft(
                "GitHub",
                username="dev-account",
                password="reused-weak",
                website="github.test",
                category="Development",
                favorite=True,
            )
        )
        gitlab = self.service.create_credential(
            self._draft(
                "GitLab",
                username="work-account",
                password="reused-weak",
                website="gitlab.test",
                category="Work",
            )
        )
        self.service.create_credential(
            self._draft(
                "LinkedIn",
                username="social-account",
                password="Blue-Mountain-Coffee-2026",
                website="linkedin.test",
                category="Social",
            )
        )
        self.service.create_credential(
            self._draft(
                "AWS",
                username="cloud-search-marker",
                password="Long-Unique-Cloud-Password-2026!",
                website="aws.test",
                category="Development",
            )
        )

        self.assertTrue(
            [item.service_name for item in self.service.list_credentials(search="Git")]
            == ["GitLab", "GitHub"]
            or [item.service_name for item in self.service.list_credentials(search="Git")]
            == ["GitHub", "GitLab"]
        )
        username_results = self.service.list_credentials(search="cloud-search")
        self.assertTrue(len(username_results) == 1 and username_results[0].service_name == "AWS")
        development = self.service.list_credentials(
            category_id=self.categories["Development"]
        )
        self.assertTrue({item.service_name for item in development} == {"GitHub", "AWS"})
        combined = self.service.list_credentials(
            search="Git", category_id=self.categories["Work"]
        )
        self.assertTrue(len(combined) == 1 and combined[0].id == gitlab)

        favorites = self.service.list_credentials(favorites_only=True)
        self.assertTrue(len(favorites) == 1 and favorites[0].id == github)
        self.service.set_favorite(github, False)
        self.assertTrue(self.service.list_credentials(favorites_only=True) == [])

        stats = self.service.dashboard_stats()
        self.assertTrue(stats.total == 4)
        self.assertTrue(stats.favorites == 0)
        self.assertTrue(stats.weak == 2)
        self.assertTrue(stats.reused == 2)
        self.assertTrue(len(self.service.recent_credentials(3)) == 3)

    def test_default_and_custom_categories(self) -> None:
        self.database.initialize()
        defaults = self.service.list_categories()
        self.assertTrue(len(defaults) == 6)
        custom = self.service.create_category("  Shopping   Accounts ")
        self.assertTrue(custom.name == "Shopping Accounts")
        with self.assertRaises(DuplicateCategoryError):
            self.service.create_category("shopping accounts")
        credential_id = self.service.create_credential(
            CredentialDraft(
                "Shop",
                "",
                "private-password",
                "",
                custom.id,
                "",
            )
        )
        counts = {category.name: category.credential_count for category in self.service.list_categories()}
        self.assertTrue(counts["Shopping Accounts"] == 1)
        updated = self._draft("Shop", category="Finance")
        self.service.update_credential(credential_id, updated)
        counts = {category.name: category.credential_count for category in self.service.list_categories()}
        self.assertTrue(counts["Shopping Accounts"] == 0 and counts["Finance"] == 1)

    def test_password_is_decrypted_lazily(self) -> None:
        credential_id = self.service.create_credential(self._draft("Lazy"))
        metadata = self.service.get_credential(credential_id, include_password=False)
        self.assertTrue(metadata.password == "")
        self.assertTrue(self.service.get_password(credential_id) == "private-password")

    def test_wrong_session_key_and_tampering_fail_safely(self) -> None:
        credential_id = self.service.create_credential(self._draft("Damaged"))
        wrong_session = VaultSession()
        wrong_session.unlock(secrets.token_bytes(32))
        with self.assertRaises(DecryptionError):
            VaultService(self.database, wrong_session).get_credential(credential_id)
        wrong_session.lock()

        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT password_encrypted FROM credentials WHERE id = ?",
                (credential_id,),
            ).fetchone()
            damaged = bytearray(row[0])
            damaged[-1] ^= 1
            connection.execute(
                "UPDATE credentials SET password_encrypted = ? WHERE id = ?",
                (bytes(damaged), credential_id),
            )
        with self.assertRaises(DecryptionError):
            self.service.get_password(credential_id)


class Phase4UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or create_application(
            ["vaultkey-phase4-tests"]
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        database = DatabaseManager(Path(self.temporary.name) / "vault.db")
        database.initialize()
        self.session = VaultSession()
        self.session.unlock(secrets.token_bytes(32))
        self.service = VaultService(database, self.session)

    def tearDown(self) -> None:
        QGuiApplication.clipboard().clear()
        self.session.lock()
        self.temporary.cleanup()

    def test_generator_save_passes_exact_visible_value_in_memory(self) -> None:
        page = GeneratorPage()
        captured: list[str] = []
        page.save_requested.connect(captured.append)
        visible = page.password_output.text()
        page.save_button.click()
        self.assertTrue(len(captured) == 1 and captured[0] == visible)
        categories = self.service.list_categories()
        dialog = CredentialDialog(categories, prefilled_password=captured[0])
        self.assertTrue(dialog.password_input.text() == visible)
        dialog.wipe_sensitive()
        captured.clear()
        del visible
        page.close()

    def test_detail_password_loads_only_on_reveal_or_copy(self) -> None:
        category_id = self.service.list_categories()[0].id
        credential_id = self.service.create_credential(
            CredentialDraft(
                "Detail",
                "private-user",
                "private-password",
                "detail.test",
                category_id,
                "private-notes",
            )
        )
        metadata = self.service.get_credential(credential_id, include_password=False)
        calls = 0

        def load_password() -> str:
            nonlocal calls
            calls += 1
            return self.service.get_password(credential_id)

        dialog = CredentialDetailDialog(metadata, load_password)
        self.assertTrue(calls == 0)
        dialog._toggle_password()
        self.assertTrue(calls == 1)
        dialog._toggle_password()
        self.assertTrue(dialog.password_display.text() == "••••••••••••••")
        dialog._copy_password()
        self.assertTrue(calls == 2)
        self.assertTrue(QGuiApplication.clipboard().text() == "private-password")
        dialog.close()

    def test_main_window_pages_refresh_after_data(self) -> None:
        category_id = self.service.list_categories()[0].id
        self.service.create_credential(
            CredentialDraft(
                "Visible Service",
                "private-user",
                "private-password",
                "visible.test",
                category_id,
                "private-notes",
                True,
            )
        )
        window = MainWindow(self.service)
        window.refresh_data()
        dashboard = window._pages["dashboard"]
        self.assertTrue(dashboard.stat_cards["total"].value_label.text() == "1")
        self.assertTrue(dashboard.stat_cards["favorites"].value_label.text() == "1")
        vault = window._pages["vault"]
        favorites = window._pages["favorites"]
        self.assertTrue(vault.list_layout.count() == 2)
        self.assertTrue(favorites.list_layout.count() == 2)
        window.close()

    def test_controller_lock_unlock_reloads_encrypted_credentials(self) -> None:
        database = DatabaseManager(Path(self.temporary.name) / "controller-vault.db")
        controller = VaultApplicationController(self.application, database)
        controller.start()
        self.assertIsInstance(controller.current_window, SetupWindow)
        setup = controller.current_window
        assert isinstance(setup, SetupWindow)
        master_password = secrets.token_urlsafe(24)
        setup.password_input.line_edit.setText(master_password)
        setup.confirm_input.line_edit.setText(master_password)
        setup._submit()
        self.application.processEvents()
        self.assertIsInstance(controller.current_window, MainWindow)
        main = controller.current_window
        assert isinstance(main, MainWindow)
        service = main.vault_service
        assert service is not None
        category_id = service.list_categories()[0].id
        credential_id = service.create_credential(
            CredentialDraft(
                "Persistent",
                "private-user",
                "private-password",
                "persistent.test",
                category_id,
                "private-notes",
            )
        )
        controller.lock_vault()
        self.application.processEvents()
        self.assertIsInstance(controller.current_window, UnlockWindow)
        unlock = controller.current_window
        assert isinstance(unlock, UnlockWindow)
        unlock.password_input.line_edit.setText(master_password)
        unlock._submit()
        self.application.processEvents()
        self.assertIsInstance(controller.current_window, MainWindow)
        reopened = controller.current_window
        assert isinstance(reopened, MainWindow)
        reopened_service = reopened.vault_service
        assert reopened_service is not None
        loaded = reopened_service.get_credential(credential_id)
        self.assertTrue(loaded.password == "private-password")
        reopened.close()
        controller.session.lock()
        self.application.processEvents()


if __name__ == "__main__":
    unittest.main()
