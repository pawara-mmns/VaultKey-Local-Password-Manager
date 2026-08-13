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
        BEGIN IMMEDIATE;

        CREATE TABLE IF NOT EXISTS vault_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            password_verifier BLOB NOT NULL,
            salt BLOB NOT NULL,
            kdf_parameters TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            service_name TEXT NOT NULL,
            username_encrypted BLOB NOT NULL,
            password_encrypted BLOB NOT NULL,
            website TEXT NOT NULL DEFAULT '',
            category_id INTEGER,
            notes_encrypted BLOB NOT NULL,
            favorite INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1)),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_credentials_service
            ON credentials(service_name COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_credentials_website
            ON credentials(website COLLATE NOCASE);
        CREATE INDEX IF NOT EXISTS idx_credentials_category
            ON credentials(category_id);
        CREATE INDEX IF NOT EXISTS idx_credentials_favorite
            ON credentials(favorite);
        CREATE INDEX IF NOT EXISTS idx_credentials_updated
            ON credentials(updated_at DESC);

        COMMIT;
    """

    _DEFAULT_CATEGORIES = (
        "Social",
        "Development",
        "Work",
        "Education",
        "Finance",
        "Other",
    )

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def initialize(self) -> None:
        """Create the data directory and Phase 2 schema if needed."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self._connect() as connection:
                connection.executescript(self._SCHEMA)
                connection.executemany(
                    """
                    INSERT OR IGNORE INTO categories (name, created_at)
                    VALUES (?, strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
                    """,
                    ((name,) for name in self._DEFAULT_CATEGORIES),
                )
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
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=10.0)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            with connection:
                yield connection
        finally:
            connection.close()

    def _connect(self):
        """Compatibility wrapper retained for the Phase 2 repository methods."""
        return self.connection()
