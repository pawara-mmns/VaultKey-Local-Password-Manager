"""Cryptographically secure, offline password generation."""

from __future__ import annotations

import secrets


LOWERCASE = "abcdefghijklmnopqrstuvwxyz"
UPPERCASE = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
NUMBERS = "0123456789"
SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?/"
AMBIGUOUS_CHARACTERS = frozenset("0Oo1lI")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 64
DEFAULT_PASSWORD_LENGTH = 20


class PasswordGenerationError(ValueError):
    """Raised when password generation options are invalid."""


class PasswordGenerator:
    """Generate passwords using only operating-system secure randomness."""

    def generate(
        self,
        length: int,
        uppercase: bool = True,
        lowercase: bool = True,
        numbers: bool = True,
        symbols: bool = True,
        exclude_ambiguous: bool = False,
    ) -> str:
        """Generate a password containing every enabled character category."""
        if type(length) is not int or not MIN_PASSWORD_LENGTH <= length <= MAX_PASSWORD_LENGTH:
            raise PasswordGenerationError(
                f"Password length must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH}."
            )

        groups = self.character_groups(
            uppercase=uppercase,
            lowercase=lowercase,
            numbers=numbers,
            symbols=symbols,
            exclude_ambiguous=exclude_ambiguous,
        )
        if not groups:
            raise PasswordGenerationError("Select at least one character type.")
        if length < len(groups):
            raise PasswordGenerationError(
                "Password length is too short for the selected character types."
            )

        pool = "".join(groups)
        characters = [secrets.choice(group) for group in groups]
        characters.extend(secrets.choice(pool) for _ in range(length - len(characters)))
        self._secure_shuffle(characters)
        return "".join(characters)

    @staticmethod
    def character_groups(
        *,
        uppercase: bool,
        lowercase: bool,
        numbers: bool,
        symbols: bool,
        exclude_ambiguous: bool,
    ) -> tuple[str, ...]:
        """Return the active, optionally filtered character groups."""
        selected = (
            (uppercase, UPPERCASE),
            (lowercase, LOWERCASE),
            (numbers, NUMBERS),
            (symbols, SYMBOLS),
        )
        groups: list[str] = []
        for enabled, characters in selected:
            if not enabled:
                continue
            if exclude_ambiguous:
                characters = "".join(
                    character
                    for character in characters
                    if character not in AMBIGUOUS_CHARACTERS
                )
            if characters:
                groups.append(characters)
        return tuple(groups)

    @classmethod
    def character_pool_size(
        cls,
        *,
        uppercase: bool,
        lowercase: bool,
        numbers: bool,
        symbols: bool,
        exclude_ambiguous: bool,
    ) -> int:
        """Return the size of the exact pool used by the generator."""
        return sum(
            len(group)
            for group in cls.character_groups(
                uppercase=uppercase,
                lowercase=lowercase,
                numbers=numbers,
                symbols=symbols,
                exclude_ambiguous=exclude_ambiguous,
            )
        )

    @staticmethod
    def _secure_shuffle(values: list[str]) -> None:
        """Shuffle in place with Fisher–Yates and secure random indexes."""
        for index in range(len(values) - 1, 0, -1):
            swap_index = secrets.randbelow(index + 1)
            values[index], values[swap_index] = values[swap_index], values[index]
