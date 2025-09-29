"""Input validation helpers shared by the presentation layer."""

from __future__ import annotations

class ValidationError(ValueError):
    """Raised when user input cannot be converted into a numeric value."""


def parse_int(value: str, field_name: str, *, minimum: int | None = None) -> int:
    """Parse ``value`` into ``int`` ensuring it meets ``minimum`` if provided."""

    try:
        number = int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValidationError(f"{field_name} must be an integer") from exc
    if minimum is not None and number < minimum:
        raise ValidationError(f"{field_name} must be at least {minimum}")
    return number


def parse_float(value: str, field_name: str, *, minimum: float | None = None) -> float:
    """Parse ``value`` into ``float`` ensuring it meets ``minimum`` if provided."""

    try:
        number = float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValidationError(f"{field_name} must be a number") from exc
    if minimum is not None and number < minimum:
        raise ValidationError(f"{field_name} must be at least {minimum}")
    return number


def ensure_positive_float(value: str, field_name: str) -> float:
    """Parse ``value`` and ensure it is a positive ``float``."""

    number = parse_float(value, field_name)
    if number <= 0:
        raise ValidationError(f"{field_name} must be positive")
    return number
