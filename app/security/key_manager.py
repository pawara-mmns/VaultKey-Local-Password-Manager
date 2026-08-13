"""Master-password key derivation and vault verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from typing import Any

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from app.database.models import VaultSettings

try:
    from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
except ImportError:  # pragma: no cover - supported fallback for older platforms
    Argon2id = None  # type: ignore[assignment,misc]


KEY_LENGTH = 32
SALT_LENGTH = 16
VERIFIER_CONTEXT = b"VaultKey master password verifier v1"


class KeyDerivationError(RuntimeError):
    """Raised for unsupported or unsafe KDF configuration."""


@dataclass(frozen=True, slots=True)
class KdfParameters:
    """Versioned, serializable KDF configuration."""

    algorithm: str
    version: int = 1
    length: int = KEY_LENGTH
    iterations: int | None = None
    lanes: int | None = None
    memory_cost: int | None = None
    n: int | None = None
    r: int | None = None
    p: int | None = None

    def to_json(self) -> str:
        values = {key: value for key, value in asdict(self).items() if value is not None}
        return json.dumps(values, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, raw: str) -> KdfParameters:
        try:
            values: Any = json.loads(raw)
            if not isinstance(values, dict):
                raise ValueError
            allowed = {field_name for field_name in cls.__dataclass_fields__}
            if set(values) - allowed:
                raise ValueError
            parameters = cls(**values)
            parameters._validate()
            return parameters
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise KeyDerivationError("The stored key derivation settings are invalid.") from error

    def _validate(self) -> None:
        if self.version != 1 or self.length != KEY_LENGTH:
            raise ValueError("Unsupported KDF version or output length")
        if self.algorithm == "argon2id":
            if not (
                isinstance(self.iterations, int)
                and 1 <= self.iterations <= 10
                and isinstance(self.lanes, int)
                and 1 <= self.lanes <= 16
                and isinstance(self.memory_cost, int)
                and 8 * 1024 <= self.memory_cost <= 1024 * 1024
            ):
                raise ValueError("Unsafe Argon2id parameters")
        elif self.algorithm == "scrypt":
            if not (
                isinstance(self.n, int)
                and self.n >= 2**14
                and self.n <= 2**20
                and self.n & (self.n - 1) == 0
                and isinstance(self.r, int)
                and 1 <= self.r <= 32
                and isinstance(self.p, int)
                and 1 <= self.p <= 16
            ):
                raise ValueError("Unsafe Scrypt parameters")
        else:
            raise ValueError("Unsupported KDF")


@dataclass(frozen=True, slots=True)
class VaultSecrets:
    """Values produced during setup; only non-key values are persisted."""

    derived_key: bytes
    salt: bytes
    password_verifier: bytes
    kdf_parameters: str


def default_kdf_parameters() -> KdfParameters:
    """Prefer Argon2id and retain a secure Scrypt fallback."""
    if Argon2id is not None:
        return KdfParameters(
            algorithm="argon2id",
            iterations=3,
            lanes=4,
            memory_cost=64 * 1024,
        )
    return KdfParameters(algorithm="scrypt", n=2**17, r=8, p=1)


def derive_key(password: str, salt: bytes, parameters: KdfParameters) -> bytes:
    """Derive a 256-bit vault key using a library-provided password KDF."""
    parameters._validate()
    if not password:
        raise KeyDerivationError("A master password is required.")
    if len(salt) < SALT_LENGTH:
        raise KeyDerivationError("The vault salt is invalid.")

    password_bytes = password.encode("utf-8")
    try:
        if parameters.algorithm == "argon2id":
            if Argon2id is None:
                raise KeyDerivationError("Argon2id is unavailable on this system.")
            kdf = Argon2id(
                salt=salt,
                length=parameters.length,
                iterations=parameters.iterations,
                lanes=parameters.lanes,
                memory_cost=parameters.memory_cost,
            )
        else:
            kdf = Scrypt(
                salt=salt,
                length=parameters.length,
                n=parameters.n,
                r=parameters.r,
                p=parameters.p,
            )
        return kdf.derive(password_bytes)
    except (MemoryError, TypeError, ValueError, UnsupportedAlgorithm) as error:
        raise KeyDerivationError("Secure key derivation failed.") from error


def create_verifier(derived_key: bytes) -> bytes:
    """Create a domain-separated verifier without persisting the key."""
    return hmac.new(derived_key, VERIFIER_CONTEXT, hashlib.sha256).digest()


def create_vault_secrets(password: str) -> VaultSecrets:
    """Generate fresh KDF inputs and derived material for a new vault."""
    salt = secrets.token_bytes(SALT_LENGTH)
    parameters = default_kdf_parameters()
    key = derive_key(password, salt, parameters)
    return VaultSecrets(key, salt, create_verifier(key), parameters.to_json())


def verify_master_password(password: str, settings: VaultSettings) -> bytes | None:
    """Return the derived key only when the stored verifier matches."""
    parameters = KdfParameters.from_json(settings.kdf_parameters)
    key = derive_key(password, settings.salt, parameters)
    candidate = create_verifier(key)
    if hmac.compare_digest(candidate, settings.password_verifier):
        return key
    return None
