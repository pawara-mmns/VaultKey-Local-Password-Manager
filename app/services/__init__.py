"""Authenticated application services."""

from app.services.vault_service import VaultService, VaultServiceError
from app.services.clipboard_service import ClipboardService
from app.services.settings_service import AppSettings, SettingsService
from app.services.backup_service import BackupError, BackupService
from app.services.vault_security_service import (
    IncorrectMasterPasswordError,
    VaultSecurityError,
    VaultSecurityService,
)

__all__ = [
    "AppSettings",
    "BackupError",
    "BackupService",
    "ClipboardService",
    "SettingsService",
    "IncorrectMasterPasswordError",
    "VaultSecurityError",
    "VaultSecurityService",
    "VaultService",
    "VaultServiceError",
]
