"""Authenticated credential operations bridging UI, encryption, and SQLite."""

from __future__ import annotations

from datetime import datetime, timezone

from app.database.category_repository import CategoryRepository
from app.database.credential_repository import CredentialRepository
from app.database.database import DatabaseError, DatabaseManager
from app.database.models import (
    Category,
    CredentialDetail,
    CredentialDraft,
    CredentialSummary,
    DashboardStats,
    EncryptedCredential,
)
from app.security.encryption import (
    DecryptionError,
    EncryptionError,
    EncryptionService,
    derive_credential_key,
)
from app.security.password_strength import assess_password_strength
from app.security.session import VaultSession


class VaultServiceError(RuntimeError):
    """User-safe credential service failure."""


class VaultService:
    """Expose plaintext models only across the authenticated service boundary."""

    USERNAME_CONTEXT = "username"
    PASSWORD_CONTEXT = "password"
    NOTES_CONTEXT = "notes"

    def __init__(self, database: DatabaseManager, session: VaultSession) -> None:
        self.database = database
        self.session = session
        self.encryption = EncryptionService()
        self.credentials = CredentialRepository(database)
        self.categories = CategoryRepository(database)

    def list_categories(self) -> list[Category]:
        self._require_unlocked()
        return self.categories.list_with_counts()

    def create_category(self, name: str) -> Category:
        self._require_unlocked()
        return self.categories.create(name)

    def create_credential(self, draft: CredentialDraft) -> int:
        draft = self._validated_draft(draft)
        key = self._credential_key()
        timestamp = self._timestamp()
        try:
            record = EncryptedCredential(
                id=0,
                service_name=draft.service_name,
                username_encrypted=self.encryption.encrypt(
                    draft.username, key, context=self.USERNAME_CONTEXT
                ),
                password_encrypted=self.encryption.encrypt(
                    draft.password, key, context=self.PASSWORD_CONTEXT
                ),
                website=draft.website,
                category_id=draft.category_id,
                category_name="",
                notes_encrypted=self.encryption.encrypt(
                    draft.notes, key, context=self.NOTES_CONTEXT
                ),
                favorite=draft.favorite,
                created_at=timestamp,
                updated_at=timestamp,
            )
            return self.credentials.create(record)
        finally:
            del key

    def update_credential(self, credential_id: int, draft: CredentialDraft) -> None:
        draft = self._validated_draft(draft)
        existing = self.credentials.get(credential_id)
        key = self._credential_key()
        try:
            record = EncryptedCredential(
                id=credential_id,
                service_name=draft.service_name,
                username_encrypted=self.encryption.encrypt(
                    draft.username, key, context=self.USERNAME_CONTEXT
                ),
                password_encrypted=self.encryption.encrypt(
                    draft.password, key, context=self.PASSWORD_CONTEXT
                ),
                website=draft.website,
                category_id=draft.category_id,
                category_name=existing.category_name,
                notes_encrypted=self.encryption.encrypt(
                    draft.notes, key, context=self.NOTES_CONTEXT
                ),
                favorite=draft.favorite,
                created_at=existing.created_at,
                updated_at=self._timestamp(),
            )
            self.credentials.update(record)
        finally:
            del key

    def get_credential(
        self, credential_id: int, *, include_password: bool = True
    ) -> CredentialDetail:
        record = self.credentials.get(credential_id)
        key = self._credential_key()
        try:
            return CredentialDetail(
                id=record.id,
                service_name=record.service_name,
                username=self.encryption.decrypt(
                    record.username_encrypted, key, context=self.USERNAME_CONTEXT
                ),
                website=record.website,
                category_id=record.category_id,
                category_name=record.category_name,
                favorite=record.favorite,
                created_at=record.created_at,
                updated_at=record.updated_at,
                password=(
                    self.encryption.decrypt(
                        record.password_encrypted, key, context=self.PASSWORD_CONTEXT
                    )
                    if include_password
                    else ""
                ),
                notes=self.encryption.decrypt(
                    record.notes_encrypted, key, context=self.NOTES_CONTEXT
                ),
            )
        finally:
            del key

    def get_password(self, credential_id: int) -> str:
        """Decrypt only the password for reveal or copy operations."""
        record = self.credentials.get(credential_id)
        key = self._credential_key()
        try:
            return self.encryption.decrypt(
                record.password_encrypted, key, context=self.PASSWORD_CONTEXT
            )
        finally:
            del key

    def list_credentials(
        self,
        *,
        search: str = "",
        category_id: int | None = None,
        favorites_only: bool = False,
        sort: str = "recent",
        limit: int | None = None,
    ) -> list[CredentialSummary]:
        self._require_unlocked()
        records = self.credentials.list(
            category_id=category_id, favorites_only=favorites_only
        )
        key = self._credential_key()
        summaries: list[CredentialSummary] = []
        term = search.strip().casefold()
        try:
            for record in records:
                username = self.encryption.decrypt(
                    record.username_encrypted, key, context=self.USERNAME_CONTEXT
                )
                if term and not any(
                    term in value.casefold()
                    for value in (record.service_name, record.website, username)
                ):
                    continue
                summaries.append(self._summary(record, username))
        finally:
            del key

        if sort == "name_asc":
            summaries.sort(key=lambda item: item.service_name.casefold())
        elif sort == "name_desc":
            summaries.sort(key=lambda item: item.service_name.casefold(), reverse=True)
        if limit is not None:
            return summaries[: max(0, limit)]
        return summaries

    def delete_credential(self, credential_id: int) -> None:
        self._require_unlocked()
        self.credentials.delete(credential_id)

    def set_favorite(self, credential_id: int, favorite: bool) -> None:
        self._require_unlocked()
        self.credentials.set_favorite(credential_id, favorite)

    def dashboard_stats(self) -> DashboardStats:
        self._require_unlocked()
        records = self.credentials.list()
        favorite_count = sum(record.favorite for record in records)
        weak_count = 0
        password_counts: dict[str, int] = {}
        key = self._credential_key()
        try:
            for record in records:
                password = self.encryption.decrypt(
                    record.password_encrypted, key, context=self.PASSWORD_CONTEXT
                )
                if assess_password_strength(password).level <= 1:
                    weak_count += 1
                password_counts[password] = password_counts.get(password, 0) + 1
            reused_count = sum(
                count for count in password_counts.values() if count > 1
            )
            return DashboardStats(
                total=len(records),
                favorites=favorite_count,
                weak=weak_count,
                reused=reused_count,
            )
        finally:
            password_counts.clear()
            del key

    def recent_credentials(self, limit: int = 5) -> list[CredentialSummary]:
        return self.list_credentials(limit=limit)

    def _credential_key(self) -> bytes:
        try:
            session_key = self.session.key_copy()
            try:
                return derive_credential_key(session_key)
            finally:
                del session_key
        except RuntimeError as error:
            raise VaultServiceError("The vault is locked.") from error

    def _require_unlocked(self) -> None:
        if not self.session.is_unlocked:
            raise VaultServiceError("The vault is locked.")

    def _validated_draft(self, draft: CredentialDraft) -> CredentialDraft:
        self._require_unlocked()
        service_name = " ".join(draft.service_name.strip().split())
        username = draft.username.strip()
        password = draft.password
        website = draft.website.strip()
        notes = draft.notes.strip()
        if not service_name:
            raise ValueError("Enter a service name.")
        if not password:
            raise ValueError("Enter a password.")
        if len(service_name) > 120:
            raise ValueError("Service names must be 120 characters or fewer.")
        if len(username) > 500 or len(website) > 500 or len(notes) > 5000:
            raise ValueError("One or more credential fields are too long.")
        category_id = draft.category_id
        if category_id is None:
            other = self.categories.find_by_name("Other")
            category_id = other.id if other else None
        return CredentialDraft(
            service_name,
            username,
            password,
            website,
            category_id,
            notes,
            draft.favorite,
        )

    @staticmethod
    def _summary(record: EncryptedCredential, username: str) -> CredentialSummary:
        return CredentialSummary(
            id=record.id,
            service_name=record.service_name,
            username=username,
            website=record.website,
            category_id=record.category_id,
            category_name=record.category_name,
            favorite=record.favorite,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    @staticmethod
    def _timestamp() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="microseconds")
