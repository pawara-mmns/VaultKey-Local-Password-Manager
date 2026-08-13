"""Phase 3 secure password generator and UI tests."""

from __future__ import annotations

import inspect
import os
import secrets
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from app.application import create_application
from app.database import DatabaseManager, VaultSettings
from app.security.password_generator import (
    AMBIGUOUS_CHARACTERS,
    LOWERCASE,
    NUMBERS,
    SYMBOLS,
    UPPERCASE,
    PasswordGenerationError,
    PasswordGenerator,
)
from app.security.password_strength import (
    assess_generated_password,
    estimate_entropy_bits,
)
from app.ui.generator_page import GeneratorPage
from app.ui.main_window import MainWindow


class PasswordGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = PasswordGenerator()

    def test_default_all_groups_has_exact_length(self) -> None:
        self.assertEqual(len(self.generator.generate(20)), 20)

    def test_uppercase_only(self) -> None:
        generated = self.generator.generate(
            20, uppercase=True, lowercase=False, numbers=False, symbols=False
        )
        self.assertTrue(all(character in UPPERCASE for character in generated))

    def test_numbers_only(self) -> None:
        generated = self.generator.generate(
            20, uppercase=False, lowercase=False, numbers=True, symbols=False
        )
        self.assertTrue(all(character in NUMBERS for character in generated))

    def test_symbols_only(self) -> None:
        generated = self.generator.generate(
            20, uppercase=False, lowercase=False, numbers=False, symbols=True
        )
        self.assertTrue(all(character in SYMBOLS for character in generated))

    def test_all_selected_groups_are_guaranteed(self) -> None:
        generated = self.generator.generate(20)
        self.assertTrue(any(character in UPPERCASE for character in generated))
        self.assertTrue(any(character in LOWERCASE for character in generated))
        self.assertTrue(any(character in NUMBERS for character in generated))
        self.assertTrue(any(character in SYMBOLS for character in generated))

    def test_ambiguous_characters_are_excluded(self) -> None:
        generated = self.generator.generate(64, exclude_ambiguous=True)
        self.assertTrue(AMBIGUOUS_CHARACTERS.isdisjoint(generated))

    def test_minimum_and_maximum_lengths(self) -> None:
        self.assertEqual(len(self.generator.generate(8)), 8)
        self.assertEqual(len(self.generator.generate(64)), 64)

    def test_no_groups_is_rejected_safely(self) -> None:
        with self.assertRaisesRegex(
            PasswordGenerationError, "Select at least one character type"
        ):
            self.generator.generate(
                20,
                uppercase=False,
                lowercase=False,
                numbers=False,
                symbols=False,
            )

    def test_invalid_lengths_are_rejected(self) -> None:
        for invalid_length in (7, 65):
            with self.subTest(length=invalid_length):
                with self.assertRaises(PasswordGenerationError):
                    self.generator.generate(invalid_length)

    def test_repeated_generation_varies(self) -> None:
        generated_values = {self.generator.generate(20) for _ in range(12)}
        self.assertEqual(len(generated_values), 12)

    def test_entropy_uses_the_selected_pool(self) -> None:
        all_pool_size = self.generator.character_pool_size(
            uppercase=True,
            lowercase=True,
            numbers=True,
            symbols=True,
            exclude_ambiguous=False,
        )
        numbers_pool_size = self.generator.character_pool_size(
            uppercase=False,
            lowercase=False,
            numbers=True,
            symbols=False,
            exclude_ambiguous=False,
        )
        self.assertGreater(
            estimate_entropy_bits(20, all_pool_size),
            estimate_entropy_bits(20, numbers_pool_size),
        )
        result = assess_generated_password("x" * 20, all_pool_size)
        self.assertEqual(result.label, "Very Strong")
        self.assertIsNotNone(result.entropy_bits)

    def test_implementation_uses_secrets_not_random(self) -> None:
        source = inspect.getsource(
            __import__(
                "app.security.password_generator", fromlist=["PasswordGenerator"]
            )
        )
        self.assertIn("secrets.choice", source)
        self.assertIn("secrets.randbelow", source)
        self.assertNotIn("import random", source)
        self.assertNotIn("random.shuffle", source)


class GeneratorPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or create_application(
            ["vaultkey-generator-tests"]
        )

    def test_initial_state_controls_copy_and_validation(self) -> None:
        page = GeneratorPage()
        page.show()
        self.application.processEvents()

        self.assertEqual(page.length_slider.value(), 20)
        self.assertEqual(len(page.password_output.text()), 20)
        self.assertTrue(all(option.isChecked() for option in page._category_checkboxes()))
        self.assertFalse(page.ambiguous_option.isChecked())
        self.assertIn("bits", page.entropy_label.text())

        page.length_slider.setValue(32)
        page._length_released()
        self.assertEqual(page.length_value.text(), "32")
        self.assertEqual(len(page.password_output.text()), 32)

        page.copy_password()
        self.assertTrue(
            QGuiApplication.clipboard().text() == page.password_output.text()
        )
        self.assertEqual(page.copy_button.text(), "Copied ✓")
        self.assertEqual(page.feedback_label.text(), "Password copied to clipboard.")
        QGuiApplication.clipboard().clear()

        for option in page._category_checkboxes():
            option.setChecked(False)
        self.assertFalse(page.generate_button.isEnabled())
        self.assertEqual(page.feedback_label.text(), "Select at least one character type.")

        page.close()
        self.application.processEvents()

    def test_navigation_preserves_generator_settings(self) -> None:
        window = MainWindow()
        generator_page = window._pages["generator"]
        assert isinstance(generator_page, GeneratorPage)
        generator_page.length_slider.setValue(32)
        generator_page.symbols_option.checkbox.setChecked(False)

        window.show_page("dashboard", animate=False)
        window.show_page("generator", animate=False)

        self.assertIs(window.stack.currentWidget(), generator_page)
        self.assertEqual(generator_page.length_slider.value(), 32)
        self.assertFalse(generator_page.symbols_option.checkbox.isChecked())
        window.close()
        self.application.processEvents()

    def test_generation_and_copy_do_not_change_database(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            database_path = Path(temporary_directory) / "vault.db"
            database = DatabaseManager(database_path)
            database.initialize()
            database.create_vault(
                VaultSettings(
                    password_verifier=secrets.token_bytes(32),
                    salt=secrets.token_bytes(16),
                    kdf_parameters='{"algorithm":"argon2id","iterations":3,"lanes":4,"length":32,"memory_cost":65536,"version":1}',
                    created_at="2026-01-01T00:00:00+00:00",
                )
            )
            before = database_path.read_bytes()

            page = GeneratorPage()
            page.generate_password()
            generated = page.password_output.text()
            page.copy_password()

            after = database_path.read_bytes()
            self.assertEqual(after, before)
            self.assertFalse(generated.encode("utf-8") in after)
            if QGuiApplication.clipboard().text() == generated:
                QGuiApplication.clipboard().clear()
            page.close()


if __name__ == "__main__":
    unittest.main()
