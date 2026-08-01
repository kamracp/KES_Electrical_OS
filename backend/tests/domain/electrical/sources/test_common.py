"""
Unit tests for common electrical source-sizing utilities.
KESE-S2-M8A
"""

from decimal import Decimal

import pytest

from app.domain.electrical.sources.common import (
    normalize_optional_text,
    normalize_required_text,
    require_decimal,
    require_factor_not_below_one,
    require_non_negative_decimal,
    require_non_positive_decimal,
    require_positive_decimal,
    require_ratio,
    select_smallest_adequate_rating,
    validate_positive_rating_schedule,
)


@pytest.mark.unit
def test_require_decimal_accepts_decimal() -> None:
    require_decimal(
        "value",
        Decimal("1.25"),
    )


@pytest.mark.unit
def test_require_decimal_rejects_float() -> None:
    with pytest.raises(
        TypeError,
        match="must be a Decimal",
    ):
        require_decimal(
            "value",
            1.25,  # type: ignore[arg-type]
        )


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
    ],
)
def test_require_decimal_rejects_non_finite(
    value: Decimal,
) -> None:
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        require_decimal(
            "value",
            value,
        )


@pytest.mark.unit
def test_positive_decimal_validation() -> None:
    require_positive_decimal(
        "value",
        Decimal("1"),
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        require_positive_decimal(
            "value",
            Decimal("0"),
        )


@pytest.mark.unit
def test_non_negative_decimal_validation() -> None:
    require_non_negative_decimal(
        "value",
        Decimal("0"),
    )

    with pytest.raises(
        ValueError,
        match="must not be negative",
    ):
        require_non_negative_decimal(
            "value",
            Decimal("-0.01"),
        )


@pytest.mark.unit
def test_non_positive_decimal_validation() -> None:
    require_non_positive_decimal(
        "value",
        Decimal("0"),
    )

    with pytest.raises(
        ValueError,
        match="must not be positive",
    ):
        require_non_positive_decimal(
            "value",
            Decimal("0.01"),
        )


@pytest.mark.unit
def test_ratio_validation() -> None:
    require_ratio(
        "ratio",
        Decimal("1"),
    )

    with pytest.raises(ValueError):
        require_ratio(
            "ratio",
            Decimal("0"),
        )


@pytest.mark.unit
def test_factor_validation() -> None:
    require_factor_not_below_one(
        "factor",
        Decimal("1"),
    )

    with pytest.raises(
        ValueError,
        match="must not be less than 1",
    ):
        require_factor_not_below_one(
            "factor",
            Decimal("0.99"),
        )


@pytest.mark.unit
def test_text_normalization() -> None:
    assert normalize_required_text(
        "name",
        "  Main Source  ",
    ) == "Main Source"

    assert normalize_optional_text(
        "notes",
        "  Approved  ",
    ) == "Approved"

    assert normalize_optional_text(
        "notes",
        "   ",
    ) is None


@pytest.mark.unit
def test_rating_schedule_validation() -> None:
    validate_positive_rating_schedule(
        field_name="ratings",
        ratings=(
            Decimal("100"),
            Decimal("250"),
            Decimal("500"),
        ),
        empty_message="ratings required",
        duplicate_message="ratings unique",
        order_message="ratings ascending",
    )


@pytest.mark.unit
def test_duplicate_rating_schedule_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match="ratings unique",
    ):
        validate_positive_rating_schedule(
            field_name="ratings",
            ratings=(
                Decimal("100"),
                Decimal("100"),
            ),
            empty_message="ratings required",
            duplicate_message="ratings unique",
            order_message="ratings ascending",
        )


@pytest.mark.unit
def test_select_smallest_adequate_rating() -> None:
    ratings = (
        Decimal("100"),
        Decimal("250"),
        Decimal("500"),
    )

    assert (
        select_smallest_adequate_rating(
            Decimal("200"),
            ratings,
        )
        == Decimal("250")
    )

    assert (
        select_smallest_adequate_rating(
            Decimal("600"),
            ratings,
        )
        is None
    )
