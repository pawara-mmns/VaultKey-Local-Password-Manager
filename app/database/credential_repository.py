"""SQLite operations for encrypted credential records."""

from __future__ import annotations

import sqlite3

from app.database.database import DatabaseError, DatabaseManager
from app.database.models import EncryptedCredential


class CredentialNotFoundError(DatabaseError):
    pass


class CredentialRepository:
    _SELECT = """
        SELECT cr.id, cr.service_name, cr.username_encrypted,
               cr.password_encrypted, cr.website, cr.category_id,
               COALESCE(c.name, 'Uncategorized') AS category_name,
               cr.notes_encrypted, cr.favorite, cr.created_at, cr.updated_at
        FROM credentials cr
        LEFT JOIN categories c ON c.id = cr.category_id
    """

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def create(self, record: EncryptedCredential) -> int:
        try:
            with self.database.connection() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO credentials (
                        service_name, username_encrypted, password_encrypted,
                        website, category_id, notes_encrypted, favorite,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.service_name,
                        record.username_encrypted,
                        record.password_encrypted,
                        record.website,
                        record.category_id,
                        record.notes_encrypted,
                        int(record.favorite),
                        record.created_at,
                        record.updated_at,
                    ),
                )
                return int(cursor.lastrowid)
        except sqlite3.Error as error:
            raise DatabaseError("Unable to save the credential.") from error

    def get(self, credential_id: int) -> EncryptedCredential:
        try:
            with self.database.connection() as connection:
                row = connection.execute(
                    self._SELECT + " WHERE cr.id = ?", (credential_id,)
                ).fetchone()
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load the credential.") from error
        if row is None:
            raise CredentialNotFoundError("The credential no longer exists.")
        return self._from_row(row)

    def list(self, *, category_id: int | None = None, favorites_only: bool = False) -> list[EncryptedCredential]:
        conditions: list[str] = []
        parameters: list[object] = []
        if category_id is not None:
            conditions.append("cr.category_id = ?")
            parameters.append(category_id)
        if favorites_only:
            conditions.append("cr.favorite = 1")
        query = self._SELECT
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY cr.updated_at DESC, cr.service_name COLLATE NOCASE"
        try:
            with self.database.connection() as connection:
                rows = connection.execute(query, parameters).fetchall()
            return [self._from_row(row) for row in rows]
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load credentials.") from error

    def update(self, record: EncryptedCredential) -> None:
        try:
            with self.database.connection() as connection:
                cursor = connection.execute(
                    """
                    UPDATE credentials
                    SET service_name = ?, username_encrypted = ?, password_encrypted = ?,
                        website = ?, category_id = ?, notes_encrypted = ?,
                        favorite = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        record.service_name,
                        record.username_encrypted,
                        record.password_encrypted,
                        record.website,
                        record.category_id,
                        record.notes_encrypted,
                        int(record.favorite),
                        record.updated_at,
                        record.id,
                    ),
                )
                if cursor.rowcount != 1:
                    raise CredentialNotFoundError("The credential no longer exists.")
        except CredentialNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to update the credential.") from error

    def delete(self, credential_id: int) -> None:
        try:
            with self.database.connection() as connection:
                cursor = connection.execute("DELETE FROM credentials WHERE id = ?", (credential_id,))
                if cursor.rowcount != 1:
                    raise CredentialNotFoundError("The credential no longer exists.")
        except CredentialNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to delete the credential.") from error

    def set_favorite(self, credential_id: int, favorite: bool) -> None:
        try:
            with self.database.connection() as connection:
                cursor = connection.execute(
                    "UPDATE credentials SET favorite = ?, updated_at = updated_at WHERE id = ?",
                    (int(favorite), credential_id),
                )
                if cursor.rowcount != 1:
                    raise CredentialNotFoundError("The credential no longer exists.")
        except CredentialNotFoundError:
            raise
        except sqlite3.Error as error:
            raise DatabaseError("Unable to update the favorite.") from error

    @staticmethod
    def _from_row(row: sqlite3.Row) -> EncryptedCredential:
        return EncryptedCredential(
            id=row["id"],
            service_name=row["service_name"],
            username_encrypted=row["username_encrypted"],
            password_encrypted=row["password_encrypted"],
            website=row["website"],
            category_id=row["category_id"],
            category_name=row["category_name"],
            notes_encrypted=row["notes_encrypted"],
            favorite=bool(row["favorite"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
