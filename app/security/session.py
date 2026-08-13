"""In-memory state for an unlocked vault session."""

from __future__ import annotations


class VaultSession:
    """Keeps derived key material only while the application is unlocked."""

    def __init__(self) -> None:
        self._active_key: bytearray | None = None

    @property
    def is_unlocked(self) -> bool:
        return self._active_key is not None

    def unlock(self, derived_key: bytes) -> None:
        if len(derived_key) != 32:
            raise ValueError("Vault keys must be 256 bits.")
        self.lock()
        self._active_key = bytearray(derived_key)

    def key_copy(self) -> bytes:
        """Return a short-lived copy for future encryption services."""
        if self._active_key is None:
            raise RuntimeError("The vault is locked.")
        return bytes(self._active_key)

    def lock(self) -> None:
        """Best-effort overwrite followed by dropping the active key reference."""
        if self._active_key is not None:
            for index in range(len(self._active_key)):
                self._active_key[index] = 0
            self._active_key = None
