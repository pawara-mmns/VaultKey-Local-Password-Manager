"""Packaging path and release-safety tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import APP_NAME, PROJECT_ROOT, resolve_data_dir
from app.database import DatabaseManager


class PackagingPathTests(unittest.TestCase):
    def test_source_runs_keep_the_existing_project_database_location(self) -> None:
        self.assertEqual(resolve_data_dir(frozen=False), PROJECT_ROOT / "data")

    def test_frozen_runs_use_local_app_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            expected = Path(temporary) / APP_NAME
            self.assertEqual(
                resolve_data_dir(frozen=True, local_app_data=temporary), expected
            )
            database = DatabaseManager(expected / "vault.db")
            database.initialize()
            self.assertTrue((expected / "vault.db").is_file())

    def test_frozen_fallback_is_outside_the_application_bundle(self) -> None:
        resolved = resolve_data_dir(frozen=True, local_app_data=None)
        self.assertEqual(resolved.name, APP_NAME)
        self.assertNotEqual(resolved, PROJECT_ROOT / "data")


if __name__ == "__main__":
    unittest.main()
