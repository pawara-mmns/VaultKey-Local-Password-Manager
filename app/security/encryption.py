"""Authenticated encryption for credential fields."""

from __future__ import annotations

import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


FORMAT_VERSION = 1
NONCE_LENGTH = 12
KEY_LENGTH = 32
KEY_CONTEXT = b"VaultKey AES-GCM credential key v1"


class EncryptionError(RuntimeError):
    """Raised when a value cannot be encrypted safely."""


class DecryptionError(RuntimeError):
    """Raised when encrypted data is malformed or fails authentication."""


class EncryptionService:
    """Serialize versioned AES-256-GCM ciphertext as version + nonce + data."""

    def encrypt(self, plaintext: str, key: bytes, *, context: str) -> bytes:
        self._validate_key(key)
        if not isinstance(plaintext, str):
            raise EncryptionError("Only text values can be encrypted.")
        nonce = secrets.token_bytes(NONCE_LENGTH)
        try:
            ciphertext = AESGCM(key).encrypt(
                nonce,
                plaintext.encode("utf-8"),
                self._associated_data(context),
            )
        except (TypeError, ValueError) as error:
            raise EncryptionError("Unable to encrypt the credential value.") from error
        return bytes((FORMAT_VERSION,)) + nonce + ciphertext

    def decrypt(self, encrypted_data: bytes, key: bytes, *, context: str) -> str:
        self._validate_key(key, decrypting=True)
        if not isinstance(encrypted_data, bytes) or len(encrypted_data) < 1 + NONCE_LENGTH + 16:
            raise DecryptionError("The encrypted credential value is invalid.")
        if encrypted_data[0] != FORMAT_VERSION:
            raise DecryptionError("The encrypted credential format is unsupported.")
        nonce = encrypted_data[1 : 1 + NONCE_LENGTH]
        ciphertext = encrypted_data[1 + NONCE_LENGTH :]
        try:
            plaintext = AESGCM(key).decrypt(
                nonce,
                ciphertext,
                self._associated_data(context),
            )
            return plaintext.decode("utf-8")
        except (InvalidTag, UnicodeDecodeError, TypeError, ValueError) as error:
            raise DecryptionError("Unable to authenticate the credential value.") from error

    @staticmethod
    def _validate_key(key: bytes, *, decrypting: bool = False) -> None:
        if not isinstance(key, bytes) or len(key) != KEY_LENGTH:
            error_type = DecryptionError if decrypting else EncryptionError
            raise error_type("A valid AES-256 key is required.")

    @staticmethod
    def _associated_data(context: str) -> bytes:
        if not context:
            raise ValueError("An encryption context is required.")
        return f"VaultKey credential field v1:{context}".encode("utf-8")


def derive_credential_key(session_key: bytes) -> bytes:
    """Domain-separate the authenticated session key for credential encryption."""
    if not isinstance(session_key, bytes) or len(session_key) != KEY_LENGTH:
        raise EncryptionError("A valid session key is required.")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=None,
        info=KEY_CONTEXT,
    ).derive(session_key)
