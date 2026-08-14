"""Release metadata generation tests."""

from __future__ import annotations

import unittest

from scripts.generate_windows_version_info import _numeric_version


class WindowsVersionMetadataTests(unittest.TestCase):
    def test_version_is_padded_for_windows(self) -> None:
        self.assertEqual(_numeric_version("1.2.3"), (1, 2, 3, 0))
        self.assertEqual(_numeric_version("1"), (1, 0, 0, 0))

    def test_non_numeric_versions_are_rejected(self) -> None:
        for value in ("", "1.2.3.4.5", "1.2-beta", "v1.2.3"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    _numeric_version(value)


if __name__ == "__main__":
    unittest.main()
