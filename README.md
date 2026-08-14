# VaultKey

VaultKey is a local-first desktop password manager built with Python and PySide6. Phase 5 adds persistent security preferences, inactivity locking, safe clipboard cleanup, transactional master-password rotation, and encrypted local backup/restore.

Sensitive credential fields are encrypted locally with AES-256-GCM before SQLite persistence. The application remains fully offline.

## Requirements

- Python 3.10 or newer
- Windows, macOS, or Linux with desktop support

## Setup

Create and activate a virtual environment, then install the dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS or Linux, activate with `source .venv/bin/activate` instead.

## Run

```powershell
python main.py
```

The first launch displays Create Vault. After a master password of at least 12 characters is accepted, VaultKey opens the existing dashboard. Later launches show Unlock Vault. The sidebar's Lock Vault action clears the active session key and returns to the unlock screen.

When running from source, the local database is created at `data/vault.db` and
is excluded by `.gitignore`. The packaged Windows application stores it at
`%LOCALAPPDATA%\VaultKey\vault.db`, outside the installation directory, so an
upgrade or uninstall does not overwrite the vault.

## Install on Windows

Download these files from the matching GitHub release:

- `VaultKey-Setup-<version>-Windows-x64.exe` for the normal installer.
- `VaultKey-Portable-<version>-Windows-x64.zip` for a portable application
  folder.
- The matching `.sha256` file if you want to verify the download.

The installer is per-user and does not need administrator access. It installs
VaultKey under `%LOCALAPPDATA%\Programs\VaultKey`, adds an uninstaller, and
offers an optional desktop shortcut. Uninstalling the program intentionally
leaves `%LOCALAPPDATA%\VaultKey\vault.db` in place. Use VaultKey's Reset Vault
feature if you intend to remove the active vault data.

Never add your development `data/vault.db` to a release. To move an existing
vault from a source checkout to the installed application, first create an
encrypted `.vkbak` backup in the source-run application, then restore that
backup from Settings in the installed application.

For the portable build, extract the entire ZIP and run `VaultKey.exe`. Keep the
`_internal` directory next to the executable; the executable cannot run by
itself without those bundled files.

The current release artifacts are not code-signed. Windows SmartScreen may
therefore show an unknown-publisher warning. Verify the SHA-256 checksum and
download only from the official project release page.

In PowerShell, compare a download with its published checksum using:

```powershell
(Get-FileHash .\VaultKey-Setup-0.5.0-Windows-x64.exe -Algorithm SHA256).Hash
Get-Content .\VaultKey-Setup-0.5.0-Windows-x64.exe.sha256
```

## Build a Windows release

Use 64-bit Python on Windows and install the application and build
dependencies into the project virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
```

Install [Inno Setup 6](https://jrsoftware.org/isinfo.php), then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_windows.ps1
```

The script runs the automated tests, regenerates the multi-resolution Windows
icon and version metadata from `APP_VERSION`, builds a PyInstaller
one-directory application, creates both the installer and portable ZIP, and
writes a SHA-256 checksum beside each artifact in `release/`.

For a portable-only build when Inno Setup is unavailable:

```powershell
.\scripts\build_windows.ps1 -SkipInstaller
```

`dist/`, `build/`, and `release/` are generated outputs and are excluded from
Git. Commit the source, packaging configuration, license, and notices; upload
the installer, portable ZIP, and their checksum files to a GitHub Release for
the same version tag.

## Password generator in Phase 3

- Generates passwords from 8 to 64 characters using Python's `secrets` module.
- Supports uppercase, lowercase, numbers, symbols, and ambiguous-character exclusion.
- Guarantees at least one character from every enabled category.
- Uses a secure Fisher–Yates shuffle driven by `secrets.randbelow`.
- Shows an entropy estimate based on the exact selected character pool.
- Copies only when requested, gives temporary feedback, and routes passwords through the ownership-aware clipboard service.
- Keeps generator settings while navigating during the current unlocked session.

Generated passwords remain only in application memory and, after an explicit copy action, the system clipboard. They are never persisted or logged.

## Encrypted vault in Phase 4

- Add, view, edit, favorite, search, filter, and delete credentials.
- Save the exact password shown by Password Generator through the Add Password dialog.
- Encrypt usernames, passwords, and notes before they cross the database boundary.
- Keep service name, website, category, favorite state, and timestamps as local plaintext metadata for efficient filtering and list rendering.
- Create six default categories once and support case-insensitive custom category creation.
- Show totals, favorites, weak passwords, reused passwords, and five recent credentials on the dashboard.
- Decrypt usernames for visible summaries, while passwords are decrypted only for reveal, copy, edit, or transient security analysis.

