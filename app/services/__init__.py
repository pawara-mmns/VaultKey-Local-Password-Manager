"""Authenticated application services."""

from app.services.vault_service import VaultService, VaultServiceError

__all__ = ["VaultService", "VaultServiceError"]
