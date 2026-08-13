"""Database records used by the vault bootstrap flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VaultSettings:
    """The single persisted vault configuration record."""

    password_verifier: bytes
    salt: bytes
    kdf_parameters: str
    created_at: str


@dataclass(frozen=True, slots=True)
class Category:
    id: int
    name: str
    credential_count: int = 0


@dataclass(frozen=True, slots=True)
class CredentialDraft:
    service_name: str
    username: str
    password: str
    website: str
    category_id: int | None
    notes: str
    favorite: bool = False


@dataclass(frozen=True, slots=True)
class CredentialSummary:
    id: int
    service_name: str
    username: str
    website: str
    category_id: int | None
    category_name: str
    favorite: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class CredentialDetail(CredentialSummary):
    password: str
    notes: str


@dataclass(frozen=True, slots=True)
class EncryptedCredential:
    id: int
    service_name: str
    username_encrypted: bytes
    password_encrypted: bytes
    website: str
    category_id: int | None
    category_name: str
    notes_encrypted: bytes
    favorite: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True, slots=True)
class DashboardStats:
    total: int
    favorites: int
    weak: int
    reused: int
