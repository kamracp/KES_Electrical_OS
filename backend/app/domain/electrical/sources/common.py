"""
Common engineering utilities for electrical source sizing.
KESE-S2-M8A
"""

from decimal import Decimal
from typing import TypeVar


RatingT = TypeVar("RatingT", bound=Decimal)


def require_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an exact finite Decimal value."""

    if not isinstance(value, Decimal):
        raise TypeError(
            f"{field_name} must be a Decimal; "
            "float values are not permitted"
        )

    if not value.is_finite():
        raise ValueError(
            f"{field_name} must be finite"
        )


def require_positive_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a Decimal value greater than zero."""

    require_decimal(field_name, value)

    if value <= Decimal("0"):
        raise ValueError(
            f"{field_name} must be greater than zero"
        )


def require_non_negative_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a Decimal value equal to or greater than zero."""

    require_decimal(field_name, value)

    if value < Decimal("0"):
        raise ValueError(
            f"{field_name} must not be negative"
        )


def require_non_positive_decimal(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a Decimal value equal to or below zero."""

    require_decimal(field_name, value)

    if value > Decimal("0"):
        raise ValueError(
            f"{field_name} must not be positive"
        )


def require_ratio(
    field_name: str,
    value: Decimal,
) -> None:
    """Require a ratio greater than zero and not above one."""

    require_decimal(field_name, value)

    if not Decimal("0") < value <= Decimal("1"):
        raise ValueError(
            f"{field_name} must be greater than 0 "
            "and not greater than 1"
        )


def require_factor_not_below_one(
    field_name: str,
    value: Decimal,
) -> None:
    """Require an engineering factor equal to or above one."""

    require_decimal(field_name, value)

    if value < Decimal("1"):
        raise ValueError(
            f"{field_name} must not be less than 1"
        )


def normalize_required_text(
    field_name: str,
    value: str,
) -> str:
    """Validate and normalize required text."""

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string"
        )

    normalized_value = value.strip()

    if not normalized_value:
        raise ValueError(
            f"{field_name} must not be empty"
        )

    return normalized_value


def normalize_optional_text(
    field_name: str,
    value: str | None,
) -> str | None:
    """Validate and normalize optional text."""

    if value is None:
        return None

    if not isinstance(value, str):
        raise TypeError(
            f"{field_name} must be a string or None"
        )

    return value.strip() or None


def validate_positive_rating_schedule(
    *,
    field_name: str,
    ratings: tuple[Decimal, ...],
    empty_message: str,
    duplicate_message: str,
    order_message: str,
) -> None:
    """Validate a positive, unique, ascending rating schedule."""

    if not isinstance(ratings, tuple):
        raise TypeError(
            f"{field_name} must be a tuple"
        )

    if not ratings:
        raise ValueError(empty_message)

    for rating in ratings:
        require_positive_decimal(
            f"{field_name} rating",
            rating,
        )

    if len(ratings) != len(set(ratings)):
        raise ValueError(duplicate_message)

    if ratings != tuple(sorted(ratings)):
        raise ValueError(order_message)


def select_smallest_adequate_rating(
    required_rating: Decimal,
    available_ratings: tuple[RatingT, ...],
) -> RatingT | None:
    """Select the smallest available rating meeting a requirement."""

    require_positive_decimal(
        "required_rating",
        required_rating,
    )

    return next(
        (
            rating
            for rating in available_ratings
            if rating >= required_rating
        ),
        None,
    )


__all__ = [
    "normalize_optional_text",
    "normalize_required_text",
    "require_decimal",
    "require_factor_not_below_one",
    "require_non_negative_decimal",
    "require_non_positive_decimal",
    "require_positive_decimal",
    "require_ratio",
    "select_smallest_adequate_rating",
    "validate_positive_rating_schedule",
]
