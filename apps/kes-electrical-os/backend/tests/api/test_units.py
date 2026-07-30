"""
API tests for Engineering Units precision hardening.
KESE-S1-M4
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

UNITS_URL = "/api/v1/units/"


def valid_unit_payload() -> dict[str, object]:
    """Return a valid Engineering Unit request payload."""

    return {
        "code": "kW",
        "name": "Kilowatt",
        "symbol": "kW",
        "quantity": "Active Power",
        "unit_system": "SI",
        "si_unit": "W",
        "conversion_factor": "1000.000000000000000000",
        "is_base_unit": False,
        "description": "One kilowatt equals one thousand watts.",
        "remarks": "KESE-S1-M4 precision test.",
        "is_active": True,
    }


@pytest.mark.api
async def test_create_unit_preserves_decimal_precision(
    client: AsyncClient,
) -> None:
    """A Decimal conversion factor should retain all 18 decimal places."""

    response = await client.post(
        UNITS_URL,
        json=valid_unit_payload(),
    )

    assert response.status_code == 201

    data = response.json()

    assert data["code"] == "kW"
    assert data["conversion_factor"] == (
        "1000.000000000000000000"
    )
    assert data["is_base_unit"] is False
    assert data["id"]
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.api
async def test_list_and_get_unit_preserve_decimal_precision(
    client: AsyncClient,
) -> None:
    """List and UUID lookup should return the exact Decimal value."""

    create_response = await client.post(
        UNITS_URL,
        json=valid_unit_payload(),
    )

    assert create_response.status_code == 201

    unit_id = create_response.json()["id"]

    list_response = await client.get(UNITS_URL)

    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["conversion_factor"] == (
        "1000.000000000000000000"
    )

    get_response = await client.get(
        f"{UNITS_URL}{unit_id}",
    )

    assert get_response.status_code == 200
    assert get_response.json()["id"] == unit_id
    assert get_response.json()["conversion_factor"] == (
        "1000.000000000000000000"
    )


@pytest.mark.api
async def test_patch_unit_conversion_factor(
    client: AsyncClient,
) -> None:
    """A conversion factor update should preserve exact precision."""

    create_response = await client.post(
        UNITS_URL,
        json=valid_unit_payload(),
    )

    assert create_response.status_code == 201

    unit_id = create_response.json()["id"]

    patch_response = await client.patch(
        f"{UNITS_URL}{unit_id}",
        json={
            "conversion_factor": "0.001000000000000000",
            "remarks": "Updated exact Decimal factor.",
        },
    )

    assert patch_response.status_code == 200

    updated_unit = patch_response.json()

    assert updated_unit["conversion_factor"] == (
        "0.001000000000000000"
    )
    assert updated_unit["remarks"] == (
        "Updated exact Decimal factor."
    )


@pytest.mark.api
async def test_float_conversion_factor_is_rejected(
    client: AsyncClient,
) -> None:
    """JSON floating-point factors should be rejected."""

    payload = valid_unit_payload()
    payload["conversion_factor"] = 0.1

    response = await client.post(
        UNITS_URL,
        json=payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "conversion_factor must be provided as a decimal string"
        in error["msg"]
        for error in errors
    )


@pytest.mark.api
@pytest.mark.parametrize(
    "conversion_factor",
    [
        "0",
        "-1",
        "0.1234567890123456789",
    ],
)
async def test_invalid_conversion_factor_is_rejected(
    client: AsyncClient,
    conversion_factor: str,
) -> None:
    """Non-positive or over-precision factors should fail validation."""

    payload = valid_unit_payload()
    payload["conversion_factor"] = conversion_factor

    response = await client.post(
        UNITS_URL,
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.api
async def test_delete_and_unknown_unit_return_not_found(
    client: AsyncClient,
) -> None:
    """Deleted and unknown Unit UUIDs should return HTTP 404."""

    create_response = await client.post(
        UNITS_URL,
        json=valid_unit_payload(),
    )

    assert create_response.status_code == 201

    unit_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"{UNITS_URL}{unit_id}",
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    deleted_get_response = await client.get(
        f"{UNITS_URL}{unit_id}",
    )

    unknown_get_response = await client.get(
        f"{UNITS_URL}{uuid4()}",
    )

    assert deleted_get_response.status_code == 404
    assert unknown_get_response.status_code == 404
    assert deleted_get_response.json() == {
        "detail": "Unit not found",
    }