Each protected field uses AES-256-GCM with a fresh 96-bit nonce and field-specific authenticated context. Stored blobs contain a format version, nonce, and ciphertext with authentication tag. An HKDF-derived credential key domain-separates encryption from the authenticated session key; neither key is persisted.

## Security and settings in Phase 5

- Stores only validated, non-sensitive preferences in `app_settings`: inactivity timeout, clipboard timeout, and appearance mode.
- Tracks application-wide mouse and keyboard activity with a Qt event filter and compares monotonic elapsed time, including after sleep/resume.
- Clears a copied password after the selected timeout only if VaultKey still owns the unchanged clipboard value. Lock and exit perform the same conditional cleanup immediately.
- Supports Dark, Light, and System appearance modes without changing the approved UI structure.
- Changes the master password by deriving a fresh key and salt, re-encrypting every protected credential field with fresh AES-GCM nonces, verifying the new ciphertext, and committing all changes in one SQLite transaction. Success locks the vault.
- Creates `.vkbak` files with a versioned JSON header and an AES-256-GCM encrypted SQLite snapshot. The backup password key uses the vault's stored KDF parameters and an HKDF-separated backup key.
- Validates and authenticates a backup before replacement, checks SQLite integrity and required tables, creates a temporary safety snapshot, and restores atomically. Successful restore returns to Unlock Vault.
- Requires the current master password and exact `RESET` confirmation before deleting only the active local database. Existing backup files are untouched.

Phase 5 remains offline and adds no telemetry, cloud services, or recovery backdoors.

## License

Copyright (C) 2026 Pawara MMNS.

VaultKey is free software licensed under the [GNU General Public License
Version 3](LICENSE). You may use, study, modify, and redistribute it under
the terms of GPL-3.0. The software is provided without warranty.

When distributing a VaultKey executable, provide recipients with this
license and access to the corresponding source code for that exact version:

<https://github.com/pawara-mmns/Password-manager-generator>

## Security design in Phase 2

- The master password is never persisted.
- A fresh 16-byte random salt is generated for each new vault.
- A 256-bit key is derived with Argon2id when supported by `cryptography`; Scrypt is the supported fallback.
- SQLite stores only the salt, versioned KDF parameters, an HMAC-SHA256 verifier, and creation time.
- Verifiers are compared in constant time.
- The derived key is held in a wipeable in-memory session only while unlocked.
- Lock and application exit overwrite the session buffer before releasing it.

Python cannot guarantee complete memory erasure of every temporary immutable value, but VaultKey minimizes key lifetime and does not write keys or passwords to logs, files, or SQLite.

## Tests

Run all automated checks with Qt's offscreen platform:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -v
```

The suite covers 50 authentication, generation, encrypted-vault, settings,
inactivity, clipboard, transactional rotation, encrypted backup/restore,
corruption, rollback, migration, reset, packaging-path, and UI regression
checks.

## Project structure

```text
VaultKey/
├── main.py
├── LICENSE
├── NOTICE
├── THIRD_PARTY_NOTICES.txt
├── requirements.txt
├── requirements-build.txt
├── packaging/
│   ├── VaultKey.spec
│   ├── VaultKey.iss
│   └── windows_version_info.txt
├── scripts/
│   ├── build_windows.ps1
│   ├── generate_windows_icon.py
│   └── generate_windows_version_info.py
├── app/
│   ├── application.py
│   ├── controller.py
│   ├── config.py
│   ├── components/
│   │   ├── auth_widgets.py
│   │   ├── page_widgets.py
│   │   ├── credential_item.py
│   │   └── sidebar.py
│   ├── database/
│   │   ├── category_repository.py
│   │   ├── credential_repository.py
│   │   ├── database.py
│   │   └── models.py
│   ├── security/
│   │   ├── encryption.py
│   │   ├── inactivity_manager.py
│   │   ├── key_manager.py
│   │   ├── password_generator.py
│   │   ├── password_strength.py
│   │   └── session.py
│   ├── services/
│   │   ├── backup_service.py
│   │   ├── clipboard_service.py
│   │   ├── settings_service.py
│   │   ├── vault_security_service.py
│   │   └── vault_service.py
│   └── ui/
│       ├── dialogs/
│       ├── auth_window.py
│       ├── setup_window.py
│       ├── unlock_window.py
│       ├── generator_page.py
│       ├── main_window.py
│       └── existing Phase 1 pages
├── styles/
│   ├── dark.qss
│   └── light.qss
├── assets/icons/
├── data/
└── tests/
    ├── test_phase2.py
    ├── test_phase3.py
    ├── test_phase4.py
    ├── test_phase5.py
    ├── test_phase6.py
    └── test_release_metadata.py
```
