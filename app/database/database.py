"""Small SQLite repository for local vault configuration."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from collections.abc import Iterator
from pathlib import Path

from app.database.models import VaultSettings


class DatabaseError(RuntimeError):
    """Raised when local database access fails."""


class VaultAlreadyExistsError(DatabaseError):
    """Raised when setup is attempted for an initialized vault."""


class VaultConfigurationError(DatabaseError):
    """Raised when persisted vault configuration is incomplete or malformed."""


class DatabaseManager:
    """Owns schema initialization and the one-row vault settings record."""

    _SCHEMA = """
        CREATE TABLE IF NOT EXISTS vault_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            password_verifier BLOB NOT NULL,
            salt BLOB NOT NULL,
            kdf_parameters TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        """Create the data directory and Phase 2 schema if needed."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.execute(self._SCHEMA)
        except (OSError, sqlite3.Error) as error:
            raise DatabaseError("Unable to initialize the local vault database.") from error

    def has_vault(self) -> bool:
        """Return whether a complete vault configuration exists."""
        return self.get_vault_settings() is not None

    def get_vault_settings(self) -> VaultSettings | None:
        """Load and validate the singleton vault settings record."""
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """
                    SELECT id, password_verifier, salt, kdf_parameters, created_at
                    FROM vault_settings
                    ORDER BY id
                    """
                ).fetchall()
        except sqlite3.Error as error:
            raise DatabaseError("Unable to read the local vault configuration.") from error

        if not rows:
            return None
        if len(rows) != 1 or rows[0][0] != 1:
            raise VaultConfigurationError("The vault configuration is not valid.")

        _, verifier, salt, parameters, created_at = rows[0]
        if (
            not isinstance(verifier, bytes)
            or len(verifier) != 32
            or not isinstance(salt, bytes)
            or len(salt) < 16
            or not isinstance(parameters, str)
            or not parameters.strip()
            or not isinstance(created_at, str)
            or not created_at.strip()
        ):
            raise VaultConfigurationError("The vault configuration is incomplete.")

        return VaultSettings(verifier, salt, parameters, created_at)

    def create_vault(self, settings: VaultSettings) -> None:
        """Persist the first vault configuration atomically."""
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    "SELECT 1 FROM vault_settings LIMIT 1"
                ).fetchone()
                if existing is not None:
                    raise VaultAlreadyExistsError("A vault has already been configured.")
                connection.execute(
                    """
                    INSERT INTO vault_settings (
                        id, password_verifier, salt, kdf_parameters, created_at
                    ) VALUES (1, ?, ?, ?, ?)
                    """,
                    (
                        settings.password_verifier,
                        settings.salt,
                        settings.kdf_parameters,
                        settings.created_at,
                    ),
                )
        except VaultAlreadyExistsError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to save the local vault configuration.") from error

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            with connection:
                yield connection
        finally:
            connection.close()
