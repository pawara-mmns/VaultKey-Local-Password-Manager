"""Versioned, authenticated local backups for the complete VaultKey database."""

from __future__ import annotations

import base64
import json
import os
import sqlite3
import struct
import tempfile
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.database.database import DatabaseError, DatabaseManager, VaultConfigurationError
from app.database.models import VaultSettings
from app.security.encryption import (
    DecryptionError,
    EncryptionError,
    EncryptionService,
    derive_credential_key,
)
from app.security.key_manager import (
    KdfParameters,
    KeyDerivationError,
    derive_key,
    verify_master_password,
)


MAGIC = b"VKBK"
FORMAT_VERSION = 1
NONCE_LENGTH = 12
MAX_HEADER_SIZE = 64 * 1024
BACKUP_KEY_CONTEXT = b"VaultKey encrypted backup key v1"


class BackupError(RuntimeError):
    pass


class BackupService:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create_backup(self, destination: Path, master_password: str) -> Path:
        try:
            settings = self.database.get_vault_settings()
            if settings is None:
                raise BackupError("No configured vault was found.")
            master_key = verify_master_password(master_password, settings)
            if master_key is None:
                raise BackupError("The master password is incorrect.")
        except BackupError:
            raise
        except (DatabaseError, KeyDerivationError, ValueError, TypeError) as error:
            raise BackupError("VaultKey could not verify the vault for backup.") from error

        destination = Path(destination)
        if destination.resolve() == self.database.path.resolve():
            raise BackupError("The backup cannot replace the active vault database.")
        snapshot_path: Path | None = None
        output_path: Path | None = None
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path = self._temporary_path(self.database.path.parent, ".snapshot")
            self._snapshot_database(snapshot_path)
            payload = snapshot_path.read_bytes()
            nonce = os.urandom(NONCE_LENGTH)
            header = {
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "format": "VaultKey Backup",
                "kdf_parameters": json.loads(settings.kdf_parameters),
                "nonce": base64.b64encode(nonce).decode("ascii"),
                "salt": base64.b64encode(settings.salt).decode("ascii"),
                "version": FORMAT_VERSION,
            }
            header_bytes = json.dumps(
                header, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            backup_key = self._backup_key(master_key)
            encrypted = AESGCM(backup_key).encrypt(nonce, payload, header_bytes)
            output_path = self._temporary_path(destination.parent, ".vkbak.tmp")
            with output_path.open("wb") as stream:
                stream.write(MAGIC)
                stream.write(struct.pack(">I", len(header_bytes)))
                stream.write(header_bytes)
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(output_path, destination)
            output_path = None
            return destination
        except BackupError:
            raise
        except (OSError, sqlite3.Error, ValueError, TypeError) as error:
            raise BackupError("VaultKey could not create the encrypted backup.") from error
        finally:
            self._remove_temporary(snapshot_path)
            self._remove_temporary(output_path)
            del master_key

    def validate_backup(self, source: Path, master_password: str) -> None:
        payload = self._decrypt_backup(Path(source), master_password)
        temp_path: Path | None = None
        try:
            temp_path = self._temporary_path(
                self.database.path.parent, ".restore-check"
            )
            temp_path.write_bytes(payload)
            self._validate_database(temp_path, master_password)
        except BackupError:
            raise
        except OSError as error:
            raise BackupError("VaultKey could not validate the backup safely.") from error
        finally:
            self._remove_temporary(temp_path)
            del payload

    def restore_backup(self, source: Path, master_password: str) -> None:
        payload = self._decrypt_backup(Path(source), master_password)
        restore_path: Path | None = None
        safety_path: Path | None = None
        replaced = False
        try:
            restore_path = self._temporary_path(self.database.path.parent, ".restore")
            safety_path = self._temporary_path(self.database.path.parent, ".safety")
            restore_path.write_bytes(payload)
            self._validate_database(restore_path, master_password)
            self._snapshot_database(safety_path)
            os.replace(restore_path, self.database.path)
            replaced = True
            self._validate_database(self.database.path, master_password)
        except Exception as error:
            if replaced and safety_path is not None and safety_path.exists():
                try:
                    os.replace(safety_path, self.database.path)
                except OSError as rollback_error:
                    retained_safety = safety_path
                    safety_path = None
                    raise BackupError(
                        "Restore failed and VaultKey could not reinstate the temporary "
                        f"safety copy. It was retained at {retained_safety}."
                    ) from rollback_error
            if isinstance(error, BackupError):
                raise
            raise BackupError("VaultKey could not restore the backup safely.") from error
        finally:
            self._remove_temporary(restore_path)
            self._remove_temporary(safety_path)
            del payload

    def _decrypt_backup(self, source: Path, master_password: str) -> bytes:
        try:
            raw = source.read_bytes()
            if len(raw) < 8 or raw[:4] != MAGIC:
                raise BackupError("This is not a VaultKey backup.")
            header_length = struct.unpack(">I", raw[4:8])[0]
            if not 1 <= header_length <= MAX_HEADER_SIZE or len(raw) <= 8 + header_length:
                raise BackupError("The backup header is invalid.")
            header_bytes = raw[8 : 8 + header_length]
            header = json.loads(header_bytes)
            if header.get("format") != "VaultKey Backup" or header.get("version") != FORMAT_VERSION:
                raise BackupError("This backup version is not supported.")
            salt = base64.b64decode(header["salt"], validate=True)
            nonce = base64.b64decode(header["nonce"], validate=True)
            if len(nonce) != NONCE_LENGTH:
                raise ValueError
            parameters = KdfParameters.from_json(
                json.dumps(header["kdf_parameters"], sort_keys=True, separators=(",", ":"))
            )
            master_key = derive_key(master_password, salt, parameters)
            key = self._backup_key(master_key)
            try:
                return AESGCM(key).decrypt(nonce, raw[8 + header_length :], header_bytes)
            finally:
                del master_key, key
        except BackupError:
            raise
        except (
            AttributeError,
            InvalidTag,
            KeyDerivationError,
            DecryptionError,
            EncryptionError,
            OSError,
            KeyError,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as error:
            raise BackupError("The backup is damaged or the master password is incorrect.") from error

    def _snapshot_database(self, target: Path) -> None:
        with self.database.connection() as source:
            with closing(sqlite3.connect(target)) as destination:
                source.backup(destination)
                destination.commit()

    @staticmethod
    def _validate_database(path: Path, master_password: str) -> None:
        try:
            with closing(
                sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
            ) as connection:
                connection.row_factory = sqlite3.Row
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                if integrity is None or integrity[0] != "ok":
                    raise BackupError("The backup database failed its integrity check.")
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                if not {"vault_settings", "categories", "credentials", "app_settings"} <= tables:
                    raise BackupError("The backup does not contain a complete VaultKey vault.")
                required_columns = {
                    "vault_settings": {
                        "id", "password_verifier", "salt", "kdf_parameters", "created_at"
                    },
                    "categories": {"id", "name", "created_at"},
                    "credentials": {
                        "id", "service_name", "username_encrypted", "password_encrypted",
                        "website", "category_id", "notes_encrypted", "favorite",
                        "created_at", "updated_at",
                    },
                    "app_settings": {"key", "value"},
                }
                for table, expected in required_columns.items():
                    actual = {
                        column[1]
                        for column in connection.execute(f"PRAGMA table_info({table})")
                    }
                    if not expected <= actual:
                        raise BackupError("The backup database schema is incomplete.")
                if connection.execute("SELECT COUNT(*) FROM vault_settings").fetchone()[0] != 1:
                    raise BackupError("The backup has an invalid vault configuration.")
                row = connection.execute(
                    """
                    SELECT password_verifier, salt, kdf_parameters, created_at
                    FROM vault_settings WHERE id = 1
                    """
                ).fetchone()
                if row is None:
                    raise BackupError("The backup has no vault configuration.")
                settings = VaultSettings(row[0], row[1], row[2], row[3])
                master_key = verify_master_password(master_password, settings)
                if master_key is None:
                    raise BackupError("The backup master password could not be verified.")
                credential_key = derive_credential_key(master_key)
                encryption = EncryptionService()
                try:
                    for credential in connection.execute(
                        "SELECT username_encrypted, password_encrypted, notes_encrypted FROM credentials"
                    ):
                        for column, context in (
                            ("username_encrypted", "username"),
                            ("password_encrypted", "password"),
                            ("notes_encrypted", "notes"),
                        ):
                            plaintext = encryption.decrypt(
                                credential[column], credential_key, context=context
                            )
                            del plaintext
                finally:
                    del master_key, credential_key
        except BackupError:
            raise
        except (
            DecryptionError,
            EncryptionError,
            KeyDerivationError,
            sqlite3.Error,
            VaultConfigurationError,
            ValueError,
            TypeError,
        ) as error:
            raise BackupError("The backup database is invalid.") from error

    @staticmethod
    def _backup_key(master_key: bytes) -> bytes:
        return HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=BACKUP_KEY_CONTEXT,
        ).derive(master_key)

    @staticmethod
    def _temporary_path(directory: Path, suffix: str) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(prefix=".vaultkey-", suffix=suffix, dir=directory)
        os.close(descriptor)
        return Path(raw_path)

    @staticmethod
    def _remove_temporary(path: Path | None) -> None:
        if path is None:
            return
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
