"""
API tests for Engineering Standards.
KESE-S1-M3
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

STANDARDS_URL = "/api/v1/standards/"


@pytest.mark.api
async def test_create_standard(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """A valid Engineering Standard should be created."""

    response = await client.post(
        STANDARDS_URL,
        json=standard_payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["code"] == standard_payload["code"]
    assert data["title"] == standard_payload["title"]
    assert data["issuing_organization"] == "IEC"
    assert data["category"] == "Electrical Installations"
    assert data["publication_year"] == 2025
    assert data["status"] == "ACTIVE"
    assert data["is_active"] is True

    assert data["id"]
    assert data["created_at"]
    assert data["updated_at"]


@pytest.mark.api
async def test_list_and_get_standard(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """A created Standard should appear in list and UUID lookup."""

    create_response = await client.post(
        STANDARDS_URL,
        json=standard_payload,
    )

    assert create_response.status_code == 201

    created_standard = create_response.json()
    standard_id = created_standard["id"]

    list_response = await client.get(STANDARDS_URL)

    assert list_response.status_code == 200

    standards = list_response.json()

    assert len(standards) == 1
    assert standards[0]["id"] == standard_id
    assert standards[0]["code"] == standard_payload["code"]

    get_response = await client.get(
        f"{STANDARDS_URL}{standard_id}",
    )

    assert get_response.status_code == 200

    retrieved_standard = get_response.json()

    assert retrieved_standard["id"] == standard_id
    assert retrieved_standard["code"] == standard_payload["code"]


@pytest.mark.api
async def test_duplicate_standard_code_returns_conflict(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """Duplicate Standard codes should return HTTP 409."""

    first_response = await client.post(
        STANDARDS_URL,
        json=standard_payload,
    )

    assert first_response.status_code == 201

    duplicate_response = await client.post(
        STANDARDS_URL,
        json=standard_payload,
    )

    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "Standard code already exists",
    }


@pytest.mark.api
async def test_patch_standard(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """A Standard should support partial updates."""

    create_response = await client.post(
        STANDARDS_URL,
        json=standard_payload,
    )

    assert create_response.status_code == 201

    standard_id = create_response.json()["id"]

    update_payload = {
        "title": "Updated electrical installation standard",
        "status": "CURRENT",
        "remarks": "Updated through automated API testing.",
        "is_active": False,
    }

    patch_response = await client.patch(
        f"{STANDARDS_URL}{standard_id}",
        json=update_payload,
    )

    assert patch_response.status_code == 200

    updated_standard = patch_response.json()

    assert updated_standard["id"] == standard_id
    assert updated_standard["title"] == update_payload["title"]
    assert updated_standard["status"] == "CURRENT"
    assert updated_standard["remarks"] == update_payload["remarks"]
    assert updated_standard["is_active"] is False
    assert updated_standard["code"] == standard_payload["code"]

    get_response = await client.get(
        f"{STANDARDS_URL}{standard_id}",
    )

    assert get_response.status_code == 200
    assert get_response.json()["status"] == "CURRENT"
    assert get_response.json()["is_active"] is False


@pytest.mark.api
async def test_patch_duplicate_code_returns_conflict(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """Updating a Standard to an existing code should return 409."""

    first_payload = dict(standard_payload)
    second_payload = dict(standard_payload)

    second_payload["code"] = "IEEE 3001.2-2017"
    second_payload["title"] = "Recommended Practice for Load-Flow Studies"
    second_payload["issuing_organization"] = "IEEE"

    first_response = await client.post(
        STANDARDS_URL,
        json=first_payload,
    )
    second_response = await client.post(
        STANDARDS_URL,
        json=second_payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    second_standard_id = second_response.json()["id"]

    conflict_response = await client.patch(
        f"{STANDARDS_URL}{second_standard_id}",
        json={"code": first_payload["code"]},
    )

    assert conflict_response.status_code == 409
    assert conflict_response.json() == {
        "detail": "Standard code already exists",
    }


@pytest.mark.api
async def test_delete_standard(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """A deleted Standard should no longer be retrievable."""

    create_response = await client.post(
        STANDARDS_URL,
        json=standard_payload,
    )

    assert create_response.status_code == 201

    standard_id = create_response.json()["id"]

    delete_response = await client.delete(
        f"{STANDARDS_URL}{standard_id}",
    )

    assert delete_response.status_code == 204
    assert delete_response.content == b""

    get_response = await client.get(
        f"{STANDARDS_URL}{standard_id}",
    )

    assert get_response.status_code == 404
    assert get_response.json() == {
        "detail": "Standard not found",
    }


@pytest.mark.api
async def test_unknown_standard_returns_not_found(
    client: AsyncClient,
) -> None:
    """Unknown UUID operations should return HTTP 404."""

    unknown_id = uuid4()

    get_response = await client.get(
        f"{STANDARDS_URL}{unknown_id}",
    )

    patch_response = await client.patch(
        f"{STANDARDS_URL}{unknown_id}",
        json={"title": "Unknown Standard"},
    )

    delete_response = await client.delete(
        f"{STANDARDS_URL}{unknown_id}",
    )

    assert get_response.status_code == 404
    assert patch_response.status_code == 404
    assert delete_response.status_code == 404

    assert get_response.json()["detail"] == "Standard not found"
    assert patch_response.json()["detail"] == "Standard not found"
    assert delete_response.json()["detail"] == "Standard not found"


@pytest.mark.api
async def test_invalid_lifecycle_dates_return_validation_error(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """withdrawn_date earlier than effective_date should be rejected."""

    invalid_payload = dict(standard_payload)

    invalid_payload["effective_date"] = "2025-12-01"
    invalid_payload["withdrawn_date"] = "2025-01-01"

    response = await client.post(
        STANDARDS_URL,
        json=invalid_payload,
    )

    assert response.status_code == 422

    errors = response.json()["detail"]

    assert any(
        "withdrawn_date cannot be earlier than effective_date"
        in error["msg"]
        for error in errors
    )


@pytest.mark.api
async def test_invalid_publication_year_returns_validation_error(
    client: AsyncClient,
    standard_payload: dict[str, object],
) -> None:
    """Publication years outside the permitted range should fail."""

    invalid_payload = dict(standard_payload)
    invalid_payload["publication_year"] = 1700

    response = await client.post(
        STANDARDS_URL,
        json=invalid_payload,
    )

    assert response.status_code == 422
