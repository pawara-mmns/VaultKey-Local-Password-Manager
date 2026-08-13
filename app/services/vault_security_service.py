"""Transactional master-password rotation and vault verification."""

from __future__ import annotations

import hmac
import sqlite3

from app.database.database import DatabaseError, DatabaseManager, VaultConfigurationError
from app.security.encryption import (
    DecryptionError,
    EncryptionError,
    EncryptionService,
    derive_credential_key,
)
from app.security.key_manager import KeyDerivationError, create_vault_secrets, verify_master_password
from app.security.password_strength import validate_master_password


class VaultSecurityError(RuntimeError):
    pass


class IncorrectMasterPasswordError(VaultSecurityError):
    pass


class VaultSecurityService:
    """Perform security-sensitive vault changes outside the UI layer."""

    FIELD_COLUMNS = (
        ("username_encrypted", "username"),
        ("password_encrypted", "password"),
        ("notes_encrypted", "notes"),
    )

    def __init__(
        self,
        database: DatabaseManager,
        encryption: EncryptionService | None = None,
    ) -> None:
        self.database = database
        self.encryption = encryption or EncryptionService()

    def verify_password(self, password: str) -> bool:
        settings = self.database.get_vault_settings()
        return settings is not None and verify_master_password(password, settings) is not None

    def change_master_password(
        self, current_password: str, new_password: str, confirmation: str
    ) -> None:
        validation = validate_master_password(new_password, confirmation)
        if validation:
            raise ValueError(validation)
        if current_password == new_password:
            raise ValueError("Choose a new master password that is different from the current one.")

        original = self.database.get_vault_settings()
        if original is None:
            raise VaultConfigurationError("No configured vault was found.")
        old_master_key = verify_master_password(current_password, original)
        if old_master_key is None:
            raise IncorrectMasterPasswordError("The current master password is incorrect.")

        new_secrets = create_vault_secrets(new_password)
        old_key = derive_credential_key(old_master_key)
        new_key = derive_credential_key(new_secrets.derived_key)
        try:
            with self.database.connection() as connection:
                connection.execute("BEGIN IMMEDIATE")
                current = connection.execute(
                    """
                    SELECT password_verifier, salt, kdf_parameters, created_at
                    FROM vault_settings WHERE id = 1
                    """
                ).fetchone()
                if current is None or not (
                    hmac.compare_digest(current["password_verifier"], original.password_verifier)
                    and hmac.compare_digest(current["salt"], original.salt)
                    and current["kdf_parameters"] == original.kdf_parameters
                ):
                    raise VaultSecurityError("The vault changed while the password was being updated.")

                rows = connection.execute(
                    """
                    SELECT id, username_encrypted, password_encrypted, notes_encrypted
                    FROM credentials ORDER BY id
                    """
                ).fetchall()
                for row in rows:
                    migrated: dict[str, bytes] = {}
                    for column, context in self.FIELD_COLUMNS:
                        plaintext = self.encryption.decrypt(row[column], old_key, context=context)
                        try:
                            ciphertext = self.encryption.encrypt(
                                plaintext, new_key, context=context
                            )
                            if self.encryption.decrypt(
                                ciphertext, new_key, context=context
                            ) != plaintext:
                                raise VaultSecurityError(
                                    "New credential encryption could not be verified."
                                )
                            migrated[column] = ciphertext
                        finally:
                            del plaintext
                    connection.execute(
                        """
                        UPDATE credentials
                        SET username_encrypted = ?, password_encrypted = ?, notes_encrypted = ?
                        WHERE id = ?
                        """,
                        (
                            migrated["username_encrypted"],
                            migrated["password_encrypted"],
                            migrated["notes_encrypted"],
                            row["id"],
                        ),
                    )
                connection.execute(
                    """
                    UPDATE vault_settings
                    SET password_verifier = ?, salt = ?, kdf_parameters = ?
                    WHERE id = 1
                    """,
                    (
                        new_secrets.password_verifier,
                        new_secrets.salt,
                        new_secrets.kdf_parameters,
                    ),
                )
        except (VaultSecurityError, ValueError):
            raise
        except (DecryptionError, EncryptionError, KeyDerivationError) as error:
            raise VaultSecurityError(
                "Credential re-encryption failed; no changes were committed."
            ) from error
        except sqlite3.Error as error:
            raise DatabaseError("Unable to update the master password.") from error
        finally:
            del old_master_key, old_key, new_key
