"""Generate PyInstaller's Windows version resource from one app version."""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DESTINATION = PROJECT_ROOT / "packaging" / "windows_version_info.txt"


def _numeric_version(version: str) -> tuple[int, int, int, int]:
    parts = version.split(".")
    if not 1 <= len(parts) <= 4 or any(not part.isdigit() for part in parts):
        raise ValueError("Windows release versions must contain 1-4 numeric parts.")
    values = [int(part) for part in parts]
    return tuple((values + [0] * (4 - len(values))))  # type: ignore[return-value]


def generate_version_info(version: str) -> Path:
    numeric = _numeric_version(version)
    content = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeric},
    prodvers={numeric},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'Pawara MMNS'),
          StringStruct('FileDescription', 'VaultKey local password manager'),
          StringStruct('FileVersion', '{version}'),
          StringStruct('InternalName', 'VaultKey'),
          StringStruct('LegalCopyright', 'Copyright (C) 2026 Pawara MMNS'),
          StringStruct('OriginalFilename', 'VaultKey.exe'),
          StringStruct('ProductName', 'VaultKey'),
          StringStruct('ProductVersion', '{version}')
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
    DESTINATION.write_text(content, encoding="utf-8", newline="\n")
    return DESTINATION


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    arguments = parser.parse_args()
    print(generate_version_info(arguments.version))
