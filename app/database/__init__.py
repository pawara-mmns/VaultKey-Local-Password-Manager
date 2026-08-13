"""SQLite persistence for VaultKey."""

from app.database.database import (
    DatabaseError,
    DatabaseManager,
    VaultAlreadyExistsError,
    VaultConfigurationError,
)
from app.database.models import (
    Category,
    CredentialDetail,
    CredentialDraft,
    CredentialSummary,
    DashboardStats,
    VaultSettings,
)

__all__ = [
    "DatabaseError",
    "DatabaseManager",
    "Category",
    "CredentialDetail",
    "CredentialDraft",
    "CredentialSummary",
    "DashboardStats",
    "VaultAlreadyExistsError",
    "VaultConfigurationError",
    "VaultSettings",
]
