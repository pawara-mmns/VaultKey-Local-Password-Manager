"""Usability-focused master-password validation and strength feedback."""

from __future__ import annotations

import re
from dataclasses import dataclass


MIN_MASTER_PASSWORD_LENGTH = 12


@dataclass(frozen=True, slots=True)
class StrengthResult:
    level: int
    label: str
    percent: int


_LABELS = ("Very Weak", "Weak", "Fair", "Strong", "Very Strong")
_COMMON_PATTERNS = (
    "password",
    "qwerty",
    "letmein",
    "welcome",
    "admin",
    "1234",
    "abcd",
)


def assess_password_strength(password: str) -> StrengthResult:
    """Estimate password quality for feedback; this is not the KDF."""
    if not password:
        return StrengthResult(0, _LABELS[0], 0)

    length = len(password)
    score = sum(length >= threshold for threshold in (8, 12, 16, 24))
    variety = sum(
        bool(re.search(pattern, password))
        for pattern in (r"[a-z]", r"[A-Z]", r"\d", r"[^\w\s]")
    )
    if variety >= 2:
        score += 1
    if variety >= 3:
        score += 1
    if variety == 4:
        score += 1

    words = [word for word in re.split(r"[^A-Za-z0-9]+", password) if word]
    if length >= 20 and len(words) >= 4:
        score += 1

    normalized = password.casefold().replace(" ", "")
    if any(pattern in normalized for pattern in _COMMON_PATTERNS):
        score -= 2
    if re.search(r"(.)\1{2,}", password):
        score -= 1
    if length >= 6 and len(set(password)) / length < 0.5:
        score -= 1

    if score <= 1:
        level = 0
    elif score == 2:
        level = 1
    elif score == 3:
        level = 2
    elif score <= 5:
        level = 3
    else:
        level = 4
    return StrengthResult(level, _LABELS[level], (level + 1) * 20)


def validate_master_password(password: str, confirmation: str) -> str | None:
    """Return a user-facing setup error, or None when the fields are valid."""
    if not password:
        return "Enter a master password."
    if not confirmation:
        return "Confirm your master password."
    if len(password) < MIN_MASTER_PASSWORD_LENGTH:
        return f"Use at least {MIN_MASTER_PASSWORD_LENGTH} characters for your master password."
    if password != confirmation:
        return "The passwords do not match."
    return None
