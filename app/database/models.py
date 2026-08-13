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
