"""SQLite category operations."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from app.database.database import DatabaseError, DatabaseManager
from app.database.models import Category


class DuplicateCategoryError(DatabaseError):
    pass


class CategoryRepository:
    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def list_with_counts(self) -> list[Category]:
        try:
            with self.database.connection() as connection:
                rows = connection.execute(
                    """
                    SELECT c.id, c.name, COUNT(cr.id) AS credential_count
                    FROM categories c
                    LEFT JOIN credentials cr ON cr.category_id = c.id
                    GROUP BY c.id, c.name
                    ORDER BY c.name COLLATE NOCASE
                    """
                ).fetchall()
            return [Category(row["id"], row["name"], row["credential_count"]) for row in rows]
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load categories.") from error

    def create(self, name: str) -> Category:
        normalized = " ".join(name.strip().split())
        if not normalized:
            raise ValueError("Enter a category name.")
        if len(normalized) > 50:
            raise ValueError("Category names must be 50 characters or fewer.")
        try:
            with self.database.connection() as connection:
                cursor = connection.execute(
                    "INSERT INTO categories (name, created_at) VALUES (?, ?)",
                    (normalized, datetime.now(timezone.utc).isoformat(timespec="seconds")),
                )
                category_id = int(cursor.lastrowid)
            return Category(category_id, normalized)
        except sqlite3.IntegrityError as error:
            raise DuplicateCategoryError("A category with this name already exists.") from error
        except sqlite3.Error as error:
            raise DatabaseError("Unable to create the category.") from error

    def find_by_name(self, name: str) -> Category | None:
        try:
            with self.database.connection() as connection:
                row = connection.execute(
                    "SELECT id, name FROM categories WHERE name = ? COLLATE NOCASE",
                    (name,),
                ).fetchone()
            return Category(row["id"], row["name"]) if row else None
        except sqlite3.Error as error:
            raise DatabaseError("Unable to load the category.") from error